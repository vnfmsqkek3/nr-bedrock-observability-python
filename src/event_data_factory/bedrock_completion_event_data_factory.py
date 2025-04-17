import json
import logging
import uuid
from typing import Dict, Any, Optional, Union
import time

from ..event_types import EventType, EventData, EventAttributes
from .common_summary_attributes_factory import CommonSummaryAttributesFactory, CommonSummaryAttributesFactoryOptions

logger = logging.getLogger(__name__)

class BedrockCompletionEventDataFactoryOptions:
    """
    Bedrock 완성 이벤트 데이터 팩토리 옵션
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

class BedrockCompletionEventDataFactory:
    """
    invoke_model API 호출에 대한 이벤트 데이터 생성
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
        
    def create_event_data(
        self, 
        options: Union[BedrockCompletionEventDataFactoryOptions, Dict[str, Any]]
    ) -> EventData:
        """
        Bedrock invoke_model 호출에 대한 이벤트 데이터 생성
        """
        if isinstance(options, dict):
            factory_options = BedrockCompletionEventDataFactoryOptions(
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
        
        # 기본 속성 이외의 특수 처리가 필요한 키
        attribute_key_special_treatments = {
            'body': {
                'skip': True  # body는 이벤트에 포함하지 않음
            }
        }
        
        # 요청 본문과 응답 본문 파싱
        request_body = {}
        if 'body' in request and request['body']:
            try:
                # body는 JSON 문자열 또는 이미 파싱된 객체일 수 있음
                if isinstance(request['body'], str):
                    request_body = json.loads(request['body'])
                else:
                    request_body = request['body']
            except Exception as e:
                logger.warning(f"Failed to parse request body: {e}")
                request_body = {}
                
        response_body = {}
        if response_data and 'body' in response_data:
            try:
                if hasattr(response_data['body'], 'read'):
                    # StreamingBody 객체인 경우
                    body_content = response_data['body'].read()
                    response_body = json.loads(body_content)
                elif isinstance(response_data['body'], str):
                    response_body = json.loads(response_data['body'])
                else:
                    response_body = response_data['body']
            except Exception as e:
                logger.warning(f"Failed to parse response body: {e}")
                response_body = {}
        
        # 완성 텍스트 추출 (모델별 다른 응답 형식 처리)
        completion_text = self._extract_completion_text(request, response_body)
        
        # 모델 ID 추출
        model_id = request.get('modelId', '')
        
        # 공통 요약 속성 생성
        attributes = self.common_summary_attributes_factory.create_attributes(
            id=completion_id,
            request=request,
            response_data=response_data,
            response_time=factory_options.response_time,
            response_headers=factory_options.response_headers,
            response_error=factory_options.response_error,
            attribute_key_special_treatments=attribute_key_special_treatments
        )
        
        # 완성 특화 속성 추가
        attributes.update({
            'completion_text': completion_text[:4095] if completion_text else '',  # 텍스트 길이 제한
            'prompt': self._extract_prompt(request_body, model_id)[:4095],  # 텍스트 길이 제한
            'model': model_id
        })
        
        # 토큰 정보 추가
        if response_body and 'usage' in response_body:
            usage = response_body['usage']
            if 'inputTokenCount' in usage:
                attributes['input_token_count'] = usage['inputTokenCount']
            if 'outputTokenCount' in usage:
                attributes['output_token_count'] = usage['outputTokenCount']
        
        return EventData(
            event_type=EventType.LLM_COMPLETION,
            attributes=attributes
        )
    
    def _extract_completion_text(self, request: Dict[str, Any], response_body: Dict[str, Any]) -> str:
        """
        모델별 응답에서 완성 텍스트 추출
        """
        model_id = request.get('modelId', '').lower()
        
        # Amazon Titan 모델
        if 'amazon.titan' in model_id:
            if response_body and 'results' in response_body and len(response_body['results']) > 0:
                return response_body['results'][0].get('outputText', '')
                
        # Anthropic Claude 모델
        elif 'anthropic.claude' in model_id:
            if response_body and 'completion' in response_body:
                return response_body['completion']
                
        # 기본 응답 처리
        if response_body and 'text' in response_body:
            return response_body['text']
        elif response_body and 'generated_text' in response_body:
            return response_body['generated_text']
            
        # AI21, Cohere, Stable Diffusion 등 다른 모델에 대한 처리도 추가 가능
            
        return ""
        
    def _extract_prompt(self, request_body: Dict[str, Any], model_id: str) -> str:
        """
        모델별 요청에서 프롬프트 추출
        """
        model_id = model_id.lower()
        
        # Amazon Titan 모델
        if 'amazon.titan' in model_id:
            return request_body.get('inputText', '')
            
        # Anthropic Claude 모델
        elif 'anthropic.claude' in model_id:
            return request_body.get('prompt', '')
            
        # 기본 요청 처리
        if 'prompt' in request_body:
            return request_body['prompt']
        elif 'text' in request_body:
            return request_body['text']
        elif 'input' in request_body:
            return request_body['input']
            
        # AI21, Cohere, Stable Diffusion 등 다른 모델에 대한 처리도 추가 가능
            
        return "" 