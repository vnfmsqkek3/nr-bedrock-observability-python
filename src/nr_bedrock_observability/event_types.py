from typing import Dict, Any, List, TypedDict, Optional, Union, Literal

# 이벤트 유형 정의
class EventType:
    LLM_COMPLETION = "LlmCompletion"
    LLM_CHAT_COMPLETION_SUMMARY = "LlmChatCompletionSummary"
    LLM_CHAT_COMPLETION_MESSAGE = "LlmChatCompletionMessage"
    LLM_EMBEDDING = "LlmEmbedding"
    LLM_SYSTEM_PROMPT = "LlmSystemPrompt"
    LLM_USER_PROMPT = "LlmUserPrompt"
    LLM_OPENSEARCH_RESULT = "LlmOpenSearchResult"
    LLM_RAG_CONTEXT = "LlmRagContext"
    LLM_FEEDBACK = "LlmFeedback"
    LLM_USER_RESPONSE_EVALUATION = "LlmUserResponseEvaluation"

# 이벤트 속성 (메타데이터) 타입
EventAttributes = Dict[str, Union[str, int, float, bool, None]]

# 이벤트 데이터 타입 - Dict 타입 힌트와 함께 주석 추가
EventData = Dict[str, Any]  # {"eventType": str, "attributes": EventAttributes}

class BedrockError:
    """
    AWS Bedrock API 오류 정보
    """
    def __init__(
        self,
        message: Optional[str] = None,
        type: Optional[str] = None,
        code: Optional[str] = None,
        status: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.message = message
        self.type = type
        self.code = code
        self.status = status
        self.request_id = request_id

class ChatCompletionMessageAttributes(TypedDict, total=False):
    """
    채팅 완성 메시지 속성
    """
    id: str
    applicationName: str
    content: str
    role: str
    completion_id: str
    sequence: str
    model: str
    vendor: str  # 'bedrock'
    prompt_type: Optional[str]
    context_source: Optional[str]
    trace_id: Optional[str]

class SystemPromptAttributes(TypedDict, total=False):
    """
    시스템 프롬프트 속성
    """
    id: str
    applicationName: str
    content: str
    model: str
    vendor: str  # 'bedrock'
    trace_id: Optional[str]
    timestamp: int
    completion_id: Optional[str]
    parent_message_id: Optional[str]

class UserPromptAttributes(TypedDict, total=False):
    """
    사용자 프롬프트 속성
    """
    id: str
    applicationName: str
    content: str
    model: str
    vendor: str  # 'bedrock'
    trace_id: Optional[str]
    timestamp: int
    completion_id: Optional[str]
    has_context: bool
    parent_message_id: Optional[str]

class OpenSearchResultAttributes(TypedDict, total=False):
    """
    OpenSearch 검색 결과 속성
    """
    id: str
    applicationName: str
    query: str
    index_name: Optional[str]
    result_content: str
    result_title: Optional[str]
    score: Optional[float]
    sequence: Optional[int]
    trace_id: Optional[str]
    timestamp: int
    total_results: Optional[int]
    response_time: Optional[int]

class RagContextAttributes(TypedDict, total=False):
    """
    RAG 컨텍스트 속성 (OpenSearch 결과를 LLM 컨텍스트로 변환)
    """
    id: str
    applicationName: str
    content: str
    source: str
    trace_id: Optional[str]
    timestamp: int
    completion_id: Optional[str]
    prompt_id: Optional[str]
    sequence: Optional[int]

class ChatCompletionSummaryAttributes(TypedDict, total=False):
    """
    채팅 완성 요약 속성
    """
    id: str
    applicationName: str
    request_model: str
    response_model: Optional[str]
    response_time: int
    timestamp: int
    api_version: Optional[str]
    region: Optional[str]
    api_key_last_four_digits: Optional[str]
    user_id: Optional[str]
    vendor: str  # 'bedrock'
    finish_reason: Optional[str]
    number_of_messages: int
    error_status: Optional[str]
    error_message: Optional[str]
    error_type: Optional[str]
    error_code: Optional[str]
    error_request_id: Optional[str]
    ingest_source: Optional[str]
    rate_limit_exceeded: Optional[bool]
    has_system_prompt: bool
    has_rag_context: bool
    trace_id: Optional[str]
    system_prompt_count: Optional[int]
    user_prompt_count: Optional[int]
    opensearch_result_count: Optional[int]
    feedback: Optional[str]
    sentiment: Optional[float]
    feedback_message: Optional[str]

class CommonSummaryAttributes:
    """
    공통 요약 속성
    """
    def __init__(
        self,
        id: str,
        application_name: str,
        request_model: Optional[str] = None,
        response_model: Optional[str] = None,
        response_time: int = 0,
        api_key_last_four_digits: Optional[str] = None,
        user_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        self.id = id
        self.application_name = application_name
        self.request_model = request_model
        self.response_model = response_model
        self.response_time = response_time
        self.api_key_last_four_digits = api_key_last_four_digits
        self.user_id = user_id
        self.error_message = error_message
        self.error_type = error_type
        self.error_code = error_code
        
    def to_dict(self) -> Dict[str, Any]:
        """
        속성을 딕셔너리로 변환
        """
        return {k: v for k, v in self.__dict__.items() if v is not None}

class EmbeddingAttributes(TypedDict, total=False):
    """
    임베딩 속성
    """
    id: str
    applicationName: str
    request_model: str
    response_model: Optional[str]
    response_time: int
    timestamp: int
    api_version: Optional[str]
    region: Optional[str]
    api_key_last_four_digits: Optional[str]
    user_id: Optional[str]
    vendor: str  # 'bedrock'
    input: str
    error_status: Optional[str]
    error_message: Optional[str]
    error_type: Optional[str]
    error_code: Optional[str]
    error_request_id: Optional[str]
    ingest_source: Optional[str]
    rate_limit_exceeded: Optional[bool]

class CompletionAttributes(TypedDict, total=False):
    """
    완성 속성
    """
    id: str
    applicationName: str
    request_model: str
    response_model: Optional[str]
    response_time: int
    timestamp: int
    api_version: Optional[str]
    region: Optional[str]
    api_key_last_four_digits: Optional[str]
    user_id: Optional[str]
    vendor: str  # 'bedrock'
    input: str
    output: str
    finish_reason: Optional[str]
    completion_tokens: Optional[int]
    prompt_tokens: Optional[int]
    total_tokens: Optional[int]
    error_status: Optional[str]
    error_message: Optional[str]
    error_type: Optional[str]
    error_code: Optional[str]
    error_request_id: Optional[str]
    ingest_source: Optional[str]
    rate_limit_exceeded: Optional[bool]
    is_streaming: Optional[bool]

class BedrockModelMapping:
    """
    Bedrock 모델 ID와 표준화된 모델 이름 간의 매핑
    """
    # 표준 모델 ID 매핑
    MODEL_MAPPING = {
        # Amazon Titan 모델
        "amazon.titan-text-lite-v1": "amazon.titan",
        "amazon.titan-text-express-v1": "amazon.titan",
        "amazon.titan-text-premier-v1": "amazon.titan",
        "amazon.titan-text-lite-v2:0": "amazon.titan-v2",
        "amazon.titan-text-express-v2:0": "amazon.titan-v2",
        "amazon.titan-text-premier-v2:0": "amazon.titan-v2",
        "amazon.titan-embed-text-v1": "amazon.titan-embed",
        "amazon.titan-embed-text-v2:0": "amazon.titan-embed-v2",
        "amazon.titan-embed-image-v1": "amazon.titan-embed-image",
        "amazon.titan-embed-g1-text-02": "amazon.titan-embed-g1",
        "amazon.titan-embed-g1-text-01": "amazon.titan-embed-g1",
        "amazon.titan-image-generator-v1": "amazon.titan-image",
        "amazon.titan-multimodal-v1": "amazon.titan-multimodal",
        "amazon.titan-multimodal-v2:0": "amazon.titan-multimodal-v2",
        
        # Anthropic Claude 모델
        "anthropic.claude-v1": "anthropic.claude",
        "anthropic.claude-v2": "anthropic.claude",
        "anthropic.claude-v2:1": "anthropic.claude",
        "anthropic.claude-instant-v1": "anthropic.claude-instant",
        "anthropic.claude-3-sonnet-20240229-v1:0": "anthropic.claude-3-sonnet",
        "anthropic.claude-3-haiku-20240307-v1:0": "anthropic.claude-3-haiku",
        "anthropic.claude-3-opus-20240229-v1:0": "anthropic.claude-3-opus",
        "anthropic.claude-3-5-sonnet-20240620-v1:0": "anthropic.claude-3-5-sonnet",
        "anthropic.claude-3-5-sonnet-20241022-v2:0": "anthropic.claude-3-5-sonnet",
        
        # AI21 Labs 모델
        "ai21.j2-mid-v1": "ai21.jurassic-2",
        "ai21.j2-ultra-v1": "ai21.jurassic-2",
        "ai21.jamba-instruct-v1:0": "ai21.jamba",
        
        # Cohere 모델
        "cohere.command-text-v14": "cohere.command",
        "cohere.command-light-text-v14": "cohere.command-light",
        "cohere.command-r-v1:0": "cohere.command-r",
        "cohere.command-r-plus-v1:0": "cohere.command-r-plus",
        "cohere.embed-english-v3": "cohere.embed",
        "cohere.embed-multilingual-v3": "cohere.embed-multilingual",
        "cohere.embed-english-light-v3:0": "cohere.embed-english-light",
        "cohere.embed-multilingual-light-v3:0": "cohere.embed-multilingual-light",
        
        # Meta 모델
        "meta.llama2-13b-chat-v1": "meta.llama2",
        "meta.llama2-70b-chat-v1": "meta.llama2",
        "meta.llama3-8b-instruct-v1:0": "meta.llama3",
        "meta.llama3-70b-instruct-v1:0": "meta.llama3",
        
        # Mistral AI 모델
        "mistral.mistral-7b-instruct-v0:2": "mistral.mistral",
        "mistral.mixtral-8x7b-instruct-v0:1": "mistral.mixtral",
        "mistral.mistral-large-2402-v1:0": "mistral.mistral-large",
        "mistral.mistral-small-2402-v1:0": "mistral.mistral-small",
        "mistral.mistral-medium-2312-v1:0": "mistral.mistral-medium",
    }
    
    @staticmethod
    def normalize_model_id(model_id: str) -> str:
        """
        Bedrock 모델 ID를 표준화된 모델 이름으로 변환
        """
        if not model_id:
            return "unknown"
            
        normalized = BedrockModelMapping.MODEL_MAPPING.get(model_id)
        if normalized:
            return normalized
            
        # 매핑에 없는 경우 모델 ID에서 기본 공급업체 추출
        if '.' in model_id:
            vendor, _ = model_id.split('.', 1)
            return f"{vendor}.unknown"
            
        return model_id

class FeedbackAttributes(TypedDict, total=False):
    """
    LLM 응답에 대한 사용자 피드백 속성
    """
    id: str
    applicationName: str
    feedback: str  # 'positive', 'negative', 'neutral'
    sentiment: float  # -1.0부터 1.0 사이의 값
    feedback_message: Optional[str]
    trace_id: Optional[str]
    completion_id: Optional[str]
    timestamp: int

class UserResponseEvaluationAttributes(TypedDict, total=False):
    """
    LLM 응답에 대한 사용자 반응 평가 속성
    """
    id: str
    applicationName: str
    user_id: Optional[str]
    session_id: Optional[str]
    trace_id: Optional[str]
    completion_id: Optional[str]
    timestamp: int
    
    # 모델 정보
    model_id: str  # 평가 대상 모델 ID (예: anthropic.claude-3-sonnet-20240229-v1:0)
    model_provider: Optional[str]  # 모델 제공 업체 (예: anthropic, amazon, mistral)
    model_name: Optional[str]  # 정규화된 모델 이름 (예: claude-3-sonnet)
    model_version: Optional[str]  # 모델 버전 (예: 20240229-v1:0)
    
    # Bedrock 지식 기반 관련
    kb_id: Optional[str]  # Bedrock 지식 기반 ID
    kb_name: Optional[str]  # 지식 기반 이름
    kb_data_source_count: Optional[int]  # 지식 기반의 데이터 소스 수
    kb_used_in_query: Optional[bool]  # 이 쿼리에서 지식 기반이 사용되었는지 여부
    
    # LangChain 관련
    langchain_used: Optional[bool]  # LangChain 사용 여부
    langchain_version: Optional[str]  # LangChain 버전
    langchain_chain_type: Optional[str]  # 사용된 체인 유형 (예: LLMChain, RetrievalQA)
    langchain_retriever_type: Optional[str]  # 사용된 검색기 유형
    langchain_embedding_model: Optional[str]  # 사용된 임베딩 모델
    
    # 만족도 평가 점수 (1-10 척도)
    overall_score: int
    
    # 모델 성능 평가 요소 (1-10 척도)
    relevance_score: Optional[int]  # 질문 관련성 점수
    accuracy_score: Optional[int]   # 정보 정확성 점수
    completeness_score: Optional[int]  # 응답 완성도/상세함 점수
    coherence_score: Optional[int]  # 응답 일관성/논리 점수
    helpfulness_score: Optional[int]  # 유용성/도움 정도 점수
    creativity_score: Optional[int]  # 창의성 점수 (필요시)
    
    # 응답 시간 관련 평가
    response_time_score: Optional[int]  # 응답 속도 만족도 점수
    response_time_ms: Optional[int]  # 실제 응답 시간 (밀리초)
    
    # 추가 피드백
    feedback_comment: Optional[str]  # 자유 형식 피드백 코멘트
    
    # 메타데이터
    query_type: Optional[str]  # 질문 유형 (factual, creative, coding 등)
    context_size: Optional[int]  # 컨텍스트 크기 (토큰)
    domain: Optional[str]  # 도메인 분야 (예: 기술, 과학, 일반 지식)
    total_tokens: Optional[int]  # 총 토큰 수
    prompt_tokens: Optional[int]  # 프롬프트 토큰 수
    completion_tokens: Optional[int]  # 완성 토큰 수
    
    # 내부 태깅
    evaluation_source: Optional[str]  # 평가 출처 (예: 'streamlit', 'api', 'cli')
    evaluator_type: Optional[str]  # 평가자 타입 (예: 'end-user', 'expert', 'developer')

# 에러 메시지에서 표준화된 오류 객체 생성
def create_error_from_exception(error: Exception) -> BedrockError:
    """
    예외에서 표준화된 오류 객체 생성
    
    :param error: 발생한 예외
    :return: 표준화된 오류 객체
    """
    error_dict = BedrockError()
    
    # 에러 메시지 추출
    error_dict.message = str(error)
    
    # 에러 유형 처리
    error_dict.type = error.__class__.__name__
    
    # 특정 Boto3/Bedrock 오류 처리
    if hasattr(error, 'response'):
        response = getattr(error, 'response')
        if isinstance(response, dict):
            # 상태 코드 추출
            if 'ResponseMetadata' in response and 'HTTPStatusCode' in response['ResponseMetadata']:
                error_dict.status = str(response['ResponseMetadata']['HTTPStatusCode'])
                
            # 요청 ID 추출
            if 'ResponseMetadata' in response and 'RequestId' in response['ResponseMetadata']:
                error_dict.request_id = response['ResponseMetadata']['RequestId']
                
            # 오류 코드 추출
            if 'Error' in response and 'Code' in response['Error']:
                error_dict.code = response['Error']['Code']
                
                # 속도 제한 오류 특별 처리
                if error_dict.code in ["ThrottlingException", "TooManyRequestsException", "ServiceQuotaExceededException"]:
                    error_dict.type = "RateLimitExceeded"
    
    return error_dict 