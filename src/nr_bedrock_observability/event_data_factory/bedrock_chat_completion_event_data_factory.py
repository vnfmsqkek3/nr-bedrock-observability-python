import json
import logging
import uuid
from typing import Dict, Any, Optional, Union, List

from ..event_types import EventType, EventData, EventAttributes, ChatCompletionMessageAttributes
from .common_summary_attributes_factory import CommonSummaryAttributesFactory, CommonSummaryAttributesFactoryOptions

logger = logging.getLogger(__name__)

class BedrockChatCompletionEventDataFactoryOptions:
    """
    Bedrock 채팅 완성 이벤트 데이터 팩토리 옵션
    """
    def __init__(
        self,
        request: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        response_time: int = 0,
        response_headers: Optional[Dict[str, Any]] = None,
        response_error: Optional[Any] = None
    ):
        self.request = request
        self.response_data = response_data
        self.response_time = response_time
        self.response_headers = response_headers
        self.response_error = response_error


class BedrockChatCompletionEventDataFactory:
    """
    Bedrock의 converse API 호출에 대한 이벤트 데이터 생성
    """
    def __init__(self, options: Union[CommonSummaryAttributesFactoryOptions, Dict[str, Any]]):
        if isinstance(options, dict):
            self.application_name = options['application_name']
            bedrock_configuration = options.get('bedrock_configuration')
            factory_options = CommonSummaryAttributesFactoryOptions(
                application_name=self.application_name,
                bedrock_configuration=bedrock_configuration
            )
        else:
            self.application_name = options.application_name
            factory_options = options
            
        self.common_summary_attributes_factory = CommonSummaryAttributesFactory(factory_options)
        
    def create_event_data_list(
        self, 
        options: Union[BedrockChatCompletionEventDataFactoryOptions, Dict[str, Any]]
    ) -> List[EventData]:
        """
        Bedrock converse 호출에 대한 이벤트 데이터 리스트 생성
        """
        if isinstance(options, dict):
            factory_options = BedrockChatCompletionEventDataFactoryOptions(
                request=options['request'],
                response_data=options.get('response_data'),
                response_time=options.get('response_time', 0),
                response_headers=options.get('response_headers'),
                response_error=options.get('response_error')
            )
        else:
            factory_options = options
        
        # ID 생성
        completion_id = str(uuid.uuid4())
        
        # 요청 및 응답 데이터
        request = factory_options.request
        response_data = factory_options.response_data or {}
        
        # 메시지 이벤트 데이터 생성
        message_data_list = self._create_message_event_data_list(completion_id, request, response_data)
        
        # 요약 이벤트 데이터 생성
        summary_data = self._create_summary_event_data(
            completion_id, 
            factory_options,
            len(message_data_list)
        )
        
        return message_data_list + [summary_data]
        
    def _create_message_event_data_list(
        self,
        completion_id: str,
        request: Dict[str, Any],
        response_data: Dict[str, Any]
    ) -> List[EventData]:
        """
        채팅 완성 메시지 이벤트 데이터 생성
        """
        messages = self._get_messages(request, response_data)
        model_id = request.get('modelId', '')
        
        event_data_list = []
        
        for i, message in enumerate(messages):
            # 모델에 따라 메시지 형식이 다를 수 있음
            role = message.get('role', 'unknown')
            content = self._extract_message_content(message)
            
            # 메시지 속성 생성
            message_attributes = ChatCompletionMessageAttributes(
                id=str(uuid.uuid4()),
                application_name=self.application_name,
                content=content[:4095] if content else '',  # 텍스트 길이 제한
                role=role,
                completion_id=completion_id,
                sequence=i,
                model=model_id
            )
            
            # 이벤트 데이터 생성
            event_data_list.append(
                EventData(
                    event_type=EventType.LLM_CHAT_COMPLETION_MESSAGE,
                    attributes=message_attributes.to_dict()
                )
            )
            
        return event_data_list
        
    def _create_summary_event_data(
        self,
        completion_id: str,
        options: BedrockChatCompletionEventDataFactoryOptions,
        number_of_messages: int
    ) -> EventData:
        """
        채팅 완성 요약 이벤트 데이터 생성
        """
        request = options.request
        response_data = options.response_data or {}
        
        # 특수 처리가 필요한 키
        attribute_key_special_treatments = {
            'messages': { 'skip': True }
        }
        
        # 응답에서 완료 이유 추출
        finish_reason = None
        if response_data and 'output' in response_data:
            output = response_data['output']
            if 'stopReason' in output:
                finish_reason = output['stopReason']
        
        # 공통 요약 속성 생성
        attributes = self.common_summary_attributes_factory.create_attributes(
            id=completion_id,
            request=request,
            response_data=response_data,
            response_time=options.response_time,
            response_headers=options.response_headers,
            response_error=options.response_error,
            attribute_key_special_treatments=attribute_key_special_treatments
        )
        
        # 채팅 완성 요약 특화 속성 추가
        attributes.update({
            'finish_reason': finish_reason or 'unknown',
            'number_of_messages': number_of_messages
        })
        
        # 토큰 정보 추가
        if response_data and 'usage' in response_data:
            usage = response_data['usage']
            if 'inputTokenCount' in usage:
                attributes['input_token_count'] = usage['inputTokenCount']
            if 'outputTokenCount' in usage:
                attributes['output_token_count'] = usage['outputTokenCount']
        
        return EventData(
            event_type=EventType.LLM_CHAT_COMPLETION_SUMMARY,
            attributes=attributes
        )
    
    def _get_messages(self, request: Dict[str, Any], response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        요청 및 응답에서 모든 메시지 추출
        """
        messages = []
        
        # 요청 메시지 추출
        if 'messages' in request:
            messages.extend(request['messages'])
        
        # 응답 메시지 추출
        if response_data and 'output' in response_data:
            output = response_data['output']
            if 'message' in output:
                messages.append(output['message'])
        
        return messages
    
    def _extract_message_content(self, message: Dict[str, Any]) -> str:
        """
        메시지에서 텍스트 콘텐츠 추출
        """
        # Bedrock converse API 응답 형식에 맞춤
        if 'content' in message:
            content = message['content']
            if isinstance(content, list):
                # 콘텐츠가 리스트인 경우 (텍스트 블록 목록)
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif isinstance(item, str):
                        text_parts.append(item)
                return " ".join(text_parts)
            elif isinstance(content, str):
                return content
            elif isinstance(content, dict) and 'text' in content:
                return content['text']
        
        # fallback
        return str(message.get('content', '')) 