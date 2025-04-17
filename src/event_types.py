from typing import Dict, Union, Optional, Any, List

# 이벤트 타입 정의
class EventType:
    LLM_COMPLETION = "LlmCompletion"
    LLM_CHAT_COMPLETION_SUMMARY = "LlmChatCompletionSummary"
    LLM_CHAT_COMPLETION_MESSAGE = "LlmChatCompletionMessage"
    LLM_EMBEDDING = "LlmEmbedding"

# 이벤트 속성 타입 정의
EventAttributes = Dict[str, Union[str, int, float, bool]]

# 채팅 완성 메시지 속성
class ChatCompletionMessageAttributes:
    def __init__(
        self,
        id: str,
        application_name: str,
        content: str,
        role: str,
        completion_id: str,
        sequence: int,
        model: str
    ):
        self.id = id
        self.application_name = application_name
        self.content = content
        self.role = role
        self.completion_id = completion_id
        self.sequence = sequence
        self.model = model
        self.vendor = "AWS Bedrock"

    def to_dict(self) -> EventAttributes:
        return {
            "id": self.id,
            "applicationName": self.application_name,
            "content": self.content,
            "role": self.role,
            "completion_id": self.completion_id,
            "sequence": self.sequence,
            "model": self.model,
            "vendor": self.vendor
        }

# Bedrock 오류 타입
class BedrockError:
    def __init__(self, message: Optional[str] = None, response_data: Optional[Dict[str, Any]] = None):
        self.message = message
        self.data = response_data

# 공통 요약 속성
class CommonSummaryAttributes:
    def __init__(
        self,
        id: str,
        application_name: str,
        request_model: str,
        response_model: Optional[str] = None,
        response_time: int = 0,
        api_key_last_four_digits: Optional[str] = None,
        user_id: Optional[str] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        error_code: Optional[str] = None
    ):
        self.id = id
        self.application_name = application_name
        self.request_model = request_model
        self.response_model = response_model
        self.response_time = response_time
        self.timestamp = int(1000 * __import__('time').time())
        self.api_key_last_four_digits = api_key_last_four_digits
        self.user_id = user_id
        self.vendor = "AWS Bedrock"
        self.error_message = error_message
        self.error_type = error_type
        self.error_code = error_code
        self.ingest_source = "python-bedrock-sdk"

    def to_dict(self) -> EventAttributes:
        attributes: EventAttributes = {
            "id": self.id,
            "applicationName": self.application_name,
            "request.model": self.request_model,
            "response_time": self.response_time,
            "timestamp": self.timestamp,
            "vendor": self.vendor,
            "ingest_source": self.ingest_source
        }
        
        # 선택적 필드 추가
        if self.response_model:
            attributes["response.model"] = self.response_model
        if self.api_key_last_four_digits:
            attributes["api_key_last_four_digits"] = self.api_key_last_four_digits
        if self.user_id:
            attributes["user_id"] = self.user_id
        if self.error_message:
            attributes["error_message"] = self.error_message
        if self.error_type:
            attributes["error_type"] = self.error_type
        if self.error_code:
            attributes["error_code"] = self.error_code
            
        return attributes

# 채팅 완성 요약 속성
class ChatCompletionSummaryAttributes(CommonSummaryAttributes):
    def __init__(
        self,
        finish_reason: Optional[str] = None,
        number_of_messages: int = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.finish_reason = finish_reason
        self.number_of_messages = number_of_messages

    def to_dict(self) -> EventAttributes:
        attributes = super().to_dict()
        if self.finish_reason:
            attributes["finish_reason"] = self.finish_reason
        attributes["number_of_messages"] = self.number_of_messages
        return attributes

# 임베딩 속성
class EmbeddingAttributes(CommonSummaryAttributes):
    def __init__(self, input_text: str, **kwargs):
        super().__init__(**kwargs)
        self.input_text = input_text

    def to_dict(self) -> EventAttributes:
        attributes = super().to_dict()
        attributes["input"] = self.input_text
        return attributes

# 이벤트 데이터 구조
class EventData:
    def __init__(self, event_type: str, attributes: EventAttributes):
        self.event_type = event_type
        self.attributes = attributes

    def to_dict(self) -> Dict[str, Union[str, EventAttributes]]:
        return {
            "eventType": self.event_type,
            "attributes": self.attributes
        } 