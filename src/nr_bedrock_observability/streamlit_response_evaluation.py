"""
Streamlit 환경을 위한 응답 평가 도구

이 모듈은 Streamlit UI에서 사용자 평가를 수집하기 위한 특화된 기능을 제공합니다.
슬라이더 조작 시 UI가 사라지거나 평가 제출 후 상태가 초기화되는 문제를 해결합니다.
"""

import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Union, Callable

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    # Streamlit이 없는 경우 더미 모듈 생성
    class DummyStreamlit:
        class session_state:
            pass
        
        def __getattr__(self, name):
            def dummy_func(*args, **kwargs):
                raise ImportError("Streamlit이 설치되지 않았습니다. 'pip install streamlit'로 설치하세요.")
            return dummy_func
    
    st = DummyStreamlit()

try:
    import newrelic.agent
    NEWRELIC_AVAILABLE = True
except ImportError:
    NEWRELIC_AVAILABLE = False

from .response_evaluation import ResponseEvaluationCollector
from .generic_response_evaluation import send_evaluation, get_evaluation_collector, reset_evaluation_collector
from .event_types import EventType

logger = logging.getLogger(__name__)

def init_response_evaluation_collector(
    application_name: str,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    collector_session_key: str = "response_evaluation_collector"
) -> ResponseEvaluationCollector:
    """
    Streamlit 세션 상태에 응답 평가 수집기를 초기화합니다.
    
    :param application_name: 애플리케이션 이름
    :param trace_id: 트레이스 ID (없으면 자동 생성)
    :param completion_id: 완성 ID (없으면 트레이스 ID 사용)
    :param user_id: 사용자 ID
    :param session_id: 세션 ID
    :param collector_session_key: 세션 상태에서 수집기를 저장할 키
    :return: 초기화된 ResponseEvaluationCollector 인스턴스
    """
    if not STREAMLIT_AVAILABLE:
        raise ImportError("Streamlit이 설치되지 않았습니다. 'pip install streamlit'로 설치하세요.")
    
    # 세션 상태가 아직 초기화되지 않았다면 초기화
    if not hasattr(st, 'session_state'):
        raise RuntimeError("Streamlit 세션 상태가 초기화되지 않았습니다.")
    
    # 수집기가 이미 존재하면 업데이트하고, 없으면 새로 생성
    if collector_session_key in st.session_state:
        collector = st.session_state[collector_session_key]
        
        # 트레이스 ID와 완성 ID 업데이트
        if trace_id is not None:
            collector.update_trace_id(trace_id)
        if completion_id is not None:
            collector.update_completion_id(completion_id)
        if user_id is not None:
            collector.update_user_id(user_id)
        if session_id is not None:
            collector.update_session_id(session_id)
    else:
        # 새 수집기 생성
        collector = ResponseEvaluationCollector(
            application_name=application_name,
            trace_id=trace_id,
            completion_id=completion_id,
            user_id=user_id,
            session_id=session_id
        )
        st.session_state[collector_session_key] = collector
    
    return collector

def ensure_evaluation_state(eval_key: str, default_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Streamlit 세션 상태에 평가 상태가 있는지 확인하고, 없으면 초기화합니다.
    
    :param eval_key: 평가 상태를 저장할 세션 상태 키
    :param default_values: 기본값 딕셔너리 (없으면 기본값 사용)
    :return: 현재 평가 상태
    """
    if not STREAMLIT_AVAILABLE:
        raise ImportError("Streamlit이 설치되지 않았습니다. 'pip install streamlit'로 설치하세요.")
    # 기본 값 설정
    if default_values is None:
        default_values = {
            "submitted": False,
            "overall_score": 5,
            "relevance_score": 5,
            "accuracy_score": 5,
            "completeness_score": 5,
            "coherence_score": 5,
            "helpfulness_score": 5,
            "response_time_score": 5,
            "feedback_comment": "",
            "query_type": "일반 지식",
            "domain": "일반",
            "show_eval_ui": True  # 평가 UI 표시 여부를 제어하는 상태값
        }
    
    # 세션 상태에 평가 키가 없으면 초기화
    if eval_key not in st.session_state:
        st.session_state[eval_key] = default_values
    
    return st.session_state[eval_key]

def update_evaluation_state(eval_key: str, field: str, value: Any) -> None:
    """
    평가 상태의 특정 필드를 업데이트합니다.
    
    :param eval_key: 평가 상태를 저장할 세션 상태 키
    :param field: 업데이트할 필드 이름
    :param value: 새 값
    """
    if not STREAMLIT_AVAILABLE:
        raise ImportError("Streamlit이 설치되지 않았습니다. 'pip install streamlit'로 설치하세요.")
    if eval_key in st.session_state:
        st.session_state[eval_key][field] = value

def create_update_callback(eval_key: str, field_name: str) -> Callable:
    """
    위젯 값이 변경될 때 평가 상태를 업데이트하는 콜백 함수를 생성합니다.
    
    :param eval_key: 평가 상태를 저장할 세션 상태 키
    :param field_name: 업데이트할 필드 이름
    :return: 콜백 함수
    """
    if not STREAMLIT_AVAILABLE:
        raise ImportError("Streamlit이 설치되지 않았습니다. 'pip install streamlit'로 설치하세요.")
    def callback():
        widget_key = f"{field_name}_{eval_key}"
        if widget_key in st.session_state and eval_key in st.session_state:
            st.session_state[eval_key][field_name] = st.session_state[widget_key]
    return callback

def create_evaluation_ui(
    eval_key: str,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    model_id: Optional[str] = None,
    kb_id: Optional[str] = None,
    kb_name: Optional[str] = None,
    kb_used_in_query: Optional[bool] = None,
    response_time_ms: Optional[int] = None,
    total_tokens: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    application_name: Optional[str] = None,
    collector_session_key: str = "response_evaluation_collector",
    use_number_input: bool = True,
    submit_button_text: str = "평가 제출",
    evaluation_source: str = "streamlit",
    on_submit_success: Optional[Callable[[Dict[str, Any]], None]] = None
) -> Dict[str, Any]:
    """
    Streamlit에서 모델 응답 평가 UI를 생성하고 상태를 관리합니다.
    
    :param eval_key: 평가 상태를 저장할 세션 상태 키
    :param trace_id: 트레이스 ID
    :param completion_id: 완성 ID
    :param model_id: 모델 ID
    :param kb_id: 지식 기반 ID
    :param kb_name: 지식 기반 이름
    :param kb_used_in_query: 쿼리에 지식 기반 사용 여부
    :param response_time_ms: 응답 시간 (밀리초)
    :param total_tokens: 총 토큰 수
    :param prompt_tokens: 프롬프트 토큰 수
    :param completion_tokens: 완성 토큰 수
    :param temperature: 모델 temperature 값
    :param top_p: 모델 top_p 값
    :param application_name: 애플리케이션 이름
    :param collector_session_key: 세션 상태에서 수집기를 저장할 키
    :param use_number_input: 슬라이더 대신 숫자 입력 사용 여부
    :param submit_button_text: 제출 버튼 텍스트
    :param evaluation_source: 평가 출처
    :param on_submit_success: 평가 제출 성공 시 호출될 콜백 함수
    :return: 현재 평가 상태
    """
    if not STREAMLIT_AVAILABLE:
        raise ImportError("Streamlit이 설치되지 않았습니다. 'pip install streamlit'로 설치하세요.")
    
    # 평가 상태 초기화
    evaluation_state = ensure_evaluation_state(eval_key)
    
    # 이미 제출된 경우 결과만 표시
    if evaluation_state["submitted"]:
        st.success("이 응답에 대한 평가를 제출해주셔서 감사합니다.")
        
        st.info(f"""
        **평가 결과**
        - 전체 만족도: {evaluation_state.get('overall_score', 'N/A')}
        - 관련성: {evaluation_state.get('relevance_score', 'N/A')}
        - 정확성: {evaluation_state.get('accuracy_score', 'N/A')}
        - 완성도: {evaluation_state.get('completeness_score', 'N/A')}
        - 일관성: {evaluation_state.get('coherence_score', 'N/A')}
        - 유용성: {evaluation_state.get('helpfulness_score', 'N/A')}
        """)
        
        return evaluation_state
    
    # 평가 UI가 표시되어야 하는 경우에만 처리
    if evaluation_state.get("show_eval_ui", True):
        st.markdown("### 모델 응답 평가")
        st.info("평가를 조정한 후 반드시 '평가 제출' 버튼을 클릭하셔야 NewRelic에 평가가 전송됩니다.")
        
        # 위젯 키 생성
        overall_key = f"overall_score_{eval_key}"
        relevance_key = f"relevance_score_{eval_key}"
        accuracy_key = f"accuracy_score_{eval_key}"
        completeness_key = f"completeness_score_{eval_key}"
        coherence_key = f"coherence_score_{eval_key}"
        helpfulness_key = f"helpfulness_score_{eval_key}"
        response_time_key = f"response_time_score_{eval_key}"
        query_type_key = f"query_type_{eval_key}"
        domain_key = f"domain_{eval_key}"
        comment_key = f"feedback_comment_{eval_key}"
        
        # 위젯 상태 초기화
        for field, key in [
            ("overall_score", overall_key),
            ("relevance_score", relevance_key),
            ("accuracy_score", accuracy_key),
            ("completeness_score", completeness_key),
            ("coherence_score", coherence_key),
            ("helpfulness_score", helpfulness_key),
            ("response_time_score", response_time_key),
            ("feedback_comment", comment_key),
            ("query_type", query_type_key),
            ("domain", domain_key)
        ]:
            if key not in st.session_state:
                # 숫자 입력 필드의 기본값은 evaluation_state에서 가져오도록 보장
                st.session_state[key] = evaluation_state.get(field, 5 if "score" in field else "")
        
        # 숫자 입력 또는 슬라이더로 점수 입력 받기
        if use_number_input:
            # 숫자 입력 필드 사용 (UI 안정성 향상)
            st.number_input("전체 만족도", min_value=1, max_value=10, step=1, 
                           key=overall_key, on_change=create_update_callback(eval_key, "overall_score"))
            
            col1, col2 = st.columns(2)
            with col1:
                st.number_input("질문 관련성", min_value=1, max_value=10, step=1, 
                               key=relevance_key, on_change=create_update_callback(eval_key, "relevance_score"))
                st.number_input("정확성", min_value=1, max_value=10, step=1, 
                               key=accuracy_key, on_change=create_update_callback(eval_key, "accuracy_score"))
                st.number_input("완성도", min_value=1, max_value=10, step=1, 
                               key=completeness_key, on_change=create_update_callback(eval_key, "completeness_score"))
            
            with col2:
                st.number_input("일관성", min_value=1, max_value=10, step=1, 
                               key=coherence_key, on_change=create_update_callback(eval_key, "coherence_score"))
                st.number_input("유용성", min_value=1, max_value=10, step=1, 
                               key=helpfulness_key, on_change=create_update_callback(eval_key, "helpfulness_score"))
                st.number_input("응답 속도", min_value=1, max_value=10, step=1, 
                               key=response_time_key, on_change=create_update_callback(eval_key, "response_time_score"))
        else:
            # 슬라이더 사용 (UI가 초기화될 위험이 있음)
            st.slider("전체 만족도", min_value=1, max_value=10, step=1, 
                     key=overall_key, on_change=create_update_callback(eval_key, "overall_score"))
            
            col1, col2 = st.columns(2)
            with col1:
                st.slider("질문 관련성", min_value=1, max_value=10, step=1, 
                         key=relevance_key, on_change=create_update_callback(eval_key, "relevance_score"))
                st.slider("정확성", min_value=1, max_value=10, step=1, 
                         key=accuracy_key, on_change=create_update_callback(eval_key, "accuracy_score"))
                st.slider("완성도", min_value=1, max_value=10, step=1, 
                         key=completeness_key, on_change=create_update_callback(eval_key, "completeness_score"))
            
            with col2:
                st.slider("일관성", min_value=1, max_value=10, step=1, 
                         key=coherence_key, on_change=create_update_callback(eval_key, "coherence_score"))
                st.slider("유용성", min_value=1, max_value=10, step=1, 
                         key=helpfulness_key, on_change=create_update_callback(eval_key, "helpfulness_score"))
                st.slider("응답 속도", min_value=1, max_value=10, step=1, 
                         key=response_time_key, on_change=create_update_callback(eval_key, "response_time_score"))
        
        # 드롭다운 및 텍스트 영역
        st.selectbox("질문 유형", ["일반 지식", "창의적 생성", "코딩/기술", "분석/추론", "기타"], 
                    key=query_type_key, on_change=create_update_callback(eval_key, "query_type"))
        
        st.selectbox("도메인", ["일반", "기술", "과학", "비즈니스", "예술", "기타"], 
                    key=domain_key, on_change=create_update_callback(eval_key, "domain"))
        
        st.text_area("피드백 (선택)", key=comment_key, height=100, 
                    on_change=create_update_callback(eval_key, "feedback_comment"))
        
        # 제출 버튼
        st.markdown(f"**아래 버튼을 클릭하여 평가를 제출하세요:**")
        submit_button_key = f"submit_{eval_key}"
        
        if st.button(submit_button_text, key=submit_button_key, use_container_width=True):
            try:
                # 상태 업데이트
                for field, widget_key in [
                    ("overall_score", overall_key),
                    ("relevance_score", relevance_key),
                    ("accuracy_score", accuracy_key),
                    ("completeness_score", completeness_key),
                    ("coherence_score", coherence_key),
                    ("helpfulness_score", helpfulness_key),
                    ("response_time_score", response_time_key),
                    ("feedback_comment", comment_key),
                    ("query_type", query_type_key),
                    ("domain", domain_key)
                ]:
                    if widget_key in st.session_state:
                        evaluation_state[field] = st.session_state[widget_key]
                
                # 모델 ID 검증
                if model_id is None:
                    st.error("모델 ID가 필요합니다.")
                    return evaluation_state
                
                # 수집기 준비 (세션 상태에 있거나 초기화)
                if application_name is not None and collector_session_key not in st.session_state:
                    init_response_evaluation_collector(
                        application_name=application_name,
                        trace_id=trace_id,
                        completion_id=completion_id,
                        collector_session_key=collector_session_key
                    )
                
                # 옵션 1: 세션에 저장된 수집기 사용
                if collector_session_key in st.session_state:
                    collector = st.session_state[collector_session_key]
                    
                    # 수집기에 트레이스 ID 및 완성 ID 업데이트
                    if trace_id is not None:
                        collector.update_trace_id(trace_id)
                    if completion_id is not None:
                        collector.update_completion_id(completion_id)
                    
                    # 평가 기록
                    result = collector.record_evaluation(
                        model_id=model_id,
                        overall_score=evaluation_state["overall_score"],
                        relevance_score=evaluation_state["relevance_score"],
                        accuracy_score=evaluation_state["accuracy_score"],
                        completeness_score=evaluation_state["completeness_score"],
                        coherence_score=evaluation_state["coherence_score"],
                        helpfulness_score=evaluation_state["helpfulness_score"],
                        response_time_score=evaluation_state["response_time_score"],
                        feedback_comment=evaluation_state["feedback_comment"],
                        query_type=evaluation_state["query_type"],
                        domain=evaluation_state["domain"],
                        kb_id=kb_id,
                        kb_name=kb_name,
                        kb_used_in_query=kb_used_in_query,
                        response_time_ms=response_time_ms,
                        total_tokens=total_tokens,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        evaluation_source=evaluation_source
                    )
                # 옵션 2: generic_response_evaluation 모듈의 함수 사용
                else:
                    result = send_evaluation(
                        model_id=model_id,
                        overall_score=evaluation_state["overall_score"],
                        application_name=application_name,
                        trace_id=trace_id,
                        completion_id=completion_id,
                        relevance_score=evaluation_state["relevance_score"],
                        accuracy_score=evaluation_state["accuracy_score"],
                        completeness_score=evaluation_state["completeness_score"],
                        coherence_score=evaluation_state["coherence_score"],
                        helpfulness_score=evaluation_state["helpfulness_score"],
                        response_time_score=evaluation_state["response_time_score"],
                        feedback_comment=evaluation_state["feedback_comment"],
                        query_type=evaluation_state["query_type"],
                        domain=evaluation_state["domain"],
                        kb_id=kb_id,
                        kb_name=kb_name,
                        kb_used_in_query=kb_used_in_query,
                        response_time_ms=response_time_ms,
                        total_tokens=total_tokens,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        temperature=temperature,
                        top_p=top_p,
                        evaluation_source=evaluation_source
                    )
                
                # 평가 상태 업데이트
                evaluation_state["submitted"] = True
                evaluation_state["show_eval_ui"] = True  # 제출 후에도 UI를 계속 보여주기 위함 (결과 표시)
                
                # 성공 메시지 표시
                st.success("평가가 성공적으로 제출되었습니다!")
                
                # 성공 콜백 호출 (있는 경우)
                if on_submit_success and callable(on_submit_success):
                    on_submit_success(result)
                
                # 페이지 새로고침 없이 UI 업데이트 (st.experimental_rerun 대신)
                # Streamlit 2023.1.0 이상에서는 st.rerun() 사용 가능
                try:
                    st.rerun()
                except:
                    try:
                        st.experimental_rerun()
                    except:
                        pass
                
            except Exception as e:
                st.error(f"평가 제출 중 오류: {str(e)}")
                logger.error(f"평가 제출 중 오류: {str(e)}", exc_info=True)
                
                # 오류 세부 정보를 개발자 모드에서만 표시
                import traceback
                st.code(traceback.format_exc())
                
    return evaluation_state

# 디버깅 UI 생성 - 개발자 모드
def create_evaluation_debug_ui(
    eval_key: str,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    model_id: Optional[str] = None,
    application_name: Optional[str] = None
) -> None:
    """
    평가 디버깅을 위한 UI를 생성합니다.
    
    :param eval_key: 평가 상태를 저장할 세션 상태 키
    :param trace_id: 트레이스 ID
    :param completion_id: 완성 ID 
    :param model_id: 모델 ID
    :param application_name: 애플리케이션 이름
    """
    if not STREAMLIT_AVAILABLE:
        raise ImportError("Streamlit이 설치되지 않았습니다. 'pip install streamlit'로 설치하세요.")
    # 디버그 로그 초기화
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    
    # 디버깅 정보 표시
    debug_expander_key = f"debug_expander_open_{eval_key}"
    debug_expander_open = st.session_state.get(debug_expander_key, False)
    debug_expander = st.expander("평가 디버깅 정보 (개발자용)", expanded=debug_expander_open)
    
    with debug_expander:
        st.markdown("### 평가 전송 정보")
        
        # 정보 표시
        st.markdown(f"""
        **애플리케이션 이름**: {application_name or "N/A"}
        **트레이스 ID**: {trace_id or "N/A"}
        **완성 ID**: {completion_id or "N/A"}
        **모델 ID**: {model_id or "N/A"}
        **현재 시간**: {int(time.time() * 1000)} (밀리초)
        """)
        
        # 로그 표시
        if st.session_state.debug_logs:
            log_text = "\n".join(st.session_state.debug_logs)
            st.text_area("전송 로그", log_text, height=200)
        else:
            st.info("아직 평가 전송 로그가 없습니다. 평가를 제출하면 여기에 로그가 표시됩니다.")
        
        # 로그 초기화 버튼
        reset_log_key = f"reset_log_{eval_key}"
        if st.button("로그 초기화", key=reset_log_key):
            st.session_state.debug_logs = []
            st.rerun()
        
        # 테스트 평가 전송 버튼
        test_key = f"test_eval_{eval_key}"
        if st.button("테스트 평가 전송", key=test_key):
            try:
                # 테스트 평가 전송 로그 기록
                test_time = int(time.time() * 1000)
                log_msg = f"[{test_time}] 테스트 평가 전송 시작..."
                st.session_state.debug_logs.append(log_msg)
                
                # 필수 정보 확인
                if not model_id:
                    raise ValueError("테스트 평가를 위한 모델 ID가 필요합니다.")
                
                if not application_name:
                    raise ValueError("테스트 평가를 위한 애플리케이션 이름이 필요합니다.")
                
                # 테스트 평가 전송
                from .generic_response_evaluation import send_evaluation_with_newrelic_agent
                
                test_result = send_evaluation_with_newrelic_agent(
                    model_id=model_id,
                    overall_score=8,
                    application_name=application_name,
                    trace_id=trace_id,
                    completion_id=completion_id,
                    relevance_score=8,
                    accuracy_score=8,
                    completeness_score=8,
                    coherence_score=8,
                    helpfulness_score=8,
                    response_time_score=8,
                    feedback_comment="테스트 평가 데이터",
                    query_type="테스트",
                    domain="테스트",
                    evaluation_source="streamlit-debug"
                )
                
                st.session_state.debug_logs.append(f"[{int(time.time() * 1000)}] 평가 ID: {test_result.get('id', 'unknown') if test_result else 'failed'}")
                st.session_state.debug_logs.append(f"[{int(time.time() * 1000)}] 전송 완료: {test_result}")
                
                st.success("테스트 평가가 성공적으로 전송되었습니다!")
                st.rerun()
                
            except Exception as e:
                error_msg = f"[{int(time.time() * 1000)}] 오류: {str(e)}"
                st.session_state.debug_logs.append(error_msg)
                st.error(f"테스트 평가 전송 중 오류 발생: {str(e)}")
                
                import traceback
                st.code(traceback.format_exc())
                st.rerun() 