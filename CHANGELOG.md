# 변경 이력

## v1.7.1 (2024-05-10)

### 버그 수정

- **타입 오류 수정**: `EventData` 타입 힌트를 실제 딕셔너리 생성에 사용하던 문제 해결
  - `response_evaluation.py`에서 `Type Dict cannot be instantiated` 오류 수정
  - `EventData` 타입 힌트 관련 주석 개선
  - 내부 함수에서 직접 딕셔너리를 생성하도록 변경

## v1.7.0 (2024-05-10)

### 개선 사항

- **Streamlit 응답 평가 UI**: Streamlit에 최적화된 안정적인 UI 컴포넌트 구현 완료
  - 슬라이더 조정 시 UI가 사라지는 문제 해결
  - 제출 후 평가 상태가 초기화되는 현상 수정
  - 숫자 입력 기반 UI로 안정성 향상

### 버그 수정

- **평가 상태 관리**: 세션 상태를 활용한 안정적인 상태 관리 구현
- **빈 파일 오류 해결**: `streamlit_response_evaluation.py` 파일 내용 구현으로 가져오기 오류 수정

## v1.6.0 (2024-05-09)

### 추가된 기능

- **범용 응답 평가 수집 도구**: 모든 환경에서 사용 가능한 `generic_response_evaluation` 모듈 추가
  - `send_evaluation()`: 모든 환경에서 쉽게 평가 데이터를 전송할 수 있는 함수
  - `send_evaluation_with_newrelic_agent()`: New Relic 에이전트를 직접 사용하여 평가 데이터 전송
  - `get_evaluation_collector()`: 평가 수집기를 쉽게 생성하고 관리할 수 있는 함수

- **Streamlit용 개선된 평가 UI**: Streamlit 환경에서 안정적인 평가 기능 제공
  - 슬라이더 조정 시 UI가 사라지는 문제 해결
  - 평가 제출 후 상태가 초기화되는 문제 해결
  - 직관적인 숫자 입력 기반 UI 제공

### 개선 사항

- **평가 UI 안정성**: Streamlit 세션 상태를 활용한 안정적인 평가 UI 구현
- **디버깅 도구**: 평가 상태를 쉽게 디버깅할 수 있는 개발자 도구 추가
- **코드 품질**: 타입 힌트 추가 및 코드 가독성 개선

### 호환성

- 기존 `ResponseEvaluationCollector` 클래스와 완벽하게 호환되어 기존 코드 동작 보장
- 추가적인 종속성 없이 다양한 환경에서 사용 가능

## v1.5.0

- **Bedrock 지식 기반 및 LangChain 모니터링 기능 추가**:
  - Bedrock 지식 기반 API 호출 모니터링
  - 지식 기반 ID, 이름 및 메타데이터 수집
  - LangChain 통합 및 모니터링 지원
  - 모델, 지식 기반, LangChain 조합에 따른 성능 비교

- **모델 만족도 평가 고급 기능**:
  - 모델별 토큰 사용량 자동 수집
  - 응답 시간과 만족도 간의 상관관계 분석 지원
  - 질문 유형/도메인별 모델 성능 심층 분석
  - Claude 3.5 Sonnet v2 최신 버전(anthropic.claude-3-5-sonnet-20241022-v2:0) 지원 