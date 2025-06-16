# 변경 이력

## v2.2.0 (2024-12-19)

### 주요 기능 추가

- **Streamlit 완전 통합**: `create_streamlit_evaluation_ui()`, `create_streamlit_nrql_queries()`, `get_streamlit_session_info()` 함수 추가
- **텍스트 추출 자동화**: 응답 텍스트 추출도 라이브러리에서 자동 처리 (`extract_claude_response_text` 불필요)
- **UI 헬퍼 함수**: 평가 UI, NRQL 쿼리, 세션 관리 모두 라이브러리에서 제공
- **제로 New Relic 코드**: 앱에서 New Relic 관련 코드 완전 제거 (라이브러리가 모든 이벤트 전송 자동 처리)

### 개선 사항

- **개발자 경험 혁신**: 앱에서 `import newrelic`, `extract_claude_response_text` 등 불필요
- **완전한 Streamlit 지원**: 프롬프트 설정, 파라미터 조정, 평가, 모니터링 모두 한 화면에서
- **제로 보일러플레이트**: 텍스트 추출, 이벤트 전송, UI 생성 모두 자동화

### 🚀 자동 패치 기능 추가

**🎯 완전한 제로 설정 모니터링 구현**

#### 새로운 기능
- **enable_auto_patch()**: boto3.client('bedrock-runtime') 자동 패치 기능
- **disable_auto_patch()**: 자동 패치 비활성화
- 모든 bedrock-runtime 클라이언트가 자동으로 모니터링 활성화
- 기존 코드 변경 없이 완전한 New Relic 통합

#### 사용 방법
```python
from nr_bedrock_observability import enable_auto_patch

# 한 번만 호출하면 모든 boto3.client('bedrock-runtime')가 자동으로 모니터링됩니다
enable_auto_patch(application_name="my-app")

# 이제 일반적인 boto3 코드가 자동으로 New Relic에 데이터를 전송합니다
client = boto3.client('bedrock-runtime', region_name='us-east-1')
response = client.invoke_model(...)  # 자동으로 모니터링됨!
```

#### 개선사항
- simple_streamlit_example.py 완전 단순화
- monitor_bedrock() 직접 호출 불필요
- 기존 boto3 코드와 100% 호환
- 자동으로 모든 Streamlit 통합 기능 활성화

## v2.1.0 (2024-12-19)

### 주요 기능 추가

- **완전 자동화 모드**: 단순히 `monitor_bedrock()` 호출만으로 모든 New Relic 이벤트 자동 수집
- **Streamlit 완전 통합**: `streamlit_integration=True` 옵션으로 세션 상태 자동 관리
- **자동 이벤트 기록**: `auto_record_events=True`로 역할별/응답 이벤트 자동 기록
- **제로 설정 모니터링**: 앱 코드에서 수동 이벤트 기록 코드 완전 제거

### 개선 사항

- **개발자 경험 대폭 향상**: 3줄의 코드로 완전한 New Relic 모니터링 구현
- **제로 보일러플레이트**: 추가 설정이나 수동 코드 작성 없이 즉시 사용 가능
- **Streamlit 네이티브 지원**: 세션 상태와 완벽하게 통합된 모니터링

## v2.0.5 (2024-12-19)

### 주요 기능 추가

- **완전 자동화 모드**: `auto_generate_ids` 및 `auto_extract_context` 옵션 추가
- **자동 ID 생성**: trace_id, completion_id 자동 생성 기능
- **자동 컨텍스트 추출**: 요청 본문에서 user_query 자동 추출 기능
- **대화 및 사용자 ID 지원**: conversation_id, user_id 옵션 추가

### 개선 사항

- **사용자 편의성 대폭 향상**: 단순히 monitor_bedrock() 호출만으로 모든 기능 자동 활성화
- **Claude 메시지 형식과 일반 프롬프트 형식 모두에서 사용자 쿼리 자동 추출**
- **Converse API에서도 사용자 메시지 자동 추출 지원**

## v2.0.4 (2024-12-19)

### 주요 기능 추가

- **Completion ID 동기화**: 앱에서 생성한 completion_id와 라이브러리에서 New Relic에 전송하는 completion_id가 일치하도록 개선
  - 모든 이벤트 팩토리에서 `context_data.completion_id`를 우선 사용하도록 수정
  - BedrockCompletionEventDataFactory와 BedrockChatCompletionEventDataFactory에서 동기화 지원
  - New Relic Span details에서 앱과 라이브러리의 ID가 일치하게 됨

- **New Relic 라이센스 키 자동 감지**: 다양한 소스에서 자동으로 라이센스 키를 찾는 기능 추가
  - 우선순위: 직접 제공된 키 → 환경변수 → New Relic 에이전트 설정 → newrelic.ini 파일
  - `_get_newrelic_license_key()` 함수 추가로 자동 감지 구현
  - 사용자가 라이센스 키를 수동으로 설정하지 않아도 자동으로 찾아서 사용

### 개선 사항

- **라이브러리 사용성 향상**: 사용자는 단순히 `{'application_name': 'app-name'}`만 제공하면 됨
- **로깅 개선**: 라이센스 키를 어디서 찾았는지 로그로 알려줌
- **에러 처리 강화**: 라이센스 키를 찾지 못한 경우에도 안정적으로 동작

### 호환성

- 기존 API와 100% 호환 유지
- 기존 코드 수정 없이 새로운 기능 자동 적용

## v2.0.3 (2024-12-19)

### 버전 업데이트

- **패키지 버전 동기화**: setup.py와 __init__.py 파일의 버전을 2.0.3으로 통일
- **안정성 개선**: 기존 기능들의 안정성 및 호환성 유지

## v2.0.2 (2024-07-02)

### 개선 사항

- **Streamlit 평가 UI 개선**: 
  - `create_evaluation_ui()` 함수에 temperature와 top_p 파라미터 추가
  - 평가 UI에서 모델 파라미터(temperature, top_p) 정보를 포함하여 전송하도록 개선
  - `create_evaluation_debug_ui()` 함수에서 테스트 평가 전송 시 파라미터 지원

### 호환성 개선

- **평가 데이터 수집 도구 호환성 개선**:
  - `send_evaluation_with_newrelic_agent()` 함수에 temperature와 top_p 파라미터 명시적 지원
  - API 호출 시 파라미터를 쉽게 전달할 수 있도록 인터페이스 개선

## v2.0.1 (2024-07-01)

### 버그 수정

- **Bedrock 대시보드 헬퍼 함수 수정**: 
  - `record_bedrock_response()` 함수에 temperature와 top_p 파라미터 추가
  - 다양한 모델 호출 방식에서 temperature와 top_p 파라미터 지원
  - 모니터링 앱에서 파라미터 전달 시 호환성 문제 해결

## v2.0.0 (2024-06-30)

### 주요 기능 추가

- **Temperature, Top_P 파라미터 수집**: LLM 모델 호출 시 사용된 temperature와 top_p 파라미터 수집 기능 추가
  - `LlmCompletion` 이벤트에 temperature와 top_p 필드 추가
  - `LlmChatCompletionSummary` 이벤트에 temperature와 top_p 필드 추가
  - `LlmUserResponseEvaluation` 이벤트에 temperature와 top_p 필드 추가
  - 다양한 모델 및 API 호출 방식에 대응하여 파라미터 추출 로직 구현
  - 모델별 기본값 처리 및 예외 상황 대응 로직 추가

### 버전 변경 이유

- API 응답 구조 변경에 따른 메이저 버전 업데이트
- New Relic 대시보드에서 temperature와 top_p에 따른 성능 분석 기능 지원

## v1.7.3 (2024-06-28)

### 개선 사항

- **대시보드 헬퍼 기능 개선**: `bedrock_dashboard_helpers.py`에서 NRQL 쿼리 기능 개선
  - 토큰 사용량 분석 쿼리 개선: 산점도 방식으로 변경하여 가시성 향상
  - `range()` 함수 사용 대신 직접 토큰과 만족도 관계를 표시하는 방식으로 변경
  - 시간 범위를 월 단위에서 시간 단위로 변경하여 최신 데이터 접근성 개선

## v1.7.2 (2024-05-15)

### 버그 수정

- **Claude 3.5 토큰 추출 기능 개선**: Claude 3.5 모델의 토큰 사용량 정보 추출 문제 해결
  - `usage: {'input_tokens': 1672, 'output_tokens': 148}` 형태의 응답 구조 지원
  - 다양한 형태의 응답 구조에서 토큰 정보를 안정적으로 추출하는 기능 추가

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