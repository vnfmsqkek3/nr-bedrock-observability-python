from typing import Dict, Any, List, TypedDict, Optional, Union, Literal

# 이벤트 유형 정의
class EventType:
    LLM_COMPLETION = "LlmCompletion"
    LLM_CHAT_COMPLETION_SUMMARY = "LlmChatCompletionSummary"
    LLM_CHAT_COMPLETION_MESSAGE = "LlmChatCompletionMessage"
    LLM_EMBEDDING = "LlmEmbedding"

# 이벤트 속성 (메타데이터) 타입
EventAttributes = Dict[str, Union[str, int, float, bool, None]]

# 이벤트 데이터 타입
EventData = Dict[str, Any]

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