"""
AWS Bedrock 모니터링 애플리케이션 (Streamlit) - Knowledge Base 없이 직접 Bedrock 호출

이 앱은 AWS Bedrock API 호출을 모니터링하고 NewRelic에 데이터를 전송합니다.
지식 기반 없이 Claude 3.5 Sonnet 모델을 직접 사용하여 질문에 답변하고 사용자 피드백을 수집합니다.
"""

import streamlit as st
import boto3
import json
import uuid
import time
import os
import newrelic.agent
from nr_bedrock_observability import (
    monitor_bedrock, 
    # 평가 수집 도구
    init_response_evaluation_collector,
    ensure_evaluation_state,
    update_evaluation_state,
    create_update_callback,
    create_evaluation_ui,
    create_evaluation_debug_ui,
    send_evaluation_with_newrelic_agent,
    get_evaluation_collector,
    reset_evaluation_collector,
    # 새로 추가된 대시보드 헬퍼 함수
    record_role_based_events,
    # record_search_results,  # Knowledge Base 없이는 사용하지 않음
    record_bedrock_response,
    extract_claude_response_text,
    get_sample_nrql_queries,
    # search_knowledge_base  # Knowledge Base 없이는 사용하지 않음
)

# NewRelic 라이센스 키 설정 - 실제 환경에서는 환경 변수나 보안 방식으로 관리해야 합니다

# 상수 정의
REGION = "ap-northeast-2"
MODEL_ID = "anthropic.claude-3-5-sonnet-20240620-v1:0"
# KNOWLEDGE_BASE_ID = "VNJYWIISJU"  # Knowledge Base 없이는 사용하지 않음
# KNOWLEDGE_BASE_NAME = "knowledge-base-quick-start-ycffx"  # Knowledge Base 없이는 사용하지 않음
APP_NAME = "Bedrock-Direct-Monitoring-App-nokb"

# 페이지 설정
st.set_page_config(
    page_title="Bedrock 모니터링 앱 (직접 호출)",
    page_icon="🤖",
    layout="wide"
)

# 뉴렐릭 설정 확인
try:
    nr_app = newrelic.agent.application()
    if nr_app:
        st.success(f"뉴렐릭 애플리케이션이 성공적으로 초기화되었습니다: {nr_app.name}")
    else:
        st.warning(f"뉴렐릭 애플리케이션을 찾을 수 없습니다. 라이센스 키를 확인하세요: {os.environ.get('NEW_RELIC_LICENSE_KEY', '').replace('FFFFNRAL', '****')}")
except Exception as e:
    st.error(f"뉴렐릭 초기화 오류: {str(e)}")

# 세션 상태 초기화
if "trace_id" not in st.session_state:
    st.session_state.trace_id = str(uuid.uuid4())
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_completion_id" not in st.session_state:
    st.session_state.current_completion_id = None
if "raw_result" not in st.session_state:
    st.session_state.raw_result = {}
# Knowledge Base 관련 세션 상태는 사용하지 않음
# if "current_search_results" not in st.session_state:
#     st.session_state.current_search_results = []
if "current_system_prompt" not in st.session_state:
    st.session_state.current_system_prompt = ""
if "message_count" not in st.session_state:
    st.session_state.message_count = 0

# 평가 수집기 초기화
if "response_evaluation_collector" not in st.session_state:
    try:
        # 새로운 평가 수집기 초기화
        init_response_evaluation_collector(
            application_name=APP_NAME,
            trace_id=st.session_state.trace_id,
            completion_id=None,
            session_id=st.session_state.conversation_id,
            collector_session_key="response_evaluation_collector"
        )
    except Exception as e:
        st.warning(f"평가 수집기 초기화 중 오류: {str(e)}")

# Bedrock 클라이언트 설정
@st.cache_resource
def get_bedrock_client():
    """Bedrock 런타임 클라이언트를 생성하고 모니터링 설정"""
    bedrock_client = boto3.client('bedrock-runtime', region_name=REGION)
    monitored_client = monitor_bedrock(bedrock_client, {
        'application_name': APP_NAME,
        'new_relic_api_key': os.environ.get("NEW_RELIC_LICENSE_KEY")
    })
    return monitored_client

# Knowledge Base 없이 직접 Bedrock 호출하는 워크플로우
def run_direct_bedrock_workflow(user_query):
    """직접 Bedrock 워크플로우 실행: Knowledge Base 없이 Claude 3.5 Sonnet에 직접 질문"""
    start_time = time.time()
    
    # 새 완성 ID 생성하고 기존 대화 ID 유지
    trace_id = str(uuid.uuid4())
    completion_id = str(uuid.uuid4())
    conversation_id = st.session_state.conversation_id
    st.session_state.current_completion_id = completion_id
    st.session_state.message_count += 1
    message_index = st.session_state.message_count
    
    # 트레이스 ID 디버깅 출력
    st.info(f"직접 호출 - 대화 ID: {conversation_id}, 트레이스 ID: {trace_id}, 완성 ID: {completion_id}, 메시지 순서: {message_index}")
    
    # 응답 평가 수집기 초기화 또는 업데이트
    try:
        init_response_evaluation_collector(
            application_name=APP_NAME,
            trace_id=trace_id,
            completion_id=completion_id,
            user_id=None,
            session_id=conversation_id
        )
    except Exception as e:
        st.warning(f"응답 평가 수집기 초기화 중 오류: {str(e)}")
    
    # Knowledge Base 검색 단계는 생략
    # 시스템 프롬프트와 사용자 쿼리 구성
    system_prompt = "당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 명확하고 정확하게 답변해주세요. 한국어로 답변해주세요."
    
    # 시스템 프롬프트 저장
    st.session_state.current_system_prompt = system_prompt
    
    # 사용자 쿼리를 직접 사용 (Knowledge Base 컨텍스트 없이)
    user_content = user_query
    
    # 역할별 이벤트 기록 - Knowledge Base 검색 결과 없이
    record_role_based_events(
        user_query=user_query,
        system_prompt=system_prompt,
        search_results=[],  # 검색 결과 없음
        context_text="",    # 컨텍스트 없음
        trace_id=trace_id,
        completion_id=completion_id,
        application_name=APP_NAME,
        conversation_id=conversation_id,
        message_index=message_index
    )
    
    # Knowledge Base 검색 결과 기록은 생략
    # record_search_results(...) 호출 없음
    
    # Bedrock 요청 구성 - Claude 3.5 Sonnet 형식에 맞춤
    request = {
        'modelId': MODEL_ID,
        'body': json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            'max_tokens': 1000,
            'temperature': 0.3,
            'top_p': 0.9,
            'system': system_prompt,
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {
                            'type': 'text',
                            'text': user_content
                        }
                    ]
                }
            ]
        })
    }
    
    # 모델 파라미터 추출 (temperature와 top_p)
    request_body = json.loads(request['body'])
    temperature = request_body.get('temperature', 0.3)
    top_p = request_body.get('top_p', 0.9)
    
    # Bedrock 요청 실행
    try:
        # Bedrock 호출
        bedrock_client = get_bedrock_client()
        response = bedrock_client.invoke_model(**request)
        response_body = json.loads(response['body'].read().decode('utf-8'))
        
        # 응답 텍스트 추출 - 라이브러리 함수 사용
        assistant_response = extract_claude_response_text(response_body)
        
        # Bedrock 응답을 New Relic에 기록 - Knowledge Base 정보 없이
        record_bedrock_response(
            assistant_response=assistant_response,
            response_body=response_body,
            trace_id=trace_id,
            completion_id=completion_id,
            application_name=APP_NAME,
            model_id=MODEL_ID,
            kb_id=None,  # Knowledge Base 없음
            kb_name=None,  # Knowledge Base 없음
            conversation_id=conversation_id,
            message_index=message_index,
            response_time_ms=int((time.time() - start_time) * 1000),
            temperature=temperature,
            top_p=top_p
        )
        
        # 토큰 사용량 추출 - Claude 3.5 호환
        usage = response_body.get("usage", {})
        # 일반 Bedrock 토큰 필드 확인
        total_tokens = usage.get("total_token_count", 0)
        input_tokens = usage.get("input_token_count", 0)
        output_tokens = usage.get("output_token_count", 0)
        
        # Claude 3.5 토큰 필드 확인
        if total_tokens == 0:
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens
        
        # 전체 처리 완료 시간 측정
        total_duration = int((time.time() - start_time) * 1000)  # 밀리초로 변환
        
        return assistant_response, {
            # "search_results": [],  # 검색 결과 없음
            # "search_time_ms": 0,   # 검색 시간 없음
            "llm_time_ms": total_duration,
            "total_time_ms": total_duration,
            "trace_id": trace_id,
            "completion_id": completion_id,
            "token_count": output_tokens,
            "total_tokens": total_tokens,
            "prompt_tokens": input_tokens,
            "model_id": MODEL_ID,
            "kb_id": None,  # Knowledge Base 없음
            "kb_name": None,  # Knowledge Base 없음
            "kb_used_in_query": False,  # Knowledge Base 사용 안함
            "response_time_ms": total_duration,
            "temperature": temperature,
            "top_p": top_p
        }
        
    except Exception as e:
        st.error(f"Bedrock 호출 오류: {str(e)}")
        return None, None

# UI 구성 함수
def build_ui():
    """Streamlit UI 구성"""
    st.title("🤖 AWS Bedrock 직접 호출 Q&A + 모니터링")
    
    # 레이아웃: 메인 컬럼과 사이드바
    main_col, info_col = st.columns([2, 1])
    
    with info_col:
        st.header("앱 정보")
        st.markdown(f"""
        **모델**: {MODEL_ID}
        
        **Knowledge Base**: 사용 안함 (직접 호출)
        
        **리전**: {REGION}
        
        **NewRelic 앱 이름**: {APP_NAME}
        """)
        
        # 트레이스 정보
        st.subheader("트레이스 정보")
        
        # ID 설명 추가
        with st.expander("ID 설명", expanded=True):
            st.markdown("""
            **대화 ID (Conversation ID)**: 사용자의 전체 대화 세션을 식별하는 고유 ID입니다. 새로운 대화 세션이 시작될 때 생성되며, 사용자가 여러 메시지를 주고받는 동안 동일하게 유지됩니다. 전체 대화 흐름을 추적할 때 사용됩니다.
            
            **트레이스 ID (Trace ID)**: 각 메시지 교환을 추적하기 위한 ID입니다. 새로운 사용자 입력이 있을 때마다 새로운 트레이스 ID가 생성됩니다. 단일 요청의 전체 처리 과정(Bedrock 직접 호출)을 추적하는 데 사용됩니다.
            
            **완성 ID (Completion ID)**: LLM 응답 완성에 대한 고유 ID입니다. Bedrock API 호출의 결과를 식별하고 추적하는 데 사용됩니다. 각 완성은 특정 사용자 질문에 대한 모델의 응답을 나타냅니다.
            """)
        
        st.code(f"대화 ID: {st.session_state.conversation_id}")
        st.code(f"트레이스 ID: {st.session_state.trace_id}")
        if st.session_state.current_completion_id:
            st.code(f"완성 ID: {st.session_state.current_completion_id}")
            
            # 모델 평가 분석 NRQL 예시 추가
            with st.expander("모델 평가 분석 쿼리", expanded=False):
                st.markdown("### 모델 평가 데이터 분석을 위한 NRQL 쿼리")
                
                # 라이브러리 함수를 사용하여 샘플 쿼리 가져오기 (Knowledge Base ID 없이)
                sample_queries = get_sample_nrql_queries(
                    trace_id=st.session_state.trace_id,
                    completion_id=st.session_state.current_completion_id,
                    conversation_id=st.session_state.conversation_id,
                    kb_id=None  # Knowledge Base 없음
                )
                
                # 쿼리 결과가 없는 이유에 대한 설명 추가
                st.warning("""
                **참고**: 쿼리 결과가 없는 경우 다음과 같은 이유가 있을 수 있습니다:
                
                1. 아직 평가 데이터가 수집되지 않았습니다. 먼저 몇 개의 모델 평가를 제출해보세요.
                2. 이벤트 타입 이름이 실제 New Relic에 기록된 이름과 다를 수 있습니다.
                3. New Relic 계정 설정에서 사용자 정의 이벤트 수집이 활성화되어 있는지 확인하세요.
                4. 시간 범위를 더 넓게 설정하여 확인해 보세요.
                
                평가 제출 후 데이터가 New Relic에 표시되는 데 약간의 시간이 걸릴 수 있습니다.
                """)
                
                # 샘플 쿼리 표시
                for title, query in sample_queries.items():
                    st.markdown(f"**{title}:**")
                    st.code(query)
        
        # 시스템 프롬프트 표시
        if st.session_state.current_system_prompt:
            with st.expander("시스템 프롬프트", expanded=False):
                st.code(st.session_state.current_system_prompt)
        
        # Knowledge Base 검색 결과는 표시하지 않음 (검색 안함)
        # if st.session_state.current_search_results:
        #     with st.expander("검색 결과", expanded=False):
        #         ...
        
        # 실행 정보 표시
        if st.session_state.raw_result:
            with st.expander("실행 정보", expanded=False):
                # st.metric("검색 시간", f"{st.session_state.raw_result.get('search_time_ms', 0)} ms")
                st.metric("LLM 응답 시간", f"{st.session_state.raw_result.get('llm_time_ms', 0)} ms")
                st.metric("총 처리 시간", f"{st.session_state.raw_result.get('total_time_ms', 0)} ms")
                st.metric("토큰 수", st.session_state.raw_result.get('token_count', 0))
        
        # 새 대화 시작 버튼
        if st.button("새 대화 시작"):
            # 이전 평가 상태 키를 모두 찾아서 초기화
            eval_keys = [key for key in st.session_state.keys() if key.startswith("eval_")]
            for key in eval_keys:
                del st.session_state[key]
                
            # 이전 슬라이더/위젯 키 초기화
            widget_keys = [key for key in st.session_state.keys() if 
                          any(key.startswith(prefix) for prefix in 
                              ["overall_score_", "relevance_score_", "accuracy_score_", 
                               "completeness_score_", "coherence_score_", "helpfulness_score_",
                               "response_time_score_", "query_type_", "domain_", "feedback_comment_",
                               "submit_", "reset_log_", "test_eval_"])]
            for key in widget_keys:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 기본 세션 상태 초기화
            st.session_state.trace_id = str(uuid.uuid4())
            st.session_state.conversation_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.current_completion_id = None
            st.session_state.raw_result = {}
            # st.session_state.current_search_results = []  # Knowledge Base 없으니 사용 안함
            st.session_state.current_system_prompt = ""
            st.session_state.message_count = 0
            
            # 응답 평가 수집기 초기화
            try:
                # 응답 평가 수집기 세션 상태 초기화
                if "response_evaluation_collector" in st.session_state:
                    # 라이브러리 함수 사용하여 평가 수집기 초기화
                    reset_evaluation_collector(collector_session_key="response_evaluation_collector")
                
                # 새로운 수집기 초기화
                init_response_evaluation_collector(
                    application_name=APP_NAME,
                    trace_id=st.session_state.trace_id,
                    completion_id=None,
                    session_id=st.session_state.conversation_id,
                    collector_session_key="response_evaluation_collector"
                )
            except Exception as e:
                st.warning(f"평가 수집기 초기화 중 오류: {str(e)}")
                
            st.rerun()
    
    with main_col:
        # 채팅 기록 표시
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # 사용자 입력
        user_input = st.chat_input("질문을 입력하세요")
        
        if user_input:
            # 사용자 메시지 표시 (원본 질문만 표시)
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # 메시지 저장 (원본 질문만 저장)
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # 응답 생성 - Knowledge Base 없이 직접 Bedrock 호출
            with st.chat_message("assistant"):
                with st.spinner("답변 생성 중..."):
                    response, result_info = run_direct_bedrock_workflow(user_input)
                    
                    if response:
                        st.markdown(response)
                        
                        # 결과 정보 저장
                        st.session_state.raw_result = result_info
                        
                        # 메시지 저장
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                        # 응답 평가 수집기 업데이트
                        try:
                            if result_info:
                                # 수집기 업데이트
                                init_response_evaluation_collector(
                                    application_name=APP_NAME,
                                    trace_id=result_info.get('trace_id'),
                                    completion_id=result_info.get('completion_id'),
                                    session_id=st.session_state.conversation_id,
                                    collector_session_key="response_evaluation_collector"
                                )
                        except Exception as e:
                            st.warning(f"응답 평가 수집기 업데이트 중 오류: {str(e)}")
                            
                    else: # if response (no response generated)
                        st.warning("모델로부터 응답을 받지 못했습니다.")
                # 여기서 with st.spinner 끝
            # 여기서 with st.chat_message("assistant") 끝
        # 여기서 if user_input 끝

    # --- 모델 응답 평가 UI 섹션 ---
    # 가장 마지막 메시지가 어시스턴트의 응답일 경우에만 평가 UI를 표시합니다.
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
        
        eval_key = f"eval_{st.session_state.message_count}"
        
        # 현재 raw_result 정보를 안전하게 가져오기
        current_raw_result = st.session_state.get("raw_result", {})
        
        # 평가 섹션 표시
        st.markdown("### 모델 응답 평가")
        
        # 라이브러리 함수를 사용한 Streamlit 응답 평가 UI - Knowledge Base 정보 없이
        try:
            create_evaluation_ui(
                eval_key=eval_key,
                trace_id=current_raw_result.get('trace_id'),
                completion_id=current_raw_result.get('completion_id'),
                model_id=MODEL_ID,
                kb_id=None,  # Knowledge Base 없음
                kb_name=None,  # Knowledge Base 없음
                kb_used_in_query=False,  # Knowledge Base 사용 안함
                response_time_ms=current_raw_result.get('total_time_ms'),
                total_tokens=current_raw_result.get('total_tokens'),
                prompt_tokens=current_raw_result.get('prompt_tokens'),
                completion_tokens=current_raw_result.get('token_count'),
                temperature=current_raw_result.get('temperature'),
                top_p=current_raw_result.get('top_p'),
                application_name=APP_NAME,
                use_number_input=True,  # 슬라이더 대신 숫자 입력 사용
                submit_button_text="평가 제출",
                evaluation_source="streamlit"
            )
        except Exception as e:
            st.error(f"평가 UI 생성 중 오류 발생: {str(e)}")
            # 기본 평가 UI 대신 수동 평가 제출 폼 표시
            st.write("대체 평가 방식을 사용합니다:")
            with st.form("manual_evaluation_form"):
                overall_score = st.number_input("전체 만족도", min_value=1, max_value=10, value=5)
                relevance = st.number_input("질문 관련성", min_value=1, max_value=10, value=5)
                accuracy = st.number_input("정확성", min_value=1, max_value=10, value=5)
                submit = st.form_submit_button("평가 제출")
                
                if submit:
                    try:
                        # 수동으로 평가 제출 - 라이브러리 함수 직접 사용 (Knowledge Base 정보 없이)
                        evaluation_data = {
                            "model_id": MODEL_ID,
                            "overall_score": overall_score,
                            "relevance_score": relevance,
                            "accuracy_score": accuracy,
                            "kb_id": None,  # Knowledge Base 없음
                            "kb_name": None,  # Knowledge Base 없음
                            "evaluation_source": "streamlit-manual",
                            "trace_id": current_raw_result.get('trace_id'),
                            "completion_id": current_raw_result.get('completion_id'),
                            "temperature": current_raw_result.get('temperature'),
                            "top_p": current_raw_result.get('top_p'),
                            "application_name": APP_NAME
                        }
                        
                        result = send_evaluation_with_newrelic_agent(
                            event_data=evaluation_data,
                            event_type="LlmUserResponseEvaluation"
                        )
                        
                        if result:
                            st.success("평가가 성공적으로 제출되었습니다!")
                    except Exception as submit_error:
                        st.error(f"평가 제출 중 오류: {str(submit_error)}")
        
        # 개발자 도구
        st.markdown("### 개발자 도구")
        show_debug = st.checkbox("디버깅 정보 표시", value=False, key=f"show_debug_{eval_key}")
        
        if show_debug:
            # 간단한 디버깅 정보 직접 표시
            st.code(f"""
            트레이스 ID: {current_raw_result.get('trace_id')}
            완성 ID: {current_raw_result.get('completion_id')}
            모델 ID: {MODEL_ID}
            응답 시간: {current_raw_result.get('total_time_ms')} ms
            총 토큰: {current_raw_result.get('total_tokens')}
            Knowledge Base 사용: 없음 (직접 호출)
            """)
            
            # 수동 테스트 평가 전송 버튼
            if st.button("테스트 평가 전송", key=f"test_eval_manual_{eval_key}"):
                try:
                    # 테스트 평가 제출 - 라이브러리 함수 직접 사용 (Knowledge Base 정보 없이)
                    evaluation_data = {
                        "model_id": MODEL_ID,
                        "overall_score": 8,
                        "kb_id": None,  # Knowledge Base 없음
                        "kb_name": None,  # Knowledge Base 없음
                        "evaluation_source": "streamlit-manual-test",
                        "trace_id": current_raw_result.get('trace_id'),
                        "completion_id": current_raw_result.get('completion_id'),
                        "temperature": current_raw_result.get('temperature'),
                        "top_p": current_raw_result.get('top_p'),
                        "application_name": APP_NAME
                    }
                    
                    test_result = send_evaluation_with_newrelic_agent(
                        event_data=evaluation_data,
                        event_type="LlmUserResponseEvaluation"
                    )
                    
                    if test_result:
                        st.success(f"테스트 평가 전송 성공: ID={test_result.get('id')}")
                except Exception as e:
                    st.error(f"테스트 평가 전송 오류: {str(e)}")

    # 푸터
    st.markdown("---")
    st.markdown(
        "이 앱은 nr-bedrock-observability-python v2.0.2 라이브러리를 사용하여 "
        "AWS Bedrock API 직접 호출을 모니터링하며, "
        "Knowledge Base 없이 Claude 3.5 Sonnet 모델과 직접 대화할 수 있습니다. "
        "temperature와 top_p 파라미터를 포함한 토큰 처리와 이벤트 수집이 개선된 Streamlit 평가 UI를 제공합니다."
    )

if __name__ == "__main__":
    build_ui() 