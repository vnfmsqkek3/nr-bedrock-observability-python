# New Relic AWS Bedrock Observability for Python

AWS Bedrock API 호출을 모니터링하고 성능 지표를 New Relic에 전송하는 라이브러리입니다.

## 최신 업데이트 (v2.0.0)

- **Temperature, Top_P 파라미터 수집 기능 추가**:
  - LLM 모델 호출 시 사용된 temperature와 top_p 파라미터 자동 수집
  - 모든 이벤트 타입(`LlmCompletion`, `LlmChatCompletionSummary`, `LlmUserResponseEvaluation`)에 파라미터 데이터 추가
  - 모델별 온도 및 top_p 값에 따른 성능 분석 가능
  - New Relic 대시보드에서 파라미터 값에 따른 응답 품질 상관관계 분석 지원

- **Bedrock 지식 기반 및 LangChain 모니터링 기능**:
  - Bedrock 지식 기반 API 호출 모니터링
  - 지식 기반 ID, 이름 및 메타데이터 수집
  - LangChain 통합 및 모니터링 지원
  - 모델, 지식 기반, LangChain 조합에 따른 성능 비교

- **모델 만족도 평가 고급 기능**:
  - 모델별 토큰 사용량 자동 수집
  - 응답 시간과 만족도 간의 상관관계 분석 지원
  - 질문 유형/도메인별 모델 성능 심층 분석
  - Claude 3.5 Sonnet v2 최신 버전(anthropic.claude-3-5-sonnet-20241022-v2:0) 지원

## 업데이트 히스토리

### v2.0.0
- LLM 모델 파라미터(temperature, top_p) 수집 기능 추가
- 모든 이벤트 타입에 파라미터 데이터 필드 추가
- 파라미터에 따른 응답 품질 상관관계 분석 지원
- 다양한 모델 및 API 호출 방식에 대응하는 파라미터 추출 로직 구현

### v1.7.3
- 대시보드 헬퍼 기능 개선
- 토큰 사용량 분석 쿼리 개선 및 가시성 향상
- 시간 범위 조정 및 데이터 접근성 개선

### v1.7.2
- Claude 3.5 토큰 추출 기능 개선
- 다양한 응답 구조에서 토큰 정보 안정적 추출
- 코드 중복 제거 및 유지 관리성 향상

### v1.5.0
- Bedrock 지식 기반 모니터링 추가
- LangChain 통합 및 모니터링 기능 추가
- 토큰 사용량 및 응답 시간 자동 수집
- Claude 3.5 Sonnet v2 최신 버전 지원 강화

### v1.4.0
- LLM 모델 만족도 평가 기능 추가 (10점 만점 기준)
- 모델별 성능 비교 기능 추가
- 질문 유형/도메인별 분석 지원
- 향상된 Streamlit UI 컴포넌트 제공

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

### 모델 평가 분석 쿼리

```sql
-- 모델별 평균 만족도 점수
FROM LlmUserResponseEvaluation SELECT average(overall_score) FACET model_id SINCE 1 week ago

-- 모델별 정확성 점수 비교
FROM LlmUserResponseEvaluation SELECT average(accuracy_score) FACET model_id SINCE 1 day ago TIMESERIES

-- 질문 유형별 모델 성능 비교
FROM LlmUserResponseEvaluation SELECT average(overall_score), average(relevance_score), average(completeness_score) FACET model_id, query_type SINCE 1 week ago

-- 도메인별 모델 성능 분석
FROM LlmUserResponseEvaluation SELECT average(overall_score) FACET model_id, domain SINCE 1 week ago

-- 모델별 강점/약점 분석
FROM LlmUserResponseEvaluation SELECT 
  average(relevance_score) as '관련성', 
  average(accuracy_score) as '정확성', 
  average(completeness_score) as '완성도',
  average(coherence_score) as '일관성',
  average(helpfulness_score) as '유용성'
FACET model_id SINCE 2 weeks ago

-- Temperature와 Top_P 파라미터에 따른 모델 성능 분석
FROM LlmUserResponseEvaluation SELECT 
  average(overall_score) as '평균 만족도'
FACET model_id, temperature WHERE temperature IS NOT NULL SINCE 1 week ago

-- Temperature 값에 따른 응답 품질 산점도
FROM LlmCompletion SELECT 
  temperature as 'Temperature', 
  response_time as '응답 시간(ms)'
WHERE temperature IS NOT NULL SINCE 1 week ago LIMIT 500

-- Top_P 값에 따른 토큰 사용량 상관관계
FROM LlmCompletion SELECT 
  top_p as 'Top_P', 
  prompt_tokens + completion_tokens as '총 토큰'
WHERE top_p IS NOT NULL AND prompt_tokens IS NOT NULL AND completion_tokens IS NOT NULL 
SINCE 1 day ago LIMIT 1000

-- Temperature/Top_P 값 분포 확인
FROM LlmCompletion SELECT histogram(temperature, 10) WHERE temperature IS NOT NULL SINCE 1 day ago
FROM LlmCompletion SELECT histogram(top_p, 10) WHERE top_p IS NOT NULL SINCE 1 day ago
```

### 지식 기반 및 LangChain 분석 쿼리

```sql
-- 지식 기반 사용 여부에 따른 모델 성능 비교
FROM LlmUserResponseEvaluation SELECT average(overall_score), average(accuracy_score) FACET model_id, kb_used_in_query SINCE 1 week ago

-- 지식 기반별 성능 분석
FROM LlmUserResponseEvaluation WHERE kb_id IS NOT NULL SELECT average(overall_score) FACET kb_id, model_id SINCE 1 week ago

-- LangChain 사용 여부에 따른 모델 성능 비교
FROM LlmUserResponseEvaluation SELECT average(overall_score) FACET model_id, langchain_used SINCE 1 week ago

-- 응답 시간과 만족도 상관관계
FROM LlmUserResponseEvaluation SELECT average(overall_score), average(response_time_ms) FACET model_id TIMESERIES SINCE 1 day ago

-- 토큰 사용량 분석
FROM LlmUserResponseEvaluation SELECT 
  average(total_tokens) as '총 토큰', 
  average(prompt_tokens) as '프롬프트 토큰',
  average(completion_tokens) as '응답 토큰'
FACET model_id SINCE 1 week ago
```

### RAG 워크플로우 분석 쿼리

```