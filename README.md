# New Relic AWS Bedrock Observability for Python

[![PyPI](https://img.shields.io/badge/PyPI-nr--bedrock--observability-blue)](https://pypi.org/project/nr-bedrock-observability/)
[![Tests](https://github.com/newrelic/nr-bedrock-observability-python/actions/workflows/tests.yml/badge.svg)](https://github.com/newrelic/nr-bedrock-observability-python/actions/workflows/tests.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

AWS Bedrock API 호출을 위한 New Relic 관찰성 라이브러리입니다. 이 라이브러리를 사용하면 AWS Bedrock API 호출을 모니터링하고 성능 지표를 New Relic에 전송할 수 있습니다.

## 최신 업데이트 (v0.3.0)

- 팩토리 패턴을 사용한 이벤트 생성 로직 개선
- 테스트 안정성 향상 및 CI/CD 파이프라인 개선
- 재귀 호출 문제 해결
- `CommonSummaryAttributes` 클래스 추가로 이벤트 데이터 표준화
- AWS 리전 지정 필요성 명시
- API 키가 없는 환경에서도 테스트용 키로 실행 가능
- README 문서 개선 및 예제 코드 업데이트

## 설치

PyPI에서 패키지를 설치합니다:

```bash
pip install nr-bedrock-observability
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
    'disable_streaming_events': False
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
bedrock = boto3.client('bedrock-runtime')

# 모니터링 설정
monitor_bedrock(bedrock, {'application_name': 'MyClaudeApp'})

# Claude 3.5 Sonnet 모델 호출
response = bedrock.invoke_model(
    modelId='anthropic.claude-3-5-sonnet-20240620-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "messages": [
            {
                "role": "user",
                "content": "인공지능의 최신 발전 동향을 설명해주세요."
            }
        ]
    })
)

# 응답 처리
response_body = json.loads(response['body'].read().decode('utf-8'))
for content_item in response_body['content']:
    if content_item['type'] == 'text':
        print(content_item['text'])
```

### 스트리밍 API 사용

```python
import boto3
import json
from nr_bedrock_observability import monitor_bedrock

# Bedrock 클라이언트 생성
bedrock = boto3.client('bedrock-runtime')

# 모니터링 설정
monitor_bedrock(bedrock, {'application_name': 'MyStreamingApp'})

# 스트리밍 응답으로 Titan 모델 호출
stream_response = bedrock.invoke_model_with_response_stream(
    modelId='amazon.titan-text-express-v1',
    body=json.dumps({
        'inputText': 'Write a short poem about clouds.',
        'textGenerationConfig': {
            'maxTokenCount': 512,
            'temperature': 0.7
        }
    })
)

# 스트리밍 응답 처리
for event in stream_response['body']:
    chunk = json.loads(event['chunk']['bytes'].decode())
    if 'outputText' in chunk:
        print(chunk['outputText'], end='', flush=True)
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

## 대용량 트래픽 최적화

대용량 트래픽 환경에서 성능을 최적화하려면 다음 옵션을 활용하세요:

```python
monitor_bedrock(bedrock_client, {
    'application_name': 'HighVolumeApp',
    'disable_streaming_events': True,  # 스트리밍 이벤트 비활성화
})
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

## 지원

New Relic은 다른 고객과 함께 New Relic 직원과 상호 작용할 수 있는 온라인 포럼을 호스팅하고 관리하며, 도움을 받고 모범 사례를 공유할 수 있습니다.

- [New Relic Community](https://forum.newrelic.com/) - 문제 해결 질문에 참여하는 가장 좋은 곳
- [New Relic Developer](https://developer.newrelic.com/) - 사용자 지정 관찰성 애플리케이션 구축을 위한 리소스
- [New Relic University](https://learn.newrelic.com/) - 모든 수준의 New Relic 사용자를 위한 다양한 온라인 교육

## 라이선스

Apache License 2.0 