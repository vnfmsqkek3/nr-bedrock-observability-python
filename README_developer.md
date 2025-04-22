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