import json
import logging
import uuid
import time
from typing import Dict, Any, Optional, Union, List

from ..event_types import (
    EventType, EventData, EventAttributes, 
    ChatCompletionMessageAttributes,
    SystemPromptAttributes, UserPromptAttributes,
    RagContextAttributes
)
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
        response_error: Optional[Any] = None,
        trace_id: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None
    ):
        self.request = request
        self.response_data = response_data
        self.response_time = response_time
        self.response_headers = response_headers
        self.response_error = response_error
        self.trace_id = trace_id
        self.context_data = context_data


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
                response_error=options.get('response_error'),
                trace_id=options.get('trace_id'),
                context_data=options.get('context_data')
            )
        else:
            factory_options = options
        
        # ID 생성
        completion_id = str(uuid.uuid4())
        trace_id = factory_options.trace_id or str(uuid.uuid4())
        
        # 요청 및 응답 데이터
        request = factory_options.request
        response_data = factory_options.response_data or {}
        context_data = factory_options.context_data or {}
        
        # 모든 이벤트 데이터를 저장할 리스트
        all_events = []
        
        # 시스템 프롬프트 이벤트 생성
        system_prompts = self._extract_system_prompts(request, completion_id, trace_id)
        all_events.extend(system_prompts)
        
        # 사용자 프롬프트 이벤트 생성
        user_prompts = self._extract_user_prompts(request, completion_id, trace_id, context_data)
        all_events.extend(user_prompts)
        
        # RAG 컨텍스트 이벤트 생성 (있는 경우)
        rag_contexts = self._extract_rag_contexts(context_data, completion_id, trace_id)
        all_events.extend(rag_contexts)
        
        # 기존 메시지 이벤트 생성 (이전 버전과의 호환성 위해 유지)
        message_events = self._create_message_event_data_list(completion_id, request, response_data, trace_id)
        all_events.extend(message_events)
        
        # 요약 이벤트 데이터 생성
        summary_data = self._create_summary_event_data(
            completion_id, 
            factory_options,
            len(message_events),
            trace_id,
            len(system_prompts),
            len(user_prompts),
            len(rag_contexts)
        )
        all_events.append(summary_data)
        
        return all_events
    
    def _extract_system_prompts(
        self, 
        request: Dict[str, Any], 
        completion_id: str,
        trace_id: str
    ) -> List[EventData]:
        """
        요청에서 시스템 프롬프트 추출하여 이벤트 생성
        """
        events = []
        model_id = request.get('modelId', '')
        
        # 메시지 목록에서 시스템 프롬프트 추출
        if 'messages' in request:
            system_messages = [m for m in request['messages'] if m.get('role') == 'system']
            
            for i, message in enumerate(system_messages):
                content = self._extract_message_content(message)
                
                # 시스템 프롬프트 속성 생성
                prompt_id = str(uuid.uuid4())
                system_prompt_attrs = SystemPromptAttributes(
                    id=prompt_id,
                    applicationName=self.application_name,
                    content=content[:4095] if content else '',
                    model=model_id,
                    vendor='bedrock',
                    trace_id=trace_id,
                    timestamp=int(time.time() * 1000),
                    completion_id=completion_id
                )
                
                # 이벤트 데이터 생성
                events.append(
                    EventData(
                        event_type=EventType.LLM_SYSTEM_PROMPT,
                        attributes=system_prompt_attrs
                    )
                )
        
        return events
    
    def _extract_user_prompts(
        self, 
        request: Dict[str, Any], 
        completion_id: str,
        trace_id: str,
        context_data: Dict[str, Any]
    ) -> List[EventData]:
        """
        요청에서 사용자 프롬프트 추출하여 이벤트 생성
        """
        events = []
        model_id = request.get('modelId', '')
        has_context = bool(context_data and context_data.get('opensearch_results'))
        
        # 메시지 목록에서 사용자 프롬프트 추출
        if 'messages' in request:
            user_messages = [m for m in request['messages'] if m.get('role') == 'user']
            
            for i, message in enumerate(user_messages):
                content = self._extract_message_content(message)
                
                # 사용자 프롬프트 속성 생성
                prompt_id = str(uuid.uuid4())
                user_prompt_attrs = UserPromptAttributes(
                    id=prompt_id,
                    applicationName=self.application_name,
                    content=content[:4095] if content else '',
                    model=model_id,
                    vendor='bedrock',
                    trace_id=trace_id,
                    timestamp=int(time.time() * 1000),
                    completion_id=completion_id,
                    has_context=has_context
                )
                
                # 이벤트 데이터 생성
                events.append(
                    EventData(
                        event_type=EventType.LLM_USER_PROMPT,
                        attributes=user_prompt_attrs
                    )
                )
        
        return events
    
    def _extract_rag_contexts(
        self, 
        context_data: Dict[str, Any], 
        completion_id: str,
        trace_id: str
    ) -> List[EventData]:
        """
        컨텍스트 데이터에서 RAG 컨텍스트 추출하여 이벤트 생성
        """
        events = []
        
        # OpenSearch 결과가 있는 경우 RAG 컨텍스트 이벤트 생성
        if context_data and 'opensearch_results' in context_data:
            results = context_data['opensearch_results']
            
            for i, result in enumerate(results):
                # 컨텍스트 내용 구성
                title = result.get('title', 'No Title')
                content = result.get('content', 'No Content')
                context_content = f"제목: {title}\n내용: {content}"
                
                # RAG 컨텍스트 속성 생성
                context_attrs = RagContextAttributes(
                    id=str(uuid.uuid4()),
                    applicationName=self.application_name,
                    content=context_content[:4095],
                    source='opensearch',
                    trace_id=trace_id,
                    timestamp=int(time.time() * 1000),
                    completion_id=completion_id,
                    sequence=i
                )
                
                # 이벤트 데이터 생성
                events.append(
                    EventData(
                        event_type=EventType.LLM_RAG_CONTEXT,
                        attributes=context_attrs
                    )
                )
        
        return events
        
    def _create_message_event_data_list(
        self,
        completion_id: str,
        request: Dict[str, Any],
        response_data: Dict[str, Any],
        trace_id: str = None
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
            
            # 메시지 유형 결정
            prompt_type = None
            context_source = None
            
            if role == 'system':
                prompt_type = 'system'
            elif role == 'user':
                prompt_type = 'user'
            elif role == 'assistant':
                prompt_type = 'assistant'
            
            # 메시지 속성 생성
            message_attributes = ChatCompletionMessageAttributes(
                id=str(uuid.uuid4()),
                applicationName=self.application_name,
                content=content[:4095] if content else '',  # 텍스트 길이 제한
                role=role,
                completion_id=completion_id,
                sequence=i,
                model=model_id,
                prompt_type=prompt_type,
                context_source=context_source,
                trace_id=trace_id
            )
            
            # 이벤트 데이터 생성
            event_data_list.append(
                EventData(
                    event_type=EventType.LLM_CHAT_COMPLETION_MESSAGE,
                    attributes=message_attributes
                )
            )
            
        return event_data_list
        
    def _create_summary_event_data(
        self,
        completion_id: str,
        options: BedrockChatCompletionEventDataFactoryOptions,
        number_of_messages: int,
        trace_id: str = None,
        system_prompt_count: int = 0,
        user_prompt_count: int = 0,
        rag_context_count: int = 0
    ) -> EventData:
        """
        채팅 완성 요약 이벤트 데이터 생성
        """
        request = options.request
        response_data = options.response_data or {}
        
        # 특수 처리가 필요한 키
        attribute_key_special_treatments = {
            'messages': { 'skip': True },
            'context_data': { 'skip': True }
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
            'number_of_messages': number_of_messages,
            'has_system_prompt': system_prompt_count > 0,
            'has_rag_context': rag_context_count > 0,
            'trace_id': trace_id,
            'system_prompt_count': system_prompt_count,
            'user_prompt_count': user_prompt_count,
            'opensearch_result_count': rag_context_count
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