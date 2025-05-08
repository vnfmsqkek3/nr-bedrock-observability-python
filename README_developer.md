# nr-bedrock-observability-python 개발자 가이드

이 문서는 nr-bedrock-observability-python 라이브러리 개발자를 위한 가이드입니다.

## 개발 환경 설정

1. 저장소 클론:

```bash
git clone https://github.com/newrelic/nr-bedrock-observability-python.git
cd nr-bedrock-observability-python
```

2. 가상 환경 생성 및 활성화:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. 개발 의존성 설치:

```bash
pip install -e ".[dev]"
```

## 테스트

이 라이브러리는 pytest를 사용하여 테스트합니다:

```bash
pytest
```

커버리지 리포트를 생성하려면:

```bash
pytest --cov=nr_bedrock_observability
```

## 코드 스타일

이 프로젝트는 black, isort, flake8을 사용하여 코드 스타일을 관리합니다:

```bash
# 코드 포맷팅
black src tests
isort src tests

# 린팅
flake8 src tests
```

## 패키지 빌드 및 배포

### 패키지 빌드

```bash
python -m build
```

### 테스트 PyPI에 배포

```bash
python -m twine upload --repository testpypi dist/*
```

### 실제 PyPI에 배포

```bash
python -m twine upload dist/*
```

## 디버깅 및 로깅

로깅 설정을 통해 라이브러리의 디버그 메시지를 확인할 수 있습니다:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 환경 변수

테스트 및 개발을 위해 다음 환경 변수를 설정할 수 있습니다:

```bash
export NEW_RELIC_LICENSE_KEY=your_license_key
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

## RAG 워크플로우 트레이싱 개발

이 라이브러리는 분산 트레이싱을 활용하여 OpenSearch 검색과 Bedrock 호출을 포함한 RAG 워크플로우를 하나의 트레이스로 연결하는 기능을 제공합니다.

### 기술적 구현 방법

RAG 워크플로우 트레이싱은 다음과 같이 구현되어 있습니다:

1. 고유한 트레이스 ID 생성 (`uuid.uuid4()` 사용)
2. New Relic 트랜잭션 생성 (`@newrelic.agent.background_task` 데코레이터 사용)
3. 각 스팬에 동일한 트레이스 ID 공유 (`add_custom_span_attribute` 사용)
4. FunctionTrace 컨텍스트 매니저를 사용한 스팬 생성

```python
# 트레이스 ID 생성 및 트랜잭션 시작
trace_id = str(uuid.uuid4())
transaction = newrelic.agent.current_transaction()
transaction.add_custom_attribute('trace.id', trace_id)

# 첫 번째 스팬 생성
with newrelic.agent.FunctionTrace(name='span_name'):
    newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
    # ... 작업 코드 ...

# 두 번째 스팬 생성
with newrelic.agent.FunctionTrace(name='another_span'):
    newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
    # ... 작업 코드 ...
```

### 커스텀 함수 트레이스 확장

보다 편리한 사용을 위해 `CustomFunctionTrace` 클래스를 구현했습니다:

```python
from newrelic.api.time_trace import TimeTrace

class CustomFunctionTrace(TimeTrace):
    def __init__(self, name, group='Custom', trace_id=None):
        super(CustomFunctionTrace, self).__init__(name=name, group=group)
        self.trace_id = trace_id
        
    def __enter__(self):
        result = super(CustomFunctionTrace, self).__enter__()
        
        # 트레이스 ID가 제공된 경우 스팬에 추가
        if self.trace_id:
            newrelic.agent.add_custom_span_attribute('trace.id', self.trace_id)
            
        return result
```

### 샘플 코드 실행

RAG 워크플로우 트레이싱 샘플 코드를 실행하려면:

```bash
# 필요한 패키지 설치
pip install boto3 newrelic opensearch-py

# 샘플 코드 실행
python samples/rag_workflow_tracing.py
```

### 테스트 작성

RAG 워크플로우 트레이싱 기능에 대한 테스트를 작성할 때는 다음 사항을 고려하세요:

1. 모킹을 통해 AWS 서비스 호출 시뮬레이션
2. New Relic 트랜잭션과 스팬이 올바르게 생성되는지 확인
3. 트레이스 ID가 모든 스팬에 올바르게 전달되는지 검증

```python
def test_rag_workflow_tracing(mock_transaction, mock_bedrock_client, mock_opensearch_client):
    # 테스트 코드...
    assert 'trace.id' in captured_attributes
    assert 'workflow.type' in captured_attributes
    # ... 더 많은 검증 ...
```

### 디버깅 팁

트레이싱 문제를 디버깅할 때 도움이 되는 팁:

1. `logging.basicConfig(level=logging.DEBUG)`로 로그 레벨 설정
2. New Relic UI에서 "Distributed Tracing" 메뉴를 확인하여 트레이스 연결 상태 확인
3. `trace.id` 속성으로 검색하여 모든 관련 스팬이 올바르게 연결되었는지 확인

## PR 제출

1. 기능 브랜치를 생성합니다.
2. 변경사항을 구현합니다.
3. 테스트를 추가하고 기존 테스트를 통과하는지 확인합니다.
4. Pull Request를 제출합니다.

## 문제 해결

### "ModuleNotFoundError: No module named 'nr_bedrock_observability'"

- 패키지가 올바르게 설치되었는지 확인하세요.
- 가상 환경이 활성화되어 있는지 확인하세요.

### ImportError 관련 문제

boto3 또는 newrelic 패키지가 없는 경우:

```bash
pip install boto3 newrelic
```

### Boto3 인증 문제

AWS 자격 증명이 올바르게 설정되어 있는지 확인하세요:

```python
import boto3
boto3.setup_default_session(
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='us-east-1'
)
``` 