# New Relic AWS Bedrock Observability for Python

## ASK for : czy1023@gmail.com

AWS Bedrock API 호출을 위한 New Relic 관찰성 라이브러리입니다. 이 라이브러리를 사용하면 AWS Bedrock API 호출을 모니터링하고 성능 지표를 New Relic에 전송할 수 있습니다.

## 최신 업데이트 (v1.0.3)

- Claude 3.5 Sonnet v2 최신 버전(anthropic.claude-3-5-sonnet-20241022-v2:0) 모델 지원 강화
- 내부 모델 맵핑 테이블의 일관성 개선 
- 모든 모듈에서 신규 모델 ID 인식 가능하도록 업데이트

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

## 고급 활용 예제

### 다중 요청 이벤트 구분 및 추적

여러 종류의 요청을 구분하여 추적하려면 각 이벤트에 고유 식별자와 메타데이터를 추가하세요:

```python
import uuid
import boto3
import json
import time
from nr_bedrock_observability import monitor_bedrock
import newrelic.agent

# New Relic 애플리케이션 객체 얻기
nr_application = newrelic.agent.application()

# Bedrock 클라이언트 생성
bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')

# 모니터링 설정
monitored_client = monitor_bedrock(bedrock_client, {
    'application_name': 'BedfordAdvancedDemo',
    'new_relic_api_key': 'YOUR_LICENSE_KEY',
    'application': nr_application
})

# 첫 번째 요청 (한국 역사 질문)
def make_history_request():
    # 고유 이벤트 ID 생성
    event_id = str(uuid.uuid4())
    
    # 요청 전 이벤트 기록
    newrelic.agent.record_custom_event(
        'PreRequestEvent', 
        {
            'event_id': event_id,
            'request_type': 'korea_history',
            'timestamp': time.time()
        },
        application=nr_application
    )
    
    # Claude 3.5 Sonnet 모델 요청
    response = monitored_client.invoke_model(
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
    raw_response = response.get("body").read()
    response_body = json.loads(raw_response.decode("utf-8"))
    response_content = ""
    
    if "content" in response_body and len(response_body["content"]) > 0:
        for content_item in response_body["content"]:
            if content_item.get("type") == "text":
                response_content += content_item.get("text", "")
    
    # 응답 후 추가 이벤트 기록
    newrelic.agent.record_custom_event(
        'KoreaHistoryCompletion', 
        {
            'event_id': event_id,
            'input_text': "한국의 역사에 대해 간략하게 설명해줘.",
            'output_text': response_content[:500],
            'model': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'prompt_type': 'korea_history',
            'request_id': response.get('ResponseMetadata', {}).get('RequestId', ''),
            'timestamp': time.time()
        },
        application=nr_application
    )
    
    return response_content

# 두 번째 요청 (인사말)
def make_greeting_request():
    # 고유 이벤트 ID 생성
    event_id = str(uuid.uuid4())
    
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
                            "text": "안녕?잘부탁해!."
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
            chunk_text = ""
            if 'content' in chunk and isinstance(chunk['content'], list):
                for content_item in chunk['content']:
                    if content_item.get('type') == 'text':
                        chunk_text = content_item.get('text', '')
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
            elif 'completion' in chunk:
                chunk_text = chunk['completion']
                full_response += chunk_text
                print(chunk_text, end='', flush=True)
            elif 'delta' in chunk and 'text' in chunk['delta']:
                chunk_text = chunk['delta']['text']
                full_response += chunk_text
                print(chunk_text, end='', flush=True)
            
            # 각 청크마다 이벤트 기록 (선택 사항)
            if chunk_text and nr_application:
                newrelic.agent.record_custom_event(
                    'StreamChunk', 
                    {
                        'parent_id': event_id,
                        'chunk_text': chunk_text[:100],
                        'timestamp': time.time()
                    },
                    application=nr_application
                )
        except json.JSONDecodeError:
            pass
    
    # 스트리밍 완료 후 이벤트 기록
    newrelic.agent.record_custom_event(
        'GreetingCompletion', 
        {
            'event_id': event_id,
            'input_text': "안녕?잘부탁해!.",
            'output_text': full_response[:500],
            'model': 'anthropic.claude-3-5-sonnet-20240620-v1:0',
            'prompt_type': 'greeting',
            'timestamp': time.time()
        },
        application=nr_application
    )
    
    return full_response

# 실행 함수
def run_demo():
    # 트랜잭션 시작
    with newrelic.agent.BackgroundTask(nr_application, name="BedrokAdvancedDemo"):
        print("1. 한국 역사 질문 시작...")
        history_response = make_history_request()
        print(f"\n응답 길이: {len(history_response)} 자")
        
        # 첫 번째와 두 번째 요청 사이에 간격 추가
        print("\n10초 대기 중...")
        time.sleep(10)
        
        print("\n2. 인사말 요청 시작...")
        greeting_response = make_greeting_request()
        print(f"\n응답 길이: {len(greeting_response)} 자")
        
        print("\n데모 완료! New Relic 대시보드에서 다음 이벤트 확인:")
        print("- LlmCompletion: Bedrock API 호출 기본 이벤트")
        print("- KoreaHistoryCompletion: 한국 역사 요청 커스텀 이벤트")
        print("- GreetingCompletion: 인사말 요청 커스텀 이벤트")
        print("- StreamChunk: 스트리밍 응답의 각 청크 이벤트")

if __name__ == "__main__":
    run_demo()
```

### 강화된 오류 처리 및 응답 파싱

다양한 응답 형식과 오류를 처리하는 개선된 코드:

```python
def process_bedrock_response(response, request_info=None):
    """
    AWS Bedrock 응답을 안전하게 처리하는 함수
    
    Args:
        response: Bedrock API 응답 객체
        request_info: 요청 관련 메타데이터 (선택 사항)
        
    Returns:
        dict: 처리된 응답 데이터
    """
    result = {
        'success': False,
        'content': '',
        'raw_content': None,
        'error': None
    }
    
    if request_info:
        result.update(request_info)
    
    try:
        # 응답 본문 가져오기
        if "body" in response:
            # 응답 바디가 스트림일 경우 읽기
            raw_bytes = response.get("body").read()
            
            try:
                # 바이트를 문자열로 디코딩 시도
                raw_text = raw_bytes.decode("utf-8")
                result['raw_content'] = raw_text
                
                # JSON 파싱 시도
                response_body = json.loads(raw_text)
                
                # 응답 내용 추출 (여러 형식 지원)
                # Claude 스타일 응답 (content 배열)
                if "content" in response_body and isinstance(response_body["content"], list):
                    for content_item in response_body["content"]:
                        if content_item.get("type") == "text":
                            result['content'] += content_item.get("text", "")
                
                # 단일 텍스트 응답
                elif "completion" in response_body:
                    result['content'] = response_body["completion"]
                
                # 다른 형식 (텍스트 필드 찾기)
                elif "text" in response_body:
                    result['content'] = response_body["text"]
                
                result['success'] = True
                result['parsed_response'] = response_body
                
            except UnicodeDecodeError:
                result['error'] = "UTF-8 디코딩 실패"
                # 다른 인코딩 시도
                for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                    try:
                        raw_text = raw_bytes.decode(encoding)
                        result['raw_content'] = raw_text
                        result['error'] = f"{encoding}으로 디코딩됨"
                        break
                    except UnicodeDecodeError:
                        continue
            
            except json.JSONDecodeError as json_err:
                result['error'] = f"JSON 파싱 오류: {str(json_err)}"
                # 원본 텍스트 응답을 그대로 사용
                result['content'] = result['raw_content']
        else:
            result['error'] = "응답에 body 필드가 없음"
    
    except Exception as e:
        result['error'] = f"응답 처리 중 예외 발생: {str(e)}"
    
    # 메타데이터 추가
    if 'ResponseMetadata' in response:
        result['request_id'] = response.get('ResponseMetadata', {}).get('RequestId')
        result['status_code'] = response.get('ResponseMetadata', {}).get('HTTPStatusCode')
    
    return result
```

### 이벤트 로깅 최적화를 위한 EventLogger 클래스

여러 이벤트를 추적하고 이벤트 전송 문제를 디버깅하려면:

```python
class EventLogger:
    """
    New Relic 이벤트 로깅을 위한 유틸리티 클래스
    """
    def __init__(self, application=None):
        self.events = []
        self.application = application
        
        # 필요한 경우 New Relic 에이전트 함수 패치
        if application and hasattr(newrelic.agent, 'record_custom_event'):
            self.original_record = newrelic.agent.record_custom_event
            
            def patched_record(event_type, attributes, application=None):
                print(f"New Relic 이벤트 감지: {event_type}")
                # 로컬 이벤트 로거에 기록
                self.log_event(event_type, attributes)
                
                # 애플리케이션이 전달되지 않았다면 기본값 사용
                if application is None:
                    application = self.application
                
                # 원본 함수 호출
                try:
                    result = self.original_record(event_type, attributes, application=application)
                    print(f"이벤트 기록 성공: {event_type}")
                    return result
                except Exception as e:
                    print(f"이벤트 기록 실패: {str(e)}")
                    return None
            
            # 함수 패치
            newrelic.agent.record_custom_event = patched_record
            print("New Relic 이벤트 기록 함수가 패치되었습니다.")
    
    def log_event(self, event_type, attributes):
        """
        이벤트를 로컬에 기록하고 New Relic에도 직접 전송 시도
        """
        print(f"이벤트 기록: {event_type}")
        
        # 타임스탬프 추가
        if 'timestamp' not in attributes:
            attributes['timestamp'] = time.time()
        
        # 로컬 큐에 이벤트 추가
        self.events.append({
            'event_type': event_type,
            'attributes': attributes
        })
        
        # 직접 New Relic에 이벤트 전송 시도
        try:
            if self.application:
                # 트랜잭션 내에서 이벤트 기록
                with newrelic.agent.BackgroundTask(self.application, name=f"EventRecording/{event_type}"):
                    self.original_record(event_type, attributes, application=self.application)
        except Exception as e:
            print(f"직접 이벤트 전송 실패: {str(e)}")
    
    def get_events(self, event_type=None, limit=None):
        """
        기록된 이벤트 가져오기 (필터링 옵션 포함)
        """
        if event_type:
            filtered = [e for e in self.events if e['event_type'] == event_type]
        else:
            filtered = self.events
        
        if limit:
            return filtered[-limit:]
        return filtered
    
    def print_summary(self):
        """
        기록된 이벤트 요약 출력
        """
        event_types = {}
        for event in self.events:
            event_type = event['event_type']
            if event_type in event_types:
                event_types[event_type] += 1
            else:
                event_types[event_type] = 1
        
        print("\n=== 이벤트 요약 ===")
        print(f"총 이벤트 수: {len(self.events)}")
        for event_type, count in event_types.items():
            print(f"- {event_type}: {count}개")
```

### 안정적인 트랜잭션 관리를 위한 TransactionManager 클래스

```python
class TransactionManager:
    """
    New Relic 트랜잭션 관리를 위한 유틸리티 클래스
    """
    def __init__(self, application=None):
        self.application = application
        self.active_transactions = {}
    
    def start(self, name, custom_params=None):
        """
        트랜잭션 시작
        
        Args:
            name: 트랜잭션 이름
            custom_params: 트랜잭션 매개변수 (선택 사항)
            
        Returns:
            transaction: 트랜잭션 객체 또는 None
        """
        transaction_id = str(uuid.uuid4())
        
        try:
            if self.application:
                transaction_name = f"Python/{name}"
                
                # 트랜잭션 시작
                transaction = newrelic.agent.BackgroundTask(
                    self.application, 
                    name=transaction_name
                )
                transaction.__enter__()
                
                # 액티브 트랜잭션 관리
                self.active_transactions[transaction_id] = {
                    'transaction': transaction,
                    'name': name,
                    'start_time': time.time()
                }
                
                # 커스텀 매개변수 추가
                if custom_params and hasattr(newrelic.agent, 'add_custom_parameters'):
                    newrelic.agent.add_custom_parameters(custom_params)
                
                print(f"트랜잭션 시작됨: {name} (ID: {transaction_id})")
                return transaction_id
            else:
                print("트랜잭션을 시작할 수 없음: 애플리케이션 객체가 없음")
                return None
        except Exception as e:
            print(f"트랜잭션 시작 오류: {str(e)}")
            return None
    
    def end(self, transaction_id, success=True):
        """
        트랜잭션 종료
        
        Args:
            transaction_id: 시작 시 반환된 트랜잭션 ID
            success: 성공 여부 (기본값: True)
        """
        if transaction_id not in self.active_transactions:
            print(f"알 수 없는 트랜잭션 ID: {transaction_id}")
            return
        
        transaction_info = self.active_transactions[transaction_id]
        transaction = transaction_info['transaction']
        
        try:
            # 트랜잭션 종료
            transaction.__exit__(None, None, None)
            
            # 트랜잭션 정보 업데이트
            duration = time.time() - transaction_info['start_time']
            print(f"트랜잭션 종료됨: {transaction_info['name']} (소요 시간: {duration:.2f}초)")
            
            # 활성 트랜잭션 목록에서 제거
            del self.active_transactions[transaction_id]
            
        except Exception as e:
            print(f"트랜잭션 종료 오류: {str(e)}")
    
    def with_transaction(self, name, custom_params=None):
        """
        컨텍스트 매니저로 사용하기 위한 데코레이터
        
        사용 예:
        with transaction_manager.with_transaction("MyTransaction") as tx_id:
            # 작업 수행
        """
        class TransactionContext:
            def __init__(self, manager, tx_name, params):
                self.manager = manager
                self.name = tx_name
                self.params = params
                self.tx_id = None
            
            def __enter__(self):
                self.tx_id = self.manager.start(self.name, self.params)
                return self.tx_id
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                success = exc_type is None
                if self.tx_id:
                    self.manager.end(self.tx_id, success)
                return False  # 예외 처리를 호출자에게 위임
        
        return TransactionContext(self, name, custom_params)
```

## 대용량 트래픽 최적화

대용량 트래픽 환경에서 성능을 최적화하려면 다음 옵션을 활용하세요:

```python
monitor_bedrock(bedrock_client, {
    'application_name': 'HighVolumeApp',
    'disable_streaming_events': True,  # 스트리밍 이벤트 비활성화
})
```

## New Relic 트랜잭션 관리

이벤트가 제대로 기록되지 않는 문제가 발생하는 경우, 명시적인 트랜잭션 관리를 사용할 수 있습니다. 트랜잭션은 New Relic에서 이벤트를 올바르게 기록하기 위해 필요합니다.

```python
import newrelic.agent
import uuid
from nr_bedrock_observability import monitor_bedrock

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

# 메인 함수 예시
def main():
    # 트랜잭션 시작
    transaction = start_transaction("main")
    
    try:
        # Bedrock 클라이언트 초기화
        bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
        
        # New Relic 모니터링 설정 - 애플리케이션 객체 직접 전달
        monitor_options = {
            'application_name': 'Bedrock-Test-App',
            'new_relic_api_key': 'YOUR_LICENSE_KEY',
            'application': nr_application  # 애플리케이션 객체 직접 전달
        }
        
        monitored_client = monitor_bedrock(bedrock_client, monitor_options)
        
        # API 호출 및 데이터 처리
        # ...
    
    finally:
        # 트랜잭션 종료
        end_transaction(transaction)

if __name__ == "__main__":
    main()
```

### 스트리밍 API와 트랜잭션 관리

스트리밍 API를 사용할 때도 트랜잭션 관리가 중요합니다:

```python
def test_streaming_completion():
    # 트랜잭션 시작
    transaction = start_transaction("test_streaming_completion")
    
    try:
        # API 호출
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
        
        # 스트리밍 청크 처리
        for event in stream_response['body']:
            chunk_bytes = event['chunk']['bytes']
            chunk_str = chunk_bytes.decode('utf-8')
            try:
                chunk = json.loads(chunk_str)
                # 다양한 응답 형식 처리
                if 'delta' in chunk and 'text' in chunk['delta']:
                    chunk_text = chunk['delta']['text']
                    print(chunk_text, end='', flush=True)
                # 기타 형식 처리
            except json.JSONDecodeError:
                print(f"JSON 파싱 오류: {chunk_str}")
    
    finally:
        # 트랜잭션 종료
        end_transaction(transaction)
```

## 이벤트 로깅 최적화

이벤트 로깅이 제대로 되지 않는 경우, 다음과 같이 이벤트 클라이언트를 커스텀하게 설정할 수 있습니다:

```python
from nr_bedrock_observability.events_client import BedrockEventClient

# 커스텀 이벤트 리스너 클래스 정의
class EventLogger:
    def __init__(self, app=None):
        self.events = []
        self.app = app
    
    def log_event(self, event_type, attributes):
        print(f"New Relic 이벤트 전송: {event_type}")
        self.events.append({"event_type": event_type, "attributes": attributes})

# 이벤트 로거 초기화
event_logger = EventLogger(app=nr_application)

# New Relic 에이전트 커스텀 이벤트 기록 함수 패치
if nr_application and hasattr(newrelic.agent, 'record_custom_event'):
    original_record_custom_event = newrelic.agent.record_custom_event
    
    def custom_record_event(event_type, attributes, application=None):
        print(f"New Relic 이벤트 감지: {event_type}")
        event_logger.log_event(event_type, attributes)
        # 명시적으로 애플리케이션 객체 전달
        return original_record_custom_event(event_type, attributes, application=nr_application)
    
    newrelic.agent.record_custom_event = custom_record_event
    print("New Relic 커스텀 이벤트 로깅이 활성화되었습니다.")
```

또는 이벤트 클라이언트를 패치할 수 있습니다:

```python
# 이벤트 클라이언트 패치
if nr_application:
    # 원본 send 메서드 저장
    original_send = BedrockEventClient.send
    
    # 새로운 send 메서드
    def patched_send(self, event_data):
        if nr_application and event_data:
            event_type = event_data.get('eventType')
            attributes = event_data.get('attributes', {})
            
            if event_type:
                # 트랜잭션 내에서 직접 이벤트 기록
                with newrelic.agent.BackgroundTask(nr_application, name=f"DirectEvent/{event_type}"):
                    newrelic.agent.record_custom_event(event_type, attributes, application=nr_application)
        
        # 원본 함수도 호출
        return original_send(self, event_data)
    
    # send 메서드 패치
    BedrockEventClient.send = patched_send
```

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

