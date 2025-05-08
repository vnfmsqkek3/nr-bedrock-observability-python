"""
Streamlit에서 AWS Bedrock과 New Relic 피드백 기능을 사용하는 예제

이 샘플 앱은 다음 기능을 보여줍니다:
1. Streamlit 인터페이스를 통한 AWS Bedrock 호출
2. LLM 응답에 대한 사용자 피드백 수집
3. 수집된 피드백을 New Relic에 전송

실행 방법:
```
streamlit run streamlit_feedback_demo.py
```
"""

import json
import time
import uuid
import boto3
import streamlit as st
import newrelic.agent
from nr_bedrock_observability import monitor_bedrock, create_feedback_collector

# 페이지 설정
st.set_page_config(
    page_title="Bedrock 피드백 데모",
    page_icon="🤖",
    layout="wide"
)

# 세션 상태 초기화
if "trace_id" not in st.session_state:
    st.session_state.trace_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_completion_id" not in st.session_state:
    st.session_state.current_completion_id = None
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False


# Bedrock 클라이언트 설정
@st.cache_resource
def get_bedrock_client(region_name='ap-northeast-2'):
    """캐시된 Bedrock 클라이언트 반환"""
    bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
    return monitor_bedrock(bedrock_client, {
        'application_name': 'Streamlit-Feedback-Demo',
        'collect_feedback': True
    })

# 피드백 수집기 생성
@st.cache_resource
def get_feedback_collector():
    """캐시된 피드백 수집기 반환"""
    return create_feedback_collector(
        application_name='Streamlit-Feedback-Demo',
        trace_id=st.session_state.trace_id
    )

# 대화 기록 표시
def display_chat_history():
    """대화 기록 표시"""
    for message in st.session_state.messages:
        role = message["role"]
        with st.chat_message(role):
            st.markdown(message["content"])

# 새 대화 시작 버튼
if st.sidebar.button("새 대화 시작"):
    st.session_state.messages = []
    st.session_state.trace_id = str(uuid.uuid4())
    st.session_state.feedback_shown = False
    feedback_collector = get_feedback_collector()
    feedback_collector.update_trace_id(st.session_state.trace_id)
    feedback_collector.reset_feedback()
    st.rerun()

# 사이드바에 정보 표시
st.sidebar.title("Bedrock 피드백 데모")
st.sidebar.info(
    "이 데모는 Streamlit에서 AWS Bedrock을 사용하고 "
    "사용자 피드백을 수집하여 New Relic에 전송하는 방법을 보여줍니다."
)

# 모델 선택
model_options = {
    "Claude 3 Sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "Claude 3 Haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "Claude 3.5 Sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0"
}
selected_model = st.sidebar.selectbox("모델 선택", list(model_options.keys()))
model_id = model_options[selected_model]

# 현재 트레이스 ID 표시
st.sidebar.subheader("트레이스 정보")
st.sidebar.code(f"트레이스 ID: {st.session_state.trace_id}")
if st.session_state.current_completion_id:
    st.sidebar.code(f"완성 ID: {st.session_state.current_completion_id}")

# 메인 인터페이스
st.title("�� AWS Bedrock 채팅 + 피드백 데모")

# 대화 기록 표시
display_chat_history()

# 사용자 입력
user_input = st.chat_input("무엇이든 물어보세요!")

# 사용자 입력이 있으면 처리
if user_input:
    # 사용자 메시지 추가
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 완성 ID 생성
    completion_id = str(uuid.uuid4())
    st.session_state.current_completion_id = completion_id
    
    # 피드백 수집기 업데이트
    feedback_collector = get_feedback_collector()
    feedback_collector.update_completion_id(completion_id)
    
    # 피드백 상태 초기화
    st.session_state.feedback_shown = False
    
    # 모델 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                # Bedrock 클라이언트 가져오기
                bedrock = get_bedrock_client()
                
                # 모델 호출
                response = bedrock.invoke_model(
                    modelId=model_id,
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [
                            {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다. 간결하고 정확하게 대답해주세요."},
                            *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages if m["role"] == "user"]
                        ],
                        "temperature": 0.7
                    })
                )
                
                # 응답 처리
                response_body = json.loads(response['body'].read().decode('utf-8'))
                assistant_response = ""
                
                if "content" in response_body and len(response_body["content"]) > 0:
                    for content_item in response_body["content"]:
                        if content_item["type"] == "text":
                            assistant_response += content_item["text"]
                
                # 어시스턴트 메시지 표시
                st.markdown(assistant_response)
                
                # 메시지 저장
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")

# 피드백 컴포넌트 - 마지막 메시지가 있고 아직 피드백을 제출하지 않은 경우에만 표시
if st.session_state.messages and len(st.session_state.messages) >= 2 and st.session_state.messages[-1]["role"] == "assistant":
    feedback_collector = get_feedback_collector()
    
    if st.session_state.current_completion_id:
        feedback_collector.update_completion_id(st.session_state.current_completion_id)
    
    # 피드백이 아직 표시되지 않은 경우에만 표시
    if not st.session_state.feedback_shown:
        st.subheader("응답 평가")
        feedback_result = feedback_collector.render_feedback_ui(key=f"feedback_{st.session_state.current_completion_id}")
        
        # 피드백이 제출되면 상태 업데이트
        if feedback_result:
            st.session_state.feedback_shown = True

# 푸터
st.markdown("---")
st.markdown(
    "이 데모는 nr-bedrock-observability-python 라이브러리를 사용하여 "
    "New Relic에 AWS Bedrock 호출 데이터와 사용자 피드백을 전송합니다."
) 