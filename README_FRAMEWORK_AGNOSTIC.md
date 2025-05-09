# 프레임워크 독립적인 모델 평가 기능

이 문서는 nr-bedrock-observability-python 라이브러리에서 Streamlit에 의존하지 않는 모델 평가 기능을 설명합니다.

## 개요

nr-bedrock-observability-python 라이브러리는 이제 Streamlit에 대한 의존성 없이도 모델 평가를 수집하고 New Relic에 전송할 수 있습니다. 어떤 프레임워크(FastAPI, Flask, Django 등) 또는 콘솔 애플리케이션에서도 평가 기능을 사용할 수 있습니다.

이 기능은 다음과 같은 이점을 제공합니다:

- **프레임워크 독립적**: 어떤 Python 환경에서도 모델 평가 가능
- **API 기반**: 다양한 클라이언트에서 평가 데이터 수집 가능
- **유연한 통합**: 기존 애플리케이션에 쉽게 통합
- **일관된 데이터**: 모든 프레임워크에서 동일한 형식의 평가 데이터 생성

## 설치

```bash
pip install -i https://test.pypi.org/simple/ nr-bedrock-observability
```

## 기본 사용법

```python
from nr_bedrock_observability import (
    create_response_evaluation_collector,
    EventType
)

# 평가 수집기 생성
collector = create_response_evaluation_collector(
    application_name="내 애플리케이션",
    trace_id="고유-트레이스-ID",  # 선택 사항
    completion_id="고유-완성-ID"  # 선택 사항
)

# 기본 평가 기록
result = collector.record_evaluation(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    overall_score=8  # 1-10 척도
)

# 세부 평가 기록
detailed_result = collector.record_evaluation(
    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    overall_score=8,
    relevance_score=9,
    accuracy_score=7,
    completeness_score=8,
    coherence_score=9,
    helpfulness_score=8,
    feedback_comment="이 응답은 매우 도움이 되었습니다!",
    query_type="코딩/기술",
    domain="기술",
    total_tokens=2500,
    response_time_ms=3500
)
```

## 평가 항목

| 항목 | 설명 | 필수 여부 |
|------|------|----------|
| `model_id` | 평가 대상 모델 ID | 필수 |
| `overall_score` | 전체 만족도 점수 (1-10) | 필수 |
| `relevance_score` | 질문 관련성 점수 (1-10) | 선택 |
| `accuracy_score` | 정확성 점수 (1-10) | 선택 |
| `completeness_score` | 완성도 점수 (1-10) | 선택 |
| `coherence_score` | 일관성 점수 (1-10) | 선택 |
| `helpfulness_score` | 유용성 점수 (1-10) | 선택 |
| `response_time_score` | 응답 속도 점수 (1-10) | 선택 |
| `creativity_score` | 창의성 점수 (1-10) | 선택 |
| `feedback_comment` | 자유 형식 피드백 코멘트 | 선택 |
| `query_type` | 질문 유형 (일반 지식, 창의적 생성 등) | 선택 |
| `domain` | 도메인 분야 (기술, 과학 등) | 선택 |
| `total_tokens` | 총 토큰 수 | 선택 |
| `prompt_tokens` | 프롬프트 토큰 수 | 선택 |
| `completion_tokens` | 완성 토큰 수 | 선택 |
| `response_time_ms` | 응답 시간 (밀리초) | 선택 |
| `evaluator_type` | 평가자 유형 (end-user, expert 등) | 선택 |
| `evaluation_source` | 평가 출처 (api, cli 등) | 선택 |

## 샘플 애플리케이션

라이브러리에는 다양한 환경에서 모델 평가 기능을 사용하는 방법을 보여주는
샘플 애플리케이션이 포함되어 있습니다:

### 1. CLI 데모 (general_evaluation_demo.py)

명령줄에서 사용자 입력을 통해 모델 평가를 수집하고 NewRelic에 전송하는 데모입니다.

**주요 기능:**
- 프레임워크에 구애받지 않는 독립형 평가 클래스 구현
- CLI를 통한 평가 데이터 수집 예제
- 대화형 입력 방식으로 평가 데이터 수집

**실행 방법:**
```bash
python samples/general_evaluation_demo.py
```

### 2. FastAPI 데모 (fastapi_evaluation_demo.py)

RESTful API를 통해 모델 평가를 수집하고 NewRelic에 전송하는 웹 서버 데모입니다.

**주요 기능:**
- 평가 데이터를 REST API로 수집
- Pydantic 모델을 활용한 데이터 유효성 검사
- 클라이언트에서 사용할 수 있는 완전한 API 구현
- Swagger UI를 통한 API 문서 제공

**실행 방법:**
```bash
# 필요한 패키지 설치
pip install fastapi uvicorn

# 서버 실행
python samples/fastapi_evaluation_demo.py
```

서버가 실행되면 http://localhost:8000/docs 에서 Swagger UI 문서를 확인할 수 있습니다.

## NewRelic에서 데이터 분석

다음 NRQL 쿼리를 사용하여 수집된 평가 데이터를 분석할 수 있습니다:

```sql
-- 모델별 평균 만족도 점수
FROM LlmUserResponseEvaluation SELECT average(overall_score) FACET model_id SINCE 1 week ago

-- 모델별 정확성 점수 비교
FROM LlmUserResponseEvaluation SELECT average(accuracy_score) FACET model_id SINCE 1 day ago TIMESERIES

-- 질문 유형별 모델 성능 비교
FROM LlmUserResponseEvaluation SELECT average(overall_score), average(relevance_score) 
FACET model_id, query_type SINCE 1 week ago

-- 도메인별 모델 성능 분석
FROM LlmUserResponseEvaluation SELECT average(overall_score) 
FACET model_id, domain SINCE 1 week ago

-- 모델별 강점/약점 분석
FROM LlmUserResponseEvaluation SELECT 
  average(relevance_score) as '관련성', 
  average(accuracy_score) as '정확성', 
  average(completeness_score) as '완성도',
  average(coherence_score) as '일관성',
  average(helpfulness_score) as '유용성'
FACET model_id SINCE 2 weeks ago
```

## FAQ

**Q: Streamlit 관련 기능은 어떻게 되나요?**  
A: Streamlit 관련 코드가 제거되었습니다. 이제 라이브러리는 프레임워크 독립적인 방식으로 평가를 수집합니다.

**Q: 기존 코드를 어떻게 수정해야 하나요?**  
A: StreamlitResponseEvaluationCollector 대신 ResponseEvaluationCollector를 사용하도록 코드를 업데이트하세요.

**Q: 평가 데이터의 스키마가 변경되었나요?**  
A: 아니요, 평가 데이터의 스키마는 동일하게 유지됩니다. 모든 필드와 데이터 형식은 이전과 동일합니다. 