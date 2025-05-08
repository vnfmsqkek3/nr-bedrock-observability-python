# New Relic AWS Bedrock Observability for Python

AWS Bedrock API 호출을 모니터링하고 성능 지표를 New Relic에 전송하는 라이브러리입니다.

## 최신 업데이트 (v1.3.0)

- **Streamlit 피드백 기능 추가**:
  - Streamlit 애플리케이션에서 사용자 피드백을 쉽게 수집
  - 시각적인 피드백 UI 컴포넌트 제공 (긍정, 중립, 부정 반응)
  - 사용자 피드백 데이터를 New Relic에 자동 전송
  - 피드백 데이터와 LLM 응답 트레이스 자동 연결

- **역할별 메시지 분리 기능 (v1.2.0)**:
  - 시스템 프롬프트를 별도의 이벤트로 분리하여 기록
  - 사용자 프롬프트를 별도의 이벤트로 분리하여 기록
  - OpenSearch 검색 결과를 별도의 이벤트로 분리하여 기록
  - RAG 컨텍스트를 별도의 이벤트로 분리하여 기록

## 업데이트 히스토리

### v1.3.0
- Streamlit 애플리케이션에서 사용자 피드백을 쉽게 수집하는 기능 추가
- 시각적인 피드백 UI 컴포넌트 제공 (긍정, 중립, 부정 반응)
- 피드백 데이터를 New Relic에 자동 전송 및 LLM 응답 트레이스와 연결
- 샘플 Streamlit 애플리케이션 제공

### v1.2.0
- 역할별 메시지 분리 기능 추가 (시스템/사용자 프롬프트, OpenSearch 결과, RAG 컨텍스트)
- 전체 워크플로우 트레이싱 연결 기능 개선
- New Relic NRQL 쿼리를 통한 분석 지원

### v1.1.2
- Streamlit 환경에서 발생하는 "Attempt to save a trace from an inactive transaction" 오류 해결
- 각 API 호출 전에 현재 활성 트랜잭션 확인
- 활성 트랜잭션이 없는 경우에만 새 트랜잭션 생성
- 트랜잭션 시작과 종료를 명확하게 관리 및 예외 처리 강화

### v1.1.1
- Streamlit 환경에서의 New Relic 트랜잭션 관리 개선
- 멀티스레딩 환경에서의 트랜잭션 처리 안정성 향상
- 비활성 트랜잭션 저장 시도로 인한 에러 방지
- 트랜잭션 초기화 및 종료 시 예외 처리 강화

### v1.1.0
- 사용자 피드백 수집 기능 추가
- 피드백 타입 지원 (positive, negative, neutral)
- 감정 점수 지원 (-1.0 ~ 1.0)
- 피드백 메시지 수집 기능
- 피드백 콜백 함수를 통한 사용자 정의 피드백 수집 지원
- New Relic 이벤트에 피드백 데이터 자동 포함

### v1.0.3
- Claude 3.5 Sonnet v2 최신 버전(anthropic.claude-3-5-sonnet-20241022-v2:0) 모델 지원 강화
- 내부 모델 맵핑 테이블의 일관성 개선
- 모든 모듈에서 신규 모델 ID 인식 가능하도록 업데이트
- RAG 워크플로우 트레이싱 샘플 코드 추가: 사용자 질문 → OpenSearch 검색 → Bedrock LLM 응답을 하나의 트레이스로 연결

### v1.0.2
- Claude 3.5 Sonnet 최신 버전(anthropic.claude-3-5-sonnet-20241022-v2:0) 지원 추가
- 모델 ID 추적 및 인식 기능 개선
- 내부 모델 매핑 테이블 업데이트

### v1.0.1
- 안정성 강화 및 내부 오류 처리 개선
- Streaming 응답을 처리한 후에도 응답 본문을 보존 가능하도록 구조 변경
- `StreamingBody` 처리 시 `BytesIO` 활용하여 이중 소비 방지
- New Relic 커스텀 이벤트 전송 성능 개선
- `generate_with_model()` 등 신규 Bedrock API 지원 강화

### v0.3.3
- 응답 데이터를 소비하지 않는 기능 추가: StreamingBody 객체를 복제하여 원본 보존
- io.BytesIO를 사용한 응답 스트림 복사 구현
- 모니터링 데이터 추출 시 원본 응답 객체를 보존하는 방식으로 개선
- seek/tell 메서드를 활용한 스트림 위치 복원 기능 추가

### v0.3.0
- 팩토리 패턴을 사용한 이벤트 생성 로직 개선
- 테스트 안정성 향상 및 CI/CD 파이프라인 개선
- 재귀 호출 문제 해결
- `CommonSummaryAttributes` 클래스 추가로 이벤트 데이터 표준화
- AWS 리전 지정 필요성 명시
- API 키가 없는 환경에서도 테스트용 키로 실행 가능
- New Relic 트랜잭션 관리 기능 추가로 이벤트 로깅 안정성 향상

## 설치 방법

### pip 설치

```bash
pip install -i https://test.pypi.org/simple/ nr-bedrock-observability
```

### Streamlit 지원 추가

```bash
pip install -i https://test.pypi.org/simple/ nr-bedrock-observability[streamlit]
```

## 기본 사용법

### 1. AWS Bedrock 클라이언트 모니터링

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock

# Bedrock 클라이언트 생성 (반드시 리전 지정)
bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')

# 모니터링 설정
monitored_client = monitor_bedrock(bedrock_client, {
    'application_name': 'MyApp',  # 필수
    'new_relic_api_key': 'YOUR_NEW_RELIC_API_KEY',  # 선택적 (환경변수 사용 가능)
})

# 평소처럼 Bedrock API 호출
response = monitored_client.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "인공지능의 역사를 간략하게 설명해줘."
                    }
                ]
            }
        ],
        "temperature": 0.7
    })
)

# 응답 처리
response_body = json.loads(response['body'].read().decode('utf-8'))
if "content" in response_body and len(response_body["content"]) > 0:
    for content_item in response_body["content"]:
        if content_item["type"] == "text":
            print(content_item["text"])
```

### 2. 스트리밍 API 사용

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock

# Bedrock 클라이언트 생성
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')

# 모니터링 설정
monitored_client = monitor_bedrock(bedrock, {
    'application_name': 'MyStreamingApp',
})

# 스트리밍 응답으로 모델 호출
stream_response = monitored_client.invoke_model_with_response_stream(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "인공지능 발전의 미래에 대해 설명해줘."
                    }
                ]
            }
        ],
        "temperature": 0.7
    })
)

# 스트리밍 응답 처리
for event in stream_response['body']:
    chunk_bytes = event['chunk']['bytes']
    chunk_str = chunk_bytes.decode('utf-8')
    
    try:
        chunk = json.loads(chunk_str)
        if 'content' in chunk and len(chunk['content']) > 0:
            for content_item in chunk['content']:
                if content_item.get('type') == 'text':
                    chunk_text = content_item.get('text', '')
                    print(chunk_text, end='', flush=True)
    except json.JSONDecodeError:
        print(f"JSON 파싱 오류: {chunk_str}")
```

### 3. 사용자 피드백 수집

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock

# 피드백 콜백 함수 정의
def feedback_callback(input_text, output_text):
    """사용자로부터 피드백을 수집하는 콜백 함수"""
    # 여기서 실제로는 UI에서 사용자로부터 피드백을 수집
    # 예제에서는 하드코딩된 값 반환
    return {
        'feedback': 'positive',  # 'positive', 'negative', 'neutral'
        'sentiment': 0.8,  # -1.0에서 1.0 사이의 값
        'feedback_message': '답변이 매우 유용했습니다.'
    }

# Bedrock 클라이언트 생성
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')

# 모니터링 설정 - 피드백 수집 활성화
monitored_client = monitor_bedrock(bedrock, {
    'application_name': 'MyFeedbackApp',
    'collect_feedback': True,  # 피드백 수집 활성화
    'feedback_callback': feedback_callback  # 피드백 콜백 함수 지정
})

# 모델 호출
response = monitored_client.invoke_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "머신러닝과 딥러닝의 차이점은 무엇인가요?"
                    }
                ]
            }
        ],
        "temperature": 0.7
    })
)

# 응답 처리
response_body = json.loads(response['body'].read().decode('utf-8'))
if "content" in response_body and len(response_body["content"]) > 0:
    for content_item in response_body["content"]:
        if content_item["type"] == "text":
            print(content_item["text"])
```

### 4. RAG 워크플로우 모니터링

```python
import boto3
import json
import newrelic.agent
from nr_bedrock_observability import monitor_bedrock, monitor_opensearch_results, link_rag_workflow

# Bedrock 클라이언트 생성
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')

# 모니터링 설정
monitored_client = monitor_bedrock(bedrock, {
    'application_name': 'MyRagApp',
})

# 사용자 질문
user_query = "인공지능 윤리에 대해 설명해주세요."

# OpenSearch 검색 (가상 예제)
opensearch_results = [
    {
        'title': 'AI 윤리 소개',
        'content': 'AI 윤리는 인공지능 기술의 개발과 사용에 관련된 윤리적 고려사항을 다룹니다.',
        'score': 0.95
    },
    {
        'title': 'AI 편향성 문제',
        'content': '인공지능 시스템의 편향성 문제는 훈련 데이터에 존재하는 사회적 편견이 반영될 수 있다는 점입니다.',
        'score': 0.85
    }
]

# OpenSearch 결과를 NewRelic에 기록
monitor_opensearch_results(
    opensearch_client=None,  # 실제로는 OpenSearch 클라이언트
    query=user_query,
    results=opensearch_results,
    application_name='MyRagApp'
)

# Bedrock 요청 구성
request = {
    'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0',
    'body': json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [
            {
                "role": "system",
                "content": "주어진 컨텍스트에 기반하여 정확하게 답변해주세요."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
                        다음 정보에 기반하여 질문에 답변해주세요:
                        
                        컨텍스트:
                        - 제목: AI 윤리 소개
                          내용: AI 윤리는 인공지능 기술의 개발과 사용에 관련된 윤리적 고려사항을 다룹니다.
                        
                        - 제목: AI 편향성 문제
                          내용: 인공지능 시스템의 편향성 문제는 훈련 데이터에 존재하는 사회적 편견이 반영될 수 있다는 점입니다.
                        
                        질문: {user_query}
                        """
                    }
                ]
            }
        ],
        "temperature": 0.7
    })
}

# RAG 워크플로우 연결 (트레이스 ID 생성 및 OpenSearch 결과 기록)
trace_id = link_rag_workflow(
    user_query=user_query,
    opensearch_results=opensearch_results,
    bedrock_client=monitored_client,
    bedrock_request=request,
    application_name='MyRagApp'
)

# Claude 3 호출 (트레이스 ID와 컨텍스트가 자동으로 연결됨)
response = monitored_client.invoke_model(**request)

# 응답 처리
response_body = json.loads(response['body'].read().decode('utf-8'))
if "content" in response_body and len(response_body["content"]) > 0:
    for content_item in response_body["content"]:
        if content_item["type"] == "text":
            print(content_item["text"])

print(f"트레이스 ID: {trace_id}")  # New Relic에서 트레이스 확인 시 사용
```

### 5. Streamlit에서 피드백 수집

```python
import streamlit as st
import boto3
import json
import uuid
from nr_bedrock_observability import monitor_bedrock, create_feedback_collector

# 페이지 설정
st.set_page_config(page_title="Bedrock 피드백 데모", page_icon="🤖")

# 세션 상태 초기화
if "trace_id" not in st.session_state:
    st.session_state.trace_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_completion_id" not in st.session_state:
    st.session_state.current_completion_id = None

# Bedrock 클라이언트 설정
@st.cache_resource
def get_bedrock_client(region_name='ap-northeast-2'):
    bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)
    return monitor_bedrock(bedrock_client, {
        'application_name': 'Streamlit-Feedback-Demo',
    })

# 피드백 수집기 생성
@st.cache_resource
def get_feedback_collector():
    return create_feedback_collector(
        application_name='Streamlit-Feedback-Demo',
        trace_id=st.session_state.trace_id
    )

# 메인 UI
st.title("🤖 AWS Bedrock 채팅 + 피드백 데모")

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력
user_input = st.chat_input("무엇이든 물어보세요!")

if user_input:
    # 사용자 메시지 표시 및 저장
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # 완성 ID 생성
    completion_id = str(uuid.uuid4())
    st.session_state.current_completion_id = completion_id
    
    # 피드백 수집기 설정
    feedback_collector = get_feedback_collector()
    feedback_collector.update_completion_id(completion_id)
    
    # 모델 응답 생성
    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                # Bedrock 호출
                bedrock = get_bedrock_client()
                response = bedrock.invoke_model(
                    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 500,
                        "messages": [
                            {"role": "system", "content": "당신은 도움이 되는 AI 어시스턴트입니다."},
                            *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
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
                
                # 응답 표시 및 저장
                st.markdown(assistant_response)
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
                # 피드백 UI 표시
                st.subheader("응답 평가")
                feedback_collector.render_feedback_ui(key=f"feedback_{completion_id}")
                
            except Exception as e:
                st.error(f"오류가 발생했습니다: {str(e)}")
```

## 초기화 옵션

```python
monitor_options = {
    # 필수 옵션
    'application_name': 'MyApp',  # New Relic에서 사용할 애플리케이션 이름
    
    # 선택적 옵션
    'new_relic_api_key': 'YOUR_NEW_RELIC_API_KEY',  # 환경 변수로도 설정 가능
    'host': 'custom.endpoint.com',  # 이벤트 엔드포인트 오버라이드
    'port': 443,  # 트레이스 엔드포인트 포트 오버라이드
    'track_token_usage': True,  # 토큰 사용량 추적 (기본값: True)
    'disable_streaming_events': False,  # 스트리밍 이벤트 비활성화 (기본값: False)
    'collect_feedback': False,  # 피드백 수집 활성화 (기본값: False)
    'feedback_callback': my_feedback_function  # 피드백 콜백 함수
}
```

## 환경 변수

다음 환경 변수를 사용하여 API 키를 설정할 수 있습니다:

- `NEW_RELIC_LICENSE_KEY` - 요청 인증에 사용되는 API 키
- `NEW_RELIC_INSERT_KEY` - API 키와 동일
- `EVENT_CLIENT_HOST` - 이벤트 엔드포인트 호스트 오버라이드

## 지원되는 모델

다음을 포함한 모든 AWS Bedrock 모델을 지원합니다:

### Amazon Titan 모델
- Titan Text (Lite, Express, Premier)
- Titan Text V2 (Lite, Express, Premier)
- Titan Embeddings
- Titan Multimodal

### Anthropic Claude 모델
- Claude 1 및 2
- Claude Instant
- Claude 3 (Haiku, Sonnet, Opus)
- Claude 3.5 Sonnet

### AI21 Labs, Cohere, Meta, Mistral 모델
- Jurassic-2, Jamba
- Command, Command Light, Command R/R Plus, Embed
- Llama 2 (13B, 70B), Llama 3 (8B, 70B)
- Mistral, Mixtral, Mistral Small/Medium/Large

## New Relic 데이터 분석

New Relic UI에서 다음 NRQL 쿼리를 사용하여 데이터를 분석할 수 있습니다:

### 기본 분석 쿼리

```sql
-- 모든 LLM 완성 이벤트 조회
FROM LlmChatCompletionSummary LIMIT 100

-- 응답 시간 분포 확인
FROM LlmChatCompletionSummary SELECT average(response_time), percentile(response_time, 95, 99) TIMESERIES

-- 모델별 사용량 분석
FROM LlmChatCompletionSummary FACET request_model LIMIT 10

-- 오류 분석
FROM LlmChatCompletionSummary WHERE error_message IS NOT NULL FACET error_type LIMIT 10
```

### RAG 워크플로우 분석 쿼리

```sql
-- 전체 RAG 워크플로우 보기
FROM Span WHERE rag.workflow = 'true' FACET name LIMIT 100

-- 시스템 프롬프트 조회
FROM LlmSystemPrompt LIMIT 100

-- 사용자 프롬프트 조회
FROM LlmUserPrompt LIMIT 100

-- OpenSearch 결과 조회
FROM LlmOpenSearchResult LIMIT 100

-- RAG 컨텍스트 조회
FROM LlmRagContext LIMIT 100

-- 채팅 메시지 역할별 조회
FROM LlmChatCompletionMessage FACET role LIMIT 100
```

### 피드백 분석 쿼리

```sql
-- 모든 피드백 조회
FROM LlmFeedback LIMIT 100

-- 긍정/부정 피드백 비율 확인
FROM LlmFeedback FACET feedback LIMIT 10

-- 평균 감정 점수 확인
FROM LlmFeedback SELECT average(sentiment) TIMESERIES

-- 특정 트레이스의 피드백 확인
FROM LlmFeedback WHERE trace_id = 'your-trace-id' LIMIT 10
```

## 개발 및 기여

### 테스트 실행

```bash
pip install -e ".[dev]"
pytest
```

### 로컬에서 빌드하기

```bash
pip install build
python -m build
```

모든 API 호출과 피드백 데이터가 자동으로 New Relic에 전송되어 LLM 응용 프로그램의 성능과 사용자 만족도를 포괄적으로 모니터링할 수 있습니다.

