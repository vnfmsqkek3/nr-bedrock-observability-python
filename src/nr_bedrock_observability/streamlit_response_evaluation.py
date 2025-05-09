"""
Streamlit에서 사용자 응답 평가를 수집하는 헬퍼 기능

이 모듈은 Streamlit 애플리케이션에서 LLM 응답에 대한 상세한 사용자 평가를 
수집하고 New Relic에 전송하는 기능을 제공합니다.
"""

import logging
import uuid
import time
from typing import Dict, Any, Optional, Union, List, Callable, Tuple
import streamlit as st

from .response_evaluation import ResponseEvaluationCollector

logger = logging.getLogger(__name__)

class StreamlitResponseEvaluationCollector:
    """
    Streamlit 애플리케이션에서 모델 만족도 평가를 수집하는 클래스
    """
    def __init__(
        self,
        application_name: str,
        response_evaluation_collector: ResponseEvaluationCollector,
        session_state_key: str = "llm_model_evaluation"
    ):
        """
        Streamlit 모델 평가 수집기 초기화
        
        :param application_name: 애플리케이션 이름
        :param response_evaluation_collector: 응답 평가 수집기 인스턴스
        :param session_state_key: Streamlit 세션 상태에 사용할 키
        """
        self.application_name = application_name
        self.response_evaluation_collector = response_evaluation_collector
        self.session_state_key = session_state_key
        
        # 세션 상태 초기화
        if self.session_state_key not in st.session_state:
            st.session_state[self.session_state_key] = {
                "submitted": False,
                "model_id": "",
                "overall_score": 5,  # 기본값: 중간 점수
                "relevance_score": 5,
                "accuracy_score": 5,
                "completeness_score": 5,
                "coherence_score": 5,
                "helpfulness_score": 5,
                "response_time_score": 5,
                "feedback_comment": "",
                "query_type": "general",
                "domain": "general",
                "evaluator_type": "end-user"
            }
    
    def render_basic_evaluation_ui(
        self,
        model_id: str,
        key: Optional[str] = None,
        on_submit_callback: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Streamlit UI에서 기본 모델 평가 컴포넌트를 렌더링
        
        :param model_id: 평가 대상 모델 ID
        :param key: UI 컴포넌트에 사용할 고유 키
        :param on_submit_callback: 제출 시 호출할 콜백 함수
        :return: 수집된 평가 데이터
        """
        component_key = key or f"model_eval_{uuid.uuid4().hex[:8]}"
        eval_state = st.session_state[self.session_state_key]
        eval_state["model_id"] = model_id
        
        # 이미 제출된 경우 메시지 표시
        if eval_state["submitted"]:
            st.success("모델 평가를 제출해주셔서 감사합니다!")
            return {
                "model_id": eval_state["model_id"],
                "overall_score": eval_state["overall_score"]
            }
        
        # 평가 UI 컴포넌트 렌더링
        st.subheader("모델 응답 만족도 평가")
        
        # 전체 만족도 평가 슬라이더
        eval_state["overall_score"] = st.slider(
            "전체 만족도 (1-10)",
            min_value=1,
            max_value=10,
            value=eval_state["overall_score"],
            key=f"{component_key}_overall"
        )
        
        # 세부 평가 접기/펼치기
        with st.expander("세부 평가 항목", expanded=False):
            # 관련성 점수
            eval_state["relevance_score"] = st.slider(
                "질문 관련성: 응답이 질문과 얼마나 관련이 있나요?",
                min_value=1,
                max_value=10,
                value=eval_state["relevance_score"],
                key=f"{component_key}_relevance"
            )
            
            # 정확성 점수
            eval_state["accuracy_score"] = st.slider(
                "정확성: 제공된 정보가 얼마나 정확한가요?",
                min_value=1,
                max_value=10,
                value=eval_state["accuracy_score"],
                key=f"{component_key}_accuracy"
            )
            
            # 완성도 점수
            eval_state["completeness_score"] = st.slider(
                "완성도: 응답이 얼마나 상세하고 완전한가요?",
                min_value=1,
                max_value=10,
                value=eval_state["completeness_score"],
                key=f"{component_key}_completeness"
            )
            
            # 유용성 점수
            eval_state["helpfulness_score"] = st.slider(
                "유용성: 응답이 얼마나 도움이 되었나요?",
                min_value=1,
                max_value=10,
                value=eval_state["helpfulness_score"],
                key=f"{component_key}_helpfulness"
            )
        
        # 피드백 코멘트
        eval_state["feedback_comment"] = st.text_area(
            "추가 의견 (선택사항)",
            value=eval_state["feedback_comment"],
            key=f"{component_key}_comment"
        )
        
        # 메타데이터 접기/펼치기
        with st.expander("질문 유형", expanded=False):
            query_types = ["일반 지식", "창의적 생성", "코딩/기술", "분석/추론", "기타"]
            query_type_index = 0
            if eval_state["query_type"] in query_types:
                query_type_index = query_types.index(eval_state["query_type"])
                
            eval_state["query_type"] = st.radio(
                "질문 유형",
                options=query_types,
                index=query_type_index,
                key=f"{component_key}_query_type",
                horizontal=True
            )
            
            domains = ["일반", "기술", "과학", "비즈니스", "예술", "기타"]
            domain_index = 0
            if eval_state["domain"] in domains:
                domain_index = domains.index(eval_state["domain"])
                
            eval_state["domain"] = st.radio(
                "도메인 분야",
                options=domains,
                index=domain_index,
                key=f"{component_key}_domain",
                horizontal=True
            )
        
        # 제출 버튼
        if st.button("평가 제출", key=f"{component_key}_submit"):
            eval_state["submitted"] = True
            
            # 평가 데이터를 기록
            try:
                self.response_evaluation_collector.record_evaluation(
                    model_id=eval_state["model_id"],
                    overall_score=eval_state["overall_score"],
                    relevance_score=eval_state["relevance_score"],
                    accuracy_score=eval_state["accuracy_score"],
                    completeness_score=eval_state["completeness_score"],
                    helpfulness_score=eval_state["helpfulness_score"],
                    feedback_comment=eval_state["feedback_comment"],
                    query_type=eval_state["query_type"],
                    domain=eval_state["domain"],
                    evaluation_source="streamlit"
                )
                
                # 콜백 호출 (있는 경우)
                if on_submit_callback:
                    result_data = {
                        "model_id": eval_state["model_id"],
                        "overall_score": eval_state["overall_score"],
                        "relevance_score": eval_state["relevance_score"],
                        "accuracy_score": eval_state["accuracy_score"],
                        "completeness_score": eval_state["completeness_score"],
                        "helpfulness_score": eval_state["helpfulness_score"]
                    }
                    on_submit_callback(result_data)
                
                st.success("모델 평가를 제출해주셔서 감사합니다!")
                return result_data
                
            except Exception as e:
                st.error(f"평가 제출 중 오류가 발생했습니다: {str(e)}")
                logger.error(f"평가 제출 중 오류: {str(e)}")
        
        # 아직 제출되지 않은 경우
        return None
    
    def render_detailed_evaluation_ui(
        self,
        model_id: str,
        key: Optional[str] = None,
        on_submit_callback: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Streamlit UI에서 상세 모델 평가 컴포넌트를 렌더링
        
        :param model_id: 평가 대상 모델 ID
        :param key: UI 컴포넌트에 사용할 고유 키
        :param on_submit_callback: 제출 시 호출할 콜백 함수
        :return: 수집된 평가 데이터
        """
        component_key = key or f"detail_model_eval_{uuid.uuid4().hex[:8]}"
        eval_state = st.session_state[self.session_state_key]
        eval_state["model_id"] = model_id
        
        # 이미 제출된 경우 메시지 표시
        if eval_state["submitted"]:
            st.success("상세 모델 평가를 제출해주셔서 감사합니다!")
            return {
                "model_id": eval_state["model_id"],
                "overall_score": eval_state["overall_score"],
                "relevance_score": eval_state["relevance_score"],
                "accuracy_score": eval_state["accuracy_score"],
                "completeness_score": eval_state["completeness_score"],
                "coherence_score": eval_state["coherence_score"],
                "helpfulness_score": eval_state["helpfulness_score"],
                "response_time_score": eval_state["response_time_score"],
                "feedback_comment": eval_state["feedback_comment"],
                "query_type": eval_state["query_type"],
                "domain": eval_state["domain"]
            }
        
        # 평가 UI 컴포넌트 렌더링
        st.subheader("모델 응답 상세 평가")
        
        # 전체 만족도 평가 슬라이더
        st.markdown("### 전체 만족도")
        eval_state["overall_score"] = st.slider(
            "전체 만족도 (1-10)",
            min_value=1,
            max_value=10,
            value=eval_state["overall_score"],
            key=f"{component_key}_overall"
        )
        
        # 세부 평가 항목들
        st.markdown("### 세부 평가 항목")
        
        # 관련성 점수
        eval_state["relevance_score"] = st.slider(
            "질문 관련성: 응답이 질문과 얼마나 관련이 있나요?",
            min_value=1,
            max_value=10,
            value=eval_state["relevance_score"],
            key=f"{component_key}_relevance"
        )
        
        # 정확성 점수
        eval_state["accuracy_score"] = st.slider(
            "정확성: 제공된 정보가 얼마나 정확한가요?",
            min_value=1,
            max_value=10,
            value=eval_state["accuracy_score"],
            key=f"{component_key}_accuracy"
        )
        
        # 완성도 점수
        eval_state["completeness_score"] = st.slider(
            "완성도: 응답이 얼마나 상세하고 완전한가요?",
            min_value=1,
            max_value=10,
            value=eval_state["completeness_score"],
            key=f"{component_key}_completeness"
        )
        
        # 일관성 점수
        eval_state["coherence_score"] = st.slider(
            "일관성: 응답이 얼마나 논리적이고 일관적인가요?",
            min_value=1,
            max_value=10,
            value=eval_state["coherence_score"],
            key=f"{component_key}_coherence"
        )
        
        # 유용성 점수
        eval_state["helpfulness_score"] = st.slider(
            "유용성: 응답이 얼마나 도움이 되었나요?",
            min_value=1,
            max_value=10,
            value=eval_state["helpfulness_score"],
            key=f"{component_key}_helpfulness"
        )
        
        # 응답 시간 점수
        eval_state["response_time_score"] = st.slider(
            "응답 속도: 응답 시간에 얼마나 만족하나요?",
            min_value=1,
            max_value=10,
            value=eval_state["response_time_score"],
            key=f"{component_key}_response_time"
        )
        
        # 메타데이터 섹션
        st.markdown("### 질문 유형 및 분야")
        
        # 질문 유형
        query_types = ["일반 지식", "창의적 생성", "코딩/기술", "분석/추론", "기타"]
        query_type_index = 0
        if eval_state["query_type"] in query_types:
            query_type_index = query_types.index(eval_state["query_type"])
            
        eval_state["query_type"] = st.radio(
            "질문 유형",
            options=query_types,
            index=query_type_index,
            key=f"{component_key}_query_type",
            horizontal=True
        )
        
        # 도메인 분야
        domains = ["일반", "기술", "과학", "비즈니스", "예술", "기타"]
        domain_index = 0
        if eval_state["domain"] in domains:
            domain_index = domains.index(eval_state["domain"])
            
        eval_state["domain"] = st.radio(
            "도메인 분야",
            options=domains,
            index=domain_index,
            key=f"{component_key}_domain",
            horizontal=True
        )
        
        # 피드백 코멘트
        st.markdown("### 추가 의견")
        eval_state["feedback_comment"] = st.text_area(
            "모델 응답에 대한 자세한 의견이나 개선 제안을 입력해주세요 (선택사항)",
            value=eval_state["feedback_comment"],
            key=f"{component_key}_comment",
            height=100
        )
        
        # 제출 버튼
        if st.button("상세 평가 제출", key=f"{component_key}_detailed_submit"):
            eval_state["submitted"] = True
            
            # 평가 데이터를 기록
            try:
                self.response_evaluation_collector.record_evaluation(
                    model_id=eval_state["model_id"],
                    overall_score=eval_state["overall_score"],
                    relevance_score=eval_state["relevance_score"],
                    accuracy_score=eval_state["accuracy_score"],
                    completeness_score=eval_state["completeness_score"],
                    coherence_score=eval_state["coherence_score"],
                    helpfulness_score=eval_state["helpfulness_score"],
                    response_time_score=eval_state["response_time_score"],
                    feedback_comment=eval_state["feedback_comment"],
                    query_type=eval_state["query_type"],
                    domain=eval_state["domain"],
                    evaluation_source="streamlit"
                )
                
                # 콜백 호출 (있는 경우)
                if on_submit_callback:
                    result_data = {
                        "model_id": eval_state["model_id"],
                        "overall_score": eval_state["overall_score"],
                        "relevance_score": eval_state["relevance_score"],
                        "accuracy_score": eval_state["accuracy_score"],
                        "completeness_score": eval_state["completeness_score"],
                        "coherence_score": eval_state["coherence_score"],
                        "helpfulness_score": eval_state["helpfulness_score"],
                        "response_time_score": eval_state["response_time_score"],
                        "feedback_comment": eval_state["feedback_comment"],
                        "query_type": eval_state["query_type"],
                        "domain": eval_state["domain"]
                    }
                    on_submit_callback(result_data)
                
                st.success("모델 평가를 제출해주셔서 감사합니다!")
                return result_data
                
            except Exception as e:
                st.error(f"평가 제출 중 오류가 발생했습니다: {str(e)}")
                logger.error(f"평가 제출 중 오류: {str(e)}")
        
        # 아직 제출되지 않은 경우
        return None
    
    def reset_evaluation(self) -> None:
        """
        평가 상태 초기화 (새 대화 시작 시 사용)
        """
        st.session_state[self.session_state_key] = {
            "submitted": False,
            "model_id": "",
            "overall_score": 5,
            "relevance_score": 5,
            "accuracy_score": 5,
            "completeness_score": 5,
            "coherence_score": 5,
            "helpfulness_score": 5,
            "response_time_score": 5,
            "feedback_comment": "",
            "query_type": "general",
            "domain": "general",
            "evaluator_type": "end-user"
        }

# 전역 Streamlit 응답 평가 수집기 생성 헬퍼 함수
def create_streamlit_response_evaluation_collector(
    application_name: str,
    response_evaluation_collector: ResponseEvaluationCollector,
    session_state_key: str = "llm_model_evaluation"
) -> StreamlitResponseEvaluationCollector:
    """
    Streamlit 응답 평가 수집기 생성 헬퍼 함수
    
    :param application_name: 애플리케이션 이름
    :param response_evaluation_collector: 응답 평가 수집기 인스턴스
    :param session_state_key: Streamlit 세션 상태에 사용할 키
    :return: StreamlitResponseEvaluationCollector 인스턴스
    """
    return StreamlitResponseEvaluationCollector(
        application_name=application_name,
        response_evaluation_collector=response_evaluation_collector,
        session_state_key=session_state_key
    ) 