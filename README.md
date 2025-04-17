# New Relic AWS Bedrock Observability for Python

[![Test PyPI](https://img.shields.io/badge/Test%20PyPI-nr--bedrock--observability-blue)](https://test.pypi.org/project/nr-bedrock-observability/)
[![Tests](https://github.com/yourusername/nr-bedrock-observability-python/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/nr-bedrock-observability-python/actions/workflows/tests.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

AWS Bedrock API 호출을 위한 New Relic 관찰성 라이브러리

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

# Bedrock 클라이언트 생성
bedrock_client = boto3.client('bedrock-runtime')

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

print(response)
```

### 초기화 옵션

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
    'port': 443
}
```

### 환경 변수

초기화 옵션에 다음과 같은 환경 변수를 사용할 수 있습니다:

- `NEW_RELIC_LICENSE_KEY` - 요청을 인증하는 데 사용되는 API 키
- `NEW_RELIC_INSERT_KEY` - API 키와 동일
- `EVENT_CLIENT_HOST` - 이벤트 엔드포인트의 호스트 오버라이드

## 개발

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

## 지원

New Relic은 다른 고객과 함께 New Relic 직원과 상호 작용할 수 있는 온라인 포럼을 호스팅하고 관리하며, 도움을 받고 모범 사례를 공유할 수 있습니다. 모든 공식 New Relic 오픈 소스 프로젝트와 마찬가지로 New Relic Explorers Hub에 관련 커뮤니티 주제가 있습니다.

- [New Relic Community](https://forum.newrelic.com/) - 문제 해결 질문에 참여하는 가장 좋은 곳
- [New Relic Developer](https://developer.newrelic.com/) - 사용자 지정 관찰성 애플리케이션 구축을 위한 리소스
- [New Relic University](https://learn.newrelic.com/) - 모든 수준의 New Relic 사용자를 위한 다양한 온라인 교육

## 라이선스

Apache License 2.0 