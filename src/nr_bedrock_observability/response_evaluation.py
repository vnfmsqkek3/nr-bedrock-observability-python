"""
사용자 반응 평가를 수집하는 도구

이 모듈은 LLM 응답에 대한 상세한 사용자 평가를 수집하고
New Relic에 전송하는 기능을 제공합니다.
"""

import logging
import uuid
import time
from typing import Dict, Any, Optional, Union, List, Callable
import newrelic.agent

from .event_types import EventType, EventData, UserResponseEvaluationAttributes

logger = logging.getLogger(__name__)

class ResponseEvaluationCollector:
    """
    사용자 반응 평가를 수집하는 클래스
    """
    def __init__(
        self,
        application_name: str,
        event_client: Any = None,
        trace_id: Optional[str] = None,
        completion_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        사용자 반응 평가 수집기 초기화
        
        :param application_name: 애플리케이션 이름
        :param event_client: 이벤트 클라이언트 (없으면 New Relic 에이전트 직접 사용)
        :param trace_id: 트레이스 ID (없으면 자동 생성)
        :param completion_id: 완성 ID (없으면 트레이스 ID 사용)
        :param user_id: 사용자 ID
        :param session_id: 세션 ID
        """
        self.application_name = application_name
        self.event_client = event_client
        self.trace_id = trace_id or str(uuid.uuid4())
        self.completion_id = completion_id or self.trace_id
        self.user_id = user_id
        self.session_id = session_id
    
    def record_evaluation(
        self,
        model_id: str,
        overall_score: int,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        kb_id: Optional[str] = None,
        kb_name: Optional[str] = None,
        kb_data_source_count: Optional[int] = None,
        kb_used_in_query: Optional[bool] = None,
        langchain_used: Optional[bool] = None,
        langchain_version: Optional[str] = None,
        langchain_chain_type: Optional[str] = None,
        langchain_retriever_type: Optional[str] = None,
        langchain_embedding_model: Optional[str] = None,
        relevance_score: Optional[int] = None,
        accuracy_score: Optional[int] = None,
        completeness_score: Optional[int] = None,
        coherence_score: Optional[int] = None,
        helpfulness_score: Optional[int] = None,
        creativity_score: Optional[int] = None,
        response_time_score: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        feedback_comment: Optional[str] = None,
        query_type: Optional[str] = None,
        context_size: Optional[int] = None,
        domain: Optional[str] = None,
        total_tokens: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        evaluation_source: Optional[str] = None,
        evaluator_type: Optional[str] = "end-user"
    ) -> Dict[str, Any]:
        """
        모델 응답에 대한 만족도 평가 기록
        
        :param model_id: 평가 대상 모델 ID
        :param overall_score: 전체 만족도 점수 (1-10 척도)
        :param model_provider: 모델 제공 업체 (anthropic, amazon, mistral 등)
        :param model_name: 정규화된 모델 이름
        :param model_version: 모델 버전
        :param kb_id: Bedrock 지식 기반 ID
        :param kb_name: 지식 기반 이름
        :param kb_data_source_count: 지식 기반의 데이터 소스 수
        :param kb_used_in_query: 이 쿼리에서 지식 기반이 사용되었는지 여부
        :param langchain_used: LangChain 사용 여부
        :param langchain_version: LangChain 버전
        :param langchain_chain_type: 사용된 체인 유형
        :param langchain_retriever_type: 사용된 검색기 유형
        :param langchain_embedding_model: 사용된 임베딩 모델
        :param relevance_score: 질문 관련성 점수 (1-10 척도)
        :param accuracy_score: 정보 정확성 점수 (1-10 척도)
        :param completeness_score: 응답 완성도/상세함 점수 (1-10 척도)
        :param coherence_score: 응답 일관성/논리 점수 (1-10 척도)
        :param helpfulness_score: 유용성/도움 정도 점수 (1-10 척도)
        :param creativity_score: 창의성 점수 (1-10 척도)
        :param response_time_score: 응답 속도 만족도 점수 (1-10 척도)
        :param response_time_ms: 실제 응답 시간 (밀리초)
        :param feedback_comment: 자유 형식 피드백 코멘트
        :param query_type: 질문 유형 (factual, creative, coding 등)
        :param context_size: 컨텍스트 크기 (토큰)
        :param domain: 도메인 분야 (기술, 과학, 일반 지식 등)
        :param total_tokens: 총 토큰 수
        :param prompt_tokens: 프롬프트 토큰 수
        :param completion_tokens: 완성 토큰 수
        :param temperature: 모델 temperature 값
        :param top_p: 모델 top_p 값
        :param evaluation_source: 평가 출처 (streamlit, api, cli 등)
        :param evaluator_type: 평가자 타입 (end-user, expert, developer 등)
        :return: 기록된 평가 데이터
        """
        # 유효성 검사
        if not model_id:
            raise ValueError("model_id는 필수 입력값입니다.")
            
        if not 1 <= overall_score <= 10:
            raise ValueError("overall_score는 1에서 10 사이의 값이어야 합니다.")
        
        # 선택적 점수 필드에 대한 유효성 검사
        score_fields = {
            "relevance_score": relevance_score,
            "accuracy_score": accuracy_score,
            "completeness_score": completeness_score, 
            "coherence_score": coherence_score,
            "helpfulness_score": helpfulness_score,
            "creativity_score": creativity_score,
            "response_time_score": response_time_score
        }
        
        for field_name, score in score_fields.items():
            if score is not None and not 1 <= score <= 10:
                raise ValueError(f"{field_name}는 1에서 10 사이의 값이어야 합니다.")
        
        # 모델 정보 자동 파싱
        if model_provider is None and '.' in model_id:
            model_provider = model_id.split('.')[0]  # anthropic.claude-3-sonnet-v1 -> anthropic
        
        if model_name is None and '.' in model_id:
            # 예) anthropic.claude-3-sonnet-20240229-v1:0 -> claude-3-sonnet
            parts = model_id.split('.')
            if len(parts) > 1:
                model_parts = parts[1].split('-')
                if len(model_parts) >= 3:  # claude-3-sonnet-20240229-v1:0
                    model_name = '-'.join(model_parts[:3])  # claude-3-sonnet
        
        if model_version is None and model_id:
            # 날짜나 버전 부분 추출 시도
            parts = model_id.split('-')
            for part in parts:
                # 날짜 형식(8자리 숫자) 또는 v1:0 같은 버전 형식 탐지
                if (len(part) == 8 and part.isdigit()) or part.startswith('v'):
                    model_version = part
                    break
        
        # 속성 준비
        attributes = {
            "id": str(uuid.uuid4()),
            "applicationName": self.application_name,
            "trace_id": self.trace_id,
            "completion_id": self.completion_id,
            "timestamp": int(time.time() * 1000),
            "model_id": model_id,
            "overall_score": overall_score
        }
        
        # 선택적 필드 추가
        optional_attrs = {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "model_provider": model_provider,
            "model_name": model_name,
            "model_version": model_version,
            "kb_id": kb_id,
            "kb_name": kb_name,
            "kb_data_source_count": kb_data_source_count,
            "kb_used_in_query": kb_used_in_query,
            "langchain_used": langchain_used,
            "langchain_version": langchain_version,
            "langchain_chain_type": langchain_chain_type,
            "langchain_retriever_type": langchain_retriever_type,
            "langchain_embedding_model": langchain_embedding_model,
            "relevance_score": relevance_score,
            "accuracy_score": accuracy_score,
            "completeness_score": completeness_score,
            "coherence_score": coherence_score,
            "helpfulness_score": helpfulness_score,
            "creativity_score": creativity_score,
            "response_time_score": response_time_score,
            "response_time_ms": response_time_ms,
            "feedback_comment": feedback_comment,
            "query_type": query_type,
            "context_size": context_size,
            "domain": domain,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "evaluation_source": evaluation_source,
            "evaluator_type": evaluator_type
        }
        
        # None이 아닌 선택적 속성 추가
        for key, value in optional_attrs.items():
            if value is not None:
                attributes[key] = value
        
        try:
            # 이벤트 데이터 생성 - EventData 타입 힌트를 실제 dict 객체로 변경
            event_data = {
                "eventType": EventType.LLM_USER_RESPONSE_EVALUATION,
                "attributes": attributes
            }
            
            # 이벤트 전송 (이벤트 클라이언트 또는 New Relic 에이전트 사용)
            if self.event_client:
                # 이벤트 클라이언트를 통해 전송
                self.event_client.send(event_data)
                logger.info("모델 평가 이벤트를 이벤트 클라이언트를 통해 전송했습니다")
            else:
                # New Relic 에이전트를 직접 사용하여 전송
                try:
                    nr_app = newrelic.agent.application()
                    if nr_app:
                        newrelic.agent.record_custom_event(
                            EventType.LLM_USER_RESPONSE_EVALUATION, 
                            attributes,
                            application=nr_app
                        )
                        logger.info("모델 평가 이벤트를 New Relic에 직접 기록했습니다")
                    else:
                        logger.warning("New Relic 애플리케이션이 없어 모델 평가 이벤트를 기록할 수 없습니다")
                except ImportError:
                    logger.warning("New Relic 에이전트를 임포트할 수 없어 모델 평가 이벤트를 기록할 수 없습니다")
                except Exception as e:
                    logger.error(f"New Relic에 모델 평가 이벤트 기록 중 오류: {str(e)}")
                    
            return attributes
            
        except Exception as e:
            logger.error(f"모델 평가 이벤트 전송 중 오류: {str(e)}")
            raise
    
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
    
    def update_user_id(self, user_id: str) -> None:
        """
        사용자 ID 업데이트
        
        :param user_id: 새 사용자 ID
        """
        self.user_id = user_id
    
    def update_session_id(self, session_id: str) -> None:
        """
        세션 ID 업데이트
        
        :param session_id: 새 세션 ID
        """
        self.session_id = session_id

# 전역 사용자 반응 평가 수집기 생성 헬퍼 함수
def create_response_evaluation_collector(
    application_name: str,
    event_client: Any = None,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> ResponseEvaluationCollector:
    """
    사용자 반응 평가 수집기 생성 헬퍼 함수
    
    :param application_name: 애플리케이션 이름
    :param event_client: 이벤트 클라이언트 (없으면 New Relic 에이전트 직접 사용)
    :param trace_id: 트레이스 ID (없으면 자동 생성)
    :param completion_id: 완성 ID (없으면 트레이스 ID 사용)
    :param user_id: 사용자 ID
    :param session_id: 세션 ID
    :return: ResponseEvaluationCollector 인스턴스
    """
    return ResponseEvaluationCollector(
        application_name=application_name,
        event_client=event_client,
        trace_id=trace_id,
        completion_id=completion_id,
        user_id=user_id,
        session_id=session_id
    ) 