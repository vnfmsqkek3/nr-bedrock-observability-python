"""
Streamlit에서 사용자 피드백을 수집하는 헬퍼 기능

이 모듈은 Streamlit 애플리케이션에서 LLM 응답에 대한 사용자 피드백을 쉽게 수집하고
New Relic에 전송하는 기능을 제공합니다.
"""

import logging
import uuid
import time
from typing import Dict, Any, Optional, Union, List, Callable
import streamlit as st
import newrelic.agent

from .event_types import EventType, EventData

logger = logging.getLogger(__name__)

class StreamlitFeedbackCollector:
    """
    Streamlit 애플리케이션에서 사용자 피드백을 수집하는 클래스
    """
    def __init__(
        self,
        application_name: str,
        event_client: Any = None,
        trace_id: Optional[str] = None,
        completion_id: Optional[str] = None,
        session_state_key: str = "llm_feedback"
    ):
        """
        Streamlit 피드백 수집기 초기화
        
        :param application_name: 애플리케이션 이름
        :param event_client: 이벤트 클라이언트 (없으면 New Relic 에이전트 직접 사용)
        :param trace_id: 트레이스 ID (없으면 자동 생성)
        :param completion_id: 완성 ID (없으면 트레이스 ID 사용)
        :param session_state_key: Streamlit 세션 상태에 사용할 키
        """
        self.application_name = application_name
        self.event_client = event_client
        self.trace_id = trace_id or str(uuid.uuid4())
        self.completion_id = completion_id or self.trace_id
        self.session_state_key = session_state_key
        
        # 세션 상태 초기화
        if self.session_state_key not in st.session_state:
            st.session_state[self.session_state_key] = {
                "submitted": False,
                "feedback_type": None,
                "feedback_message": "",
                "sentiment_score": 0.0
            }
    
    def render_feedback_ui(
        self,
        key: Optional[str] = None,
        on_submit_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Streamlit UI에서 피드백 컴포넌트를 렌더링
        
        :param key: UI 컴포넌트에 사용할 고유 키
        :param on_submit_callback: 제출 시 호출할 콜백 함수
        :return: 수집된 피드백 데이터
        """
        component_key = key or f"feedback_{uuid.uuid4().hex[:8]}"
        feedback_state = st.session_state[self.session_state_key]
        
        # 이미 제출된 경우 메시지 표시
        if feedback_state["submitted"]:
            st.success("피드백을 제출해주셔서 감사합니다!")
            return {
                "feedback": feedback_state["feedback_type"],
                "sentiment": feedback_state["sentiment_score"],
                "feedback_message": feedback_state["feedback_message"]
            }
        
        # 피드백 UI 컴포넌트 렌더링
        st.subheader("응답에 대한 피드백을 제공해주세요")
        
        # 피드백 버튼 (긍정, 중립, 부정)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            positive_clicked = st.button("👍 좋아요", key=f"{component_key}_positive")
        with col2:
            neutral_clicked = st.button("😐 보통", key=f"{component_key}_neutral")
        with col3:
            negative_clicked = st.button("👎 별로에요", key=f"{component_key}_negative")
        
        # 버튼 클릭 처리
        if positive_clicked:
            feedback_state["feedback_type"] = "positive"
            feedback_state["sentiment_score"] = 1.0
        elif neutral_clicked:
            feedback_state["feedback_type"] = "neutral"
            feedback_state["sentiment_score"] = 0.0
        elif negative_clicked:
            feedback_state["feedback_type"] = "negative"
            feedback_state["sentiment_score"] = -1.0
        
        # 피드백 타입이 선택된 경우, 추가 의견 입력 폼 표시
        if feedback_state["feedback_type"]:
            feedback_state["feedback_message"] = st.text_area(
                "추가 의견을 입력해주세요 (선택사항)",
                key=f"{component_key}_message"
            )
            
            # 제출 버튼
            if st.button("피드백 제출", key=f"{component_key}_submit"):
                feedback_state["submitted"] = True
                
                # 피드백 데이터 구성
                feedback_data = {
                    "feedback": feedback_state["feedback_type"],
                    "sentiment": feedback_state["sentiment_score"],
                    "feedback_message": feedback_state["feedback_message"]
                }
                
                # New Relic에 피드백 이벤트 전송
                self._send_feedback_event(feedback_data)
                
                # 콜백 호출 (있는 경우)
                if on_submit_callback:
                    on_submit_callback(feedback_data)
                
                st.success("피드백을 제출해주셔서 감사합니다!")
                return feedback_data
        
        # 아직 제출되지 않은 경우
        return None
    
    def _send_feedback_event(self, feedback_data: Dict[str, Any]) -> None:
        """
        피드백 데이터를 New Relic에 전송
        
        :param feedback_data: 피드백 데이터
        """
        try:
            # 이벤트 속성 구성
            attributes = {
                "id": str(uuid.uuid4()),
                "applicationName": self.application_name,
                "feedback": feedback_data.get("feedback"),
                "sentiment": feedback_data.get("sentiment"),
                "feedback_message": feedback_data.get("feedback_message"),
                "trace_id": self.trace_id,
                "completion_id": self.completion_id,
                "timestamp": int(time.time() * 1000)
            }
            
            # 이벤트 데이터 생성
            event_data = EventData(
                event_type="LlmFeedback",  # 신규 이벤트 타입
                attributes=attributes
            )
            
            # 이벤트 전송 (이벤트 클라이언트 또는 New Relic 에이전트 사용)
            if self.event_client:
                # 이벤트 클라이언트를 통해 전송
                self.event_client.send(event_data)
                logger.info("피드백 이벤트를 이벤트 클라이언트를 통해 전송했습니다")
            else:
                # New Relic 에이전트를 직접 사용하여 전송
                try:
                    nr_app = newrelic.agent.application()
                    if nr_app:
                        newrelic.agent.record_custom_event(
                            "LlmFeedback", 
                            attributes,
                            application=nr_app
                        )
                        logger.info("피드백 이벤트를 New Relic에 직접 기록했습니다")
                    else:
                        logger.warning("New Relic 애플리케이션이 없어 피드백 이벤트를 기록할 수 없습니다")
                except ImportError:
                    logger.warning("New Relic 에이전트를 임포트할 수 없어 피드백 이벤트를 기록할 수 없습니다")
                except Exception as e:
                    logger.error(f"New Relic에 피드백 이벤트 기록 중 오류: {str(e)}")
            
        except Exception as e:
            logger.error(f"피드백 이벤트 전송 중 오류: {str(e)}")
    
    def update_trace_id(self, trace_id: str) -> None:
        """
        트레이스 ID 업데이트
        
        :param trace_id: 새 트레이스 ID
        """
        self.trace_id = trace_id
    
    def update_completion_id(self, completion_id: str) -> None:
        """
        완성 ID 업데이트
        
        :param completion_id: 새 완성 ID
        """
        self.completion_id = completion_id
    
    def reset_feedback(self) -> None:
        """
        피드백 상태 초기화 (새 대화 시작 시 사용)
        """
        st.session_state[self.session_state_key] = {
            "submitted": False,
            "feedback_type": None,
            "feedback_message": "",
            "sentiment_score": 0.0
        }

# 전역 피드백 수집기 생성 헬퍼 함수
def create_feedback_collector(
    application_name: str,
    event_client: Any = None,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None
) -> StreamlitFeedbackCollector:
    """
    Streamlit 피드백 수집기 생성 헬퍼 함수
    
    :param application_name: 애플리케이션 이름
    :param event_client: 이벤트 클라이언트 (없으면 New Relic 에이전트 직접 사용)
    :param trace_id: 트레이스 ID (없으면 자동 생성)
    :param completion_id: 완성 ID (없으면 트레이스 ID 사용)
    :return: StreamlitFeedbackCollector 인스턴스
    """
    return StreamlitFeedbackCollector(
        application_name=application_name,
        event_client=event_client,
        trace_id=trace_id,
        completion_id=completion_id
    ) 