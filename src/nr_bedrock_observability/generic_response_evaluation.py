"""
범용적인 LLM 응답 평가 수집 도구

이 모듈은 어느 환경에서든 쉽게 사용할 수 있는 LLM 응답 평가 수집 함수들을 제공합니다.
Streamlit, Flask, Django, FastAPI 등 다양한 웹 프레임워크 및 CLI 환경에서 활용 가능합니다.
"""

import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union

import newrelic.agent
from .response_evaluation import ResponseEvaluationCollector
from .event_types import EventType

logger = logging.getLogger(__name__)

# 글로벌 평가 수집기 인스턴스를 저장하는 딕셔너리
_evaluation_collectors = {}

def get_evaluation_collector(
    application_name: str,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    collector_id: Optional[str] = None
) -> ResponseEvaluationCollector:
    """
    평가 수집기 인스턴스를 가져오거나 생성합니다.
    
    :param application_name: 애플리케이션 이름
    :param trace_id: 트레이스 ID (없으면 자동 생성)
    :param completion_id: 완성 ID (없으면 트레이스 ID 사용)
    :param user_id: 사용자 ID
    :param session_id: 세션 ID
    :param collector_id: 수집기 ID (여러 수집기를 관리할 때 사용, 없으면 자동 생성)
    :return: ResponseEvaluationCollector 인스턴스
    """
    # 수집기 ID가 제공되지 않은 경우 기본값 사용
    if collector_id is None:
        collector_id = "default"
    
    # 아직 해당 ID의 수집기가 없다면 새로 생성
    if collector_id not in _evaluation_collectors:
        _evaluation_collectors[collector_id] = ResponseEvaluationCollector(
            application_name=application_name,
            trace_id=trace_id,
            completion_id=completion_id,
            user_id=user_id,
            session_id=session_id
        )
    
    # 트레이스 ID나 완성 ID가 제공된 경우 업데이트
    collector = _evaluation_collectors[collector_id]
    if trace_id is not None:
        collector.update_trace_id(trace_id)
    if completion_id is not None:
        collector.update_completion_id(completion_id)
    if user_id is not None:
        collector.update_user_id(user_id)
    if session_id is not None:
        collector.update_session_id(session_id)
    
    return collector

def reset_evaluation_collector(collector_id: str = "default") -> None:
    """
    특정 ID의 평가 수집기를 리셋합니다.
    
    :param collector_id: 제거할 수집기의 ID
    """
    if collector_id in _evaluation_collectors:
        del _evaluation_collectors[collector_id]

def send_evaluation(
    model_id: str,
    overall_score: int,
    application_name: Optional[str] = None,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    model_provider: Optional[str] = None,
    model_name: Optional[str] = None,
    model_version: Optional[str] = None,
    kb_id: Optional[str] = None,
    kb_name: Optional[str] = None,
    kb_data_source_count: Optional[int] = None,
    kb_used_in_query: Optional[bool] = None,
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
    domain: Optional[str] = None,
    total_tokens: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    evaluation_source: Optional[str] = None,
    collector_id: str = "default"
) -> Dict[str, Any]:
    """
    LLM 응답에 대한 사용자 평가를 New Relic에 직접 전송합니다.
    
    이 함수는 이미 생성된 평가 수집기를 사용하거나, 필요한 경우 새로운 수집기를 생성합니다.
    평가 수집기는 collector_id로 구분됩니다.
    
    :param model_id: 평가 대상 모델 ID
    :param overall_score: 전체 만족도 점수 (1-10 척도)
    :param application_name: 애플리케이션 이름 (기존 수집기가 없는 경우 필수)
    :param trace_id: 트레이스 ID
    :param completion_id: 완성 ID
    :param model_provider: 모델 제공 업체 (anthropic, amazon, mistral 등)
    :param model_name: 정규화된 모델 이름
    :param model_version: 모델 버전
    :param kb_id: Bedrock 지식 기반 ID
    :param kb_name: 지식 기반 이름
    :param kb_data_source_count: 지식 기반의 데이터 소스 수
    :param kb_used_in_query: 이 쿼리에서 지식 기반이 사용되었는지 여부
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
    :param domain: 도메인 분야 (기술, 과학, 일반 지식 등)
    :param total_tokens: 총 토큰 수
    :param prompt_tokens: 프롬프트 토큰 수
    :param completion_tokens: 완성 토큰 수
    :param evaluation_source: 평가 출처 (streamlit, api, cli 등)
    :param collector_id: 사용할 평가 수집기 ID
    :return: 기록된 평가 이벤트 데이터 (dictionary)
    """
    try:
        collector = None
        
        # 기존 수집기가 있는지 확인
        if collector_id in _evaluation_collectors:
            collector = _evaluation_collectors[collector_id]
            
            # 트레이스 ID와 완성 ID 업데이트
            if trace_id is not None:
                collector.update_trace_id(trace_id)
            if completion_id is not None:
                collector.update_completion_id(completion_id)
        else:
            # 새 수집기를 생성하기 위해 application_name이 필요
            if application_name is None:
                raise ValueError("application_name은 필수 입력값입니다 (새 수집기 생성 시)")
            
            # 새 수집기 생성
            collector = ResponseEvaluationCollector(
                application_name=application_name,
                trace_id=trace_id,
                completion_id=completion_id
            )
            _evaluation_collectors[collector_id] = collector
        
        # 평가 기록
        result = collector.record_evaluation(
            model_id=model_id,
            overall_score=overall_score,
            model_provider=model_provider,
            model_name=model_name,
            model_version=model_version,
            kb_id=kb_id,
            kb_name=kb_name,
            kb_data_source_count=kb_data_source_count,
            kb_used_in_query=kb_used_in_query,
            relevance_score=relevance_score,
            accuracy_score=accuracy_score,
            completeness_score=completeness_score,
            coherence_score=coherence_score,
            helpfulness_score=helpfulness_score,
            creativity_score=creativity_score,
            response_time_score=response_time_score,
            response_time_ms=response_time_ms,
            feedback_comment=feedback_comment,
            query_type=query_type,
            domain=domain,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            evaluation_source=evaluation_source
        )
        
        return result
    
    except Exception as e:
        logger.error(f"평가 전송 중 오류: {str(e)}")
        # 오류를 다시 발생시켜 호출자가 처리할 수 있도록 함
        raise

def send_evaluation_with_newrelic_agent(
    model_id: str,
    overall_score: int,
    application_name: str,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    New Relic 에이전트를 직접 사용하여 평가 데이터를 전송합니다.
    
    다른 수집기 인스턴스를 사용하지 않고 직접 New Relic에 이벤트를 기록하므로,
    애플리케이션 간의 상태를 유지할 필요가 없는 경우에 유용합니다.
    
    :param model_id: 평가 대상 모델 ID
    :param overall_score: 전체 만족도 점수 (1-10 척도)
    :param application_name: 애플리케이션 이름
    :param trace_id: 트레이스 ID (없으면 자동 생성)
    :param completion_id: 완성 ID (없으면 트레이스 ID 사용)
    :param kwargs: record_evaluation 메소드에 전달할 추가 인수
    :return: 기록된 평가 이벤트 데이터 (dictionary)
    """
    try:
        # 기본 필수 필드 유효성 검사
        if not model_id:
            raise ValueError("model_id는 필수 입력값입니다")
            
        if not 1 <= overall_score <= 10:
            raise ValueError("overall_score는 1에서 10 사이의 값이어야 합니다")
        
        # 트레이스 ID와 완성 ID 설정
        trace_id = trace_id or str(uuid.uuid4())
        completion_id = completion_id or trace_id
        
        # 속성 준비
        attributes = {
            "id": str(uuid.uuid4()),
            "applicationName": application_name,
            "trace_id": trace_id,
            "completion_id": completion_id,
            "timestamp": int(time.time() * 1000),
            "model_id": model_id,
            "overall_score": overall_score
        }
        
        # kwargs에서 추가 속성 가져오기
        for key, value in kwargs.items():
            if value is not None:
                attributes[key] = value
        
        # New Relic 에이전트를 통해 이벤트 기록
        try:
            nr_app = newrelic.agent.application()
            if nr_app:
                # 백그라운드 트랜잭션으로 이벤트 기록
                with newrelic.agent.BackgroundTask(nr_app, name="RecordLlmEvaluation"):
                    newrelic.agent.record_custom_event(
                        EventType.LLM_USER_RESPONSE_EVALUATION, 
                        attributes,
                        application=nr_app
                    )
                    logger.info("모델 평가 이벤트를 New Relic에 직접 기록했습니다")
            else:
                # 애플리케이션 없이 기본 방식으로 기록
                newrelic.agent.record_custom_event(
                    EventType.LLM_USER_RESPONSE_EVALUATION, 
                    attributes
                )
                logger.info("기본 방식으로 모델 평가 이벤트를 New Relic에 기록했습니다")
        except Exception as e:
            logger.error(f"New Relic에 모델 평가 이벤트 기록 중 오류: {str(e)}")
            raise
        
        return attributes
        
    except Exception as e:
        logger.error(f"평가 전송 중 오류: {str(e)}")
        raise 