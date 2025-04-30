# New Relic AWS Bedrock Observability for Python

## ASK for : czy1023@gmail.com

AWS Bedrock API 호출을 위한 New Relic 관찰성 라이브러리입니다. 이 라이브러리를 사용하면 AWS Bedrock API 호출을 모니터링하고 성능 지표를 New Relic에 전송할 수 있습니다.

## 최신 업데이트 (v1.1.0)

- 사용자 피드백 수집 기능 추가
  - 피드백 (positive, negative, neutral)
  - 감정 점수 (-1.0 ~ 1.0)
  - 피드백 메시지
- 피드백 콜백 함수를 통한 사용자 정의 피드백 수집 지원
- New Relic 이벤트에 피드백 데이터 자동 포함

## 이전 업데이트 (v1.0.3)

- Claude 3.5 Sonnet v2 최신 버전(anthropic.claude-3-5-sonnet-20241022-v2:0) 모델 지원 강화
- 내부 모델 맵핑 테이블의 일관성 개선 
- 모든 모듈에서 신규 모델 ID 인식 가능하도록 업데이트
- RAG 워크플로우 트레이싱 샘플 코드 추가: 사용자 질문 → OpenSearch 검색 → Bedrock LLM 응답을 하나의 트레이스로 연결

## 이전 업데이트 (v1.0.2)

- Claude 3.5 Sonnet 최신 버전(anthropic.claude-3-5-sonnet-20241022-v2:0) 지원 추가
- 모델 ID 추적 및 인식 기능 개선
- 내부 모델 매핑 테이블 업데이트

## 이전 업데이트 (v1.0.1)

- 안정성 강화 및 내부 오류 처리 개선
- Streaming 응답을 처리한 후에도 응답 본문을 보존 가능하도록 구조 변경
- `StreamingBody` 처리 시 `BytesIO` 활용하여 이중 소비 방지
- New Relic 커스텀 이벤트 전송 성능 개선
- `generate_with_model()` 등 신규 Bedrock API 지원 강화

## 이전 업데이트 (v0.3.3)

- 응답 데이터를 소비하지 않는 기능 추가: StreamingBody 객체를 복제하여 원본 보존
- io.BytesIO를 사용한 응답 스트림 복사 구현
- 모니터링 데이터 추출 시 원본 응답 객체를 보존하는 방식으로 개선
- seek/tell 메서드를 활용한 스트림 위치 복원 기능 추가

## 이전 업데이트 (v0.3.0)

- 팩토리 패턴을 사용한 이벤트 생성 로직 개선
- 테스트 안정성 향상 및 CI/CD 파이프라인 개선
- 재귀 호출 문제 해결
- `CommonSummaryAttributes` 클래스 추가로 이벤트 데이터 표준화
- AWS 리전 지정 필요성 명시
- API 키가 없는 환경에서도 테스트용 키로 실행 가능
- New Relic 트랜잭션 관리 기능 추가로 이벤트 로깅 안정성 향상
- README 문서 개선 및 예제 코드 업데이트

## 설치

Test PyPI에서 패키지를 설치합니다:

```bash
pip install -i https://test.pypi.org/simple/ nr-bedrock-observability
```

## 시작하기

`monitor_bedrock` 함수를 `boto3.client('bedrock-runtime')` 인스턴스와 함께 호출하기만 하면 됩니다. 그러면 New Relic에 데이터를 전송하기 위해 뒤에서 자동으로 패치됩니다.

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock

# Bedrock 클라이언트 생성 (리전 필수 지정)
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

# 모니터링 설정
monitor_bedrock(bedrock_client, {
    'application_name': 'MyApp',
    'new_relic_api_key': 'NEW_RELIC_LICENSE_KEY',
})

# 평소처럼 Bedrock API 사용
response = bedrock_client.invoke_model(
    modelId='amazon.titan-text-express-v1',
    body=json.dumps({
        'inputText': 'What is observability?',
        'textGenerationConfig': {
            'maxTokenCount': 512,
            'temperature': 0.5
        }
    })
)

# 응답 처리
response_body = json.loads(response['body'].read().decode('utf-8'))
print(response_body['results'][0]['outputText'])
```

## 지원되는 API

이 라이브러리는 다음과 같은 AWS Bedrock API를 지원합니다:

- `invoke_model`: 텍스트 생성 요청
- `invoke_model_with_response_stream`: 스트리밍 응답을 통한 텍스트 생성
- `converse`: Claude 3와 같은 모델을 위한 대화형 API
- `create_embedding`: 임베딩 생성 (일부 모델에서 사용 가능)
- `generate_with_model`: RAG(Retrieval Augmented Generation) API

## 지원되는 모델

이 라이브러리는 다음을 포함한 모든 AWS Bedrock 모델을 지원합니다:

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

### AI21 Labs 모델
- Jurassic-2 (Mid, Ultra)
- Jamba

### Cohere 모델
- Command
- Command Light
- Command R
- Command R Plus
- Embed (English, Multilingual)

### Meta 모델
- Llama 2 (13B, 70B)
- Llama 3 (8B, 70B)

### Mistral AI 모델
- Mistral 7B
- Mixtral 8x7B
- Mistral Small/Medium/Large

## 초기화 옵션

```python
monitor_options = {
    # New Relic에서 사용할 애플리케이션 이름 (필수)
    'application_name': 'MyApp',
    
    # 요청을 인증하는 데 사용되는 API 키 (선택적)
    # 환경 변수로 설정할 수도 있습니다
    'new_relic_api_key': 'YOUR_NEW_RELIC_API_KEY',
    
    # 이벤트 엔드포인트의 호스트 오버라이드 (선택적)
    'host': 'custom.endpoint.com',
    
    # 트레이스 엔드포인트의 포트 오버라이드 (선택적)
    'port': 443,
    
    # 토큰 사용량 추적 활성화/비활성화 (기본값: True)
    'track_token_usage': True,
    
    # 스트리밍 이벤트 비활성화 (대용량 트래픽 시 유용, 기본값: False)
    'disable_streaming_events': False,
    
    # New Relic 애플리케이션 객체 (트랜잭션 관리에 필요)
    'application': nr_application
}
```

## 환경 변수

초기화 옵션에 다음과 같은 환경 변수를 사용할 수 있습니다:

- `NEW_RELIC_LICENSE_KEY` - 요청을 인증하는 데 사용되는 API 키
- `NEW_RELIC_INSERT_KEY` - API 키와 동일
- `EVENT_CLIENT_HOST` - 이벤트 엔드포인트의 호스트 오버라이드

## 예제

### Claude 3.5 모델 사용

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock

# Bedrock 클라이언트 생성
bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')

# 모니터링 설정
monitor_bedrock(bedrock, {'application_name': 'MyClaudeApp'})

# Claude 3.5 Sonnet 모델 호출
response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "한국의 역사에 대해 간략하게 설명해줘."
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

### 스트리밍 API 사용

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock
import newrelic.agent

# New Relic 애플리케이션 객체 얻기
nr_application = newrelic.agent.application()

# 트랜잭션 시작 함수
def start_transaction(name):
    transaction = None
    if nr_application:
        print(f"New Relic 트랜잭션 시작: {name}")
        transaction = newrelic.agent.BackgroundTask(nr_application, name=f"Python/{name}")
        transaction.__enter__()
    return transaction

# 트랜잭션 종료 함수
def end_transaction(transaction):
    if transaction:
        print("New Relic 트랜잭션 종료")
        transaction.__exit__(None, None, None)

# 스트리밍 테스트 함수
def test_streaming_completion():
    # 트랜잭션 시작
    transaction = start_transaction("test_streaming_completion")
    
    try:
        # Bedrock 클라이언트 생성
        bedrock = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        
        # 모니터링 설정 - 애플리케이션 객체 직접 전달
        monitor_options = {
            'application_name': 'MyStreamingApp',
            'application': nr_application
        }
        
        monitored_client = monitor_bedrock(bedrock, monitor_options)
        
        # 스트리밍 응답으로 Claude 3.5 Sonnet 모델 호출
        stream_response = monitored_client.invoke_model_with_response_stream(
            modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "구름에 대한 짧은 시를 써줘."
                            }
                        ]
                    }
                ],
                "temperature": 0.7
            })
        )

        # 스트리밍 응답 처리
        full_response = ""
        for event in stream_response['body']:
            chunk_bytes = event['chunk']['bytes']
            chunk_str = chunk_bytes.decode('utf-8')
            
            try:
                chunk = json.loads(chunk_str)
                
                # 다양한 응답 형식 처리
                if 'content' in chunk and len(chunk['content']) > 0:
                    for content_item in chunk['content']:
                        if content_item.get('type') == 'text':
                            chunk_text = content_item.get('text', '')
                            full_response += chunk_text
                            print(chunk_text, end='', flush=True)
                elif 'completion' in chunk:
                    chunk_text = chunk['completion']
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)
                elif 'outputText' in chunk:
                    chunk_text = chunk['outputText']
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)
                elif 'delta' in chunk and 'text' in chunk['delta']:
                    chunk_text = chunk['delta']['text']
                    full_response += chunk_text
                    print(chunk_text, end='', flush=True)
            except json.JSONDecodeError:
                print(f"JSON 파싱 오류: {chunk_str}")
                
    finally:
        # 트랜잭션 종료
        end_transaction(transaction)

# 함수 호출
test_streaming_completion()
```

### RAG API 사용

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock

# Bedrock 클라이언트 생성
bedrock = boto3.client('bedrock-runtime')

# 모니터링 설정
monitor_bedrock(bedrock, {'application_name': 'MyRagApp'})

# Knowledge Base 데이터소스 ID 설정
knowledge_base_id = "your-knowledge-base-id"

# RAG API 호출
response = bedrock.generate_with_model(
    modelId='anthropic.claude-3-sonnet-20240229-v1:0',
    textQuery="우리 회사의 환불 정책은 어떻게 되나요?",
    retrieveAndGenerateConfiguration={
        'knowledgeBaseConfiguration': {
            'retrievalConfiguration': {
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            },
            'knowledgeBaseId': knowledge_base_id
        },
        'generationConfiguration': {
            'promptTemplate': "You are a helpful customer service assistant. Use only the information in the provided context to answer the question at the end. If you don't know the answer, just say you don't know.\n\nContext:\n{{context}}\n\nQuestion: {{question}}\n\nAnswer:",
            'maxTokens': 2048
        }
    }
)

# 생성된 텍스트 출력
print(response.generation)

# 인용 정보 출력
if hasattr(response, 'citations') and response.citations:
    print("\n참고 문서:")
    for citation in response.citations:
        print(f"- {citation.retrievedReferences[0].content[:100]}...")
```

## 이벤트 데이터 구조

이 라이브러리는 이벤트 데이터를 구조화하기 위해 다음과 같은 클래스를 제공합니다:

- `EventType`: 이벤트 유형 정의 (LlmCompletion, LlmChatCompletionSummary 등)
- `CommonSummaryAttributes`: 모든 요약 이벤트에 공통으로 포함되는 속성
- `ChatCompletionSummaryAttributes`: 채팅 완성 요약 속성
- `ChatCompletionMessageAttributes`: 채팅 메시지 속성
- `EmbeddingAttributes`: 임베딩 속성
- `CompletionAttributes`: 완성 속성
- `BedrockError`: AWS Bedrock API 오류 정보

## New Relic 데이터

이 라이브러리를 사용하면 다음과 같은 이벤트가 New Relic에 보고됩니다:

- `LlmCompletion`: AWS Bedrock 모델 호출에 대한 세부 정보
- `LlmChatCompletionSummary`: 대화형 채팅 완성 요약
- `LlmChatCompletionMessage`: 개별 채팅 메시지
- `LlmEmbedding`: 임베딩 요청 데이터

각 이벤트에는 다음과 같은 유용한 메트릭이 포함됩니다:

- 응답 시간
- 토큰 사용량 (입력, 출력, 총 토큰 수)
- 모델 ID 및 정규화된 모델 이름
- 프롬프트 및 응답 내용
- 완료 이유 (stop_reason)
- 오류 정보 (발생한 경우)
- 속도 제한 (Rate Limit) 발생 여부
- AWS 리전 정보

## 통합 RAG 워크플로우 트레이싱

이 라이브러리는 분산 트레이싱을 활용하여 복잡한 Retrieval-Augmented Generation(RAG) 워크플로우를 하나의 트레이스로 연결할 수 있습니다. 이를 통해 사용자의 질문부터 검색, 그리고 최종 응답까지의 전체 흐름을 모니터링할 수 있습니다.

### RAG 워크플로우 트레이싱 예제

다음 예제는 OpenSearch 검색과 AWS Bedrock LLM 응답 생성을 하나의 트레이스로 연결합니다:

```python
import newrelic.agent
import uuid
import boto3
from nr_bedrock_observability import monitor_bedrock

# 트랜잭션에 대한 백그라운드 태스크 정의
@newrelic.agent.background_task(name='rag_workflow')
def rag_workflow(user_query):
    # 고유 트레이스 ID 생성
    trace_id = str(uuid.uuid4())
    
    # 트랜잭션에 메타데이터 추가
    transaction = newrelic.agent.current_transaction()
    if transaction:
        transaction.add_custom_attribute('trace.id', trace_id)
        transaction.add_custom_attribute('workflow.type', 'rag')
        
    # OpenSearch 검색 실행
    with newrelic.agent.FunctionTrace(name='search_opensearch'):
        # 트레이스 ID 공유를 위한 스팬 속성 추가
        newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
        
        # OpenSearch 검색 로직...
        opensearch_client = boto3.client('opensearch')
        # 검색 실행 코드...
        search_results = [...]  # 검색 결과
    
    # Bedrock 호출로 LLM 응답 생성
    with newrelic.agent.FunctionTrace(name='generate_bedrock_response'):
        # 트레이스 ID 공유를 위한 스팬 속성 추가
        newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
        
        # Bedrock 클라이언트 설정
        bedrock_client = boto3.client('bedrock-runtime')
        monitored_client = monitor_bedrock(bedrock_client, {
            'application_name': 'MyRagApp'
        })
        
        # LLM 응답 생성
        # ...Bedrock 모델 호출 코드...
    
    return {
        'query': user_query,
        'results': search_results,
        'response': llm_response,
        'trace_id': trace_id
    }
```

### 전체 샘플 코드

더 자세한 구현은 `samples/rag_workflow_tracing.py`를 참조하세요. 이 샘플 코드는 다음 기능을 포함합니다:

1. 고유한 트레이스 ID 생성 및 모든 단계에서 공유
2. OpenSearch 검색과 Bedrock 호출을 하나의 트랜잭션으로 연결
3. 각 단계에서 유용한 메타데이터 수집
4. New Relic UI에서 전체 워크플로우 시각화 및 분석

### 트레이싱 데이터 보기

New Relic UI에서 다음과 같이 통합 RAG 워크플로우 트레이스를 확인할 수 있습니다:

1. New Relic One에서 "Distributed Tracing" 메뉴로 이동
2. 검색창에 `workflow.type:rag` 또는 `trace.id:[특정 ID]`로 검색
3. 해당 트레이스를 클릭하여 사용자 질문, 검색 쿼리, LLM 응답 과정을 포함한 전체 워크플로우 확인

## 개발

### 테스트 실행

```bash
pip install -e ".[dev]"
pytest
```

### 주의사항

- 테스트 실행 시 `boto3.client('bedrock-runtime')` 호출에 `region_name`을 반드시 지정해야 합니다.
- New Relic API 키가 없어도 테스트는 자동으로 테스트용 키를 사용합니다.
- 단위 테스트는 실제 AWS 리소스에 접근하지 않고 모킹(mocking)을 통해 실행됩니다.

### 로컬에서 빌드하기

```bash
pip install build
python -m build
```

