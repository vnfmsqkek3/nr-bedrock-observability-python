import json
import logging
import uuid
import io  # 바이트 입출력을 위한 io 모듈
from typing import Dict, Any, Optional, Union, List

from ..event_types import EventType, EventData, EventAttributes, EmbeddingAttributes
from .common_summary_attributes_factory import CommonSummaryAttributesFactory, CommonSummaryAttributesFactoryOptions

logger = logging.getLogger(__name__)

class BedrockEmbeddingEventDataFactoryOptions:
    """
    Bedrock 임베딩 이벤트 데이터 팩토리 옵션
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


class BedrockEmbeddingEventDataFactory:
    """
    Bedrock 임베딩 API 호출에 대한 이벤트 데이터 생성
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
        options: Union[BedrockEmbeddingEventDataFactoryOptions, Dict[str, Any]]
    ) -> EventData:
        """
        Bedrock 임베딩 호출에 대한 이벤트 데이터 생성
        """
        if isinstance(options, dict):
            factory_options = BedrockEmbeddingEventDataFactoryOptions(
                request=options['request'],
                response_data=options.get('response_data'),
                response_time=options.get('response_time', 0),
                response_headers=options.get('response_headers'),
                response_error=options.get('response_error')
            )
        else:
            factory_options = options
        
        # ID 생성
        embedding_id = str(uuid.uuid4())
        
        # 요청 및 응답 데이터
        request = factory_options.request
        response_data = factory_options.response_data or {}
        
        # 요청 본문과 응답 본문 파싱
        request_body = {}
        if 'body' in request and request['body']:
            try:
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
                    # StreamingBody 객체인 경우 - 복제하여 사용
                    position = 0
                    if hasattr(response_data['body'], 'tell'):
                        try:
                            position = response_data['body'].tell()  # 현재 위치 저장
                        except:
                            pass
                    
                    # 현재 위치에서 내용 읽기
                    body_content = response_data['body'].read()
                    
                    # 원본 위치 복원 (가능한 경우)
                    if hasattr(response_data['body'], 'seek'):
                        try:
                            response_data['body'].seek(position)  # 원래 위치로 되돌리기
                        except:
                            # 위치 복원 실패 시 새 객체로 대체
                            if isinstance(body_content, bytes):
                                response_data['body'] = io.BytesIO(body_content)
                    else:
                        # seek이 없는 경우 새 객체로 대체
                        if isinstance(body_content, bytes):
                            response_data['body'] = io.BytesIO(body_content)
                    
                    # 파싱
                    response_body = json.loads(body_content)
                elif isinstance(response_data['body'], str):
                    response_body = json.loads(response_data['body'])
                else:
                    response_body = response_data['body']
            except Exception as e:
                logger.warning(f"Failed to parse response body: {e}")
                response_body = {}
        
        # 입력 텍스트 추출
        input_text = self._extract_input_text(request_body)
        
        # 모델 ID 추출
        model_id = request.get('modelId', '')
        
        # 기본 속성 이외의 특수 처리가 필요한 키
        attribute_key_special_treatments = {
            'body': {
                'skip': True  # body는 이벤트에 포함하지 않음
            }
        }
        
        # 임베딩 속성 객체 생성
        embedding_attributes = EmbeddingAttributes(
            input_text=input_text[:4095],  # 텍스트 길이 제한
            id=embedding_id,
            application_name=self.application_name,
            request_model=model_id,
            response_model=model_id,
            response_time=factory_options.response_time
        )
        
        # 공통 요약 속성 추가
        common_attributes = self.common_summary_attributes_factory.create_attributes(
            id=embedding_id,
            request=request,
            response_data=response_data,
            response_time=factory_options.response_time,
            response_headers=factory_options.response_headers,
            response_error=factory_options.response_error,
            attribute_key_special_treatments=attribute_key_special_treatments
        )
        
        # 임베딩 특화 속성 추가
        attributes = {**embedding_attributes.to_dict(), **common_attributes}
        
        # 임베딩 벡터 크기 추가
        if response_body and 'embedding' in response_body:
            embedding = response_body['embedding']
            if isinstance(embedding, list):
                attributes['embedding_dimensions'] = len(embedding)
            elif 'embedding' in embedding and isinstance(embedding['embedding'], list):
                attributes['embedding_dimensions'] = len(embedding['embedding'])
                
        # 토큰 정보 추가
        if response_body and 'usage' in response_body:
            usage = response_body['usage']
            if 'inputTokenCount' in usage:
                attributes['input_token_count'] = usage['inputTokenCount']
            if 'outputTokenCount' in usage:
                attributes['output_token_count'] = usage['outputTokenCount']
        
        return EventData(
            event_type=EventType.LLM_EMBEDDING,
            attributes=attributes
        )
    
    def _extract_input_text(self, request_body: Dict[str, Any]) -> str:
        """
        요청에서 입력 텍스트 추출
        """
        if 'inputText' in request_body:
            return request_body['inputText']
        elif 'text' in request_body:
            return request_body['text']
        elif 'input' in request_body:
            if isinstance(request_body['input'], str):
                return request_body['input']
            elif isinstance(request_body['input'], list):
                # 배치 요청인 경우 첫 번째 항목만 사용
                if len(request_body['input']) > 0:
                    if isinstance(request_body['input'][0], str):
                        return request_body['input'][0]
                    elif isinstance(request_body['input'][0], dict) and 'text' in request_body['input'][0]:
                        return request_body['input'][0]['text']
        
        return "" 