import json
import logging
from typing import Dict, Any, Optional, Union
import uuid

from ..event_types import CommonSummaryAttributes, BedrockError, EventAttributes

logger = logging.getLogger(__name__)

class CommonSummaryAttributesFactoryOptions:
    """
    공통 요약 속성 팩토리를 위한 옵션
    """
    def __init__(
        self,
        application_name: str,
        bedrock_configuration: Optional[Dict[str, Any]] = None
    ):
        self.application_name = application_name
        self.bedrock_configuration = bedrock_configuration

class CommonSummaryAttributesFactory:
    """
    공통 요약 속성을 생성하는 팩토리
    """
    def __init__(self, options: Union[CommonSummaryAttributesFactoryOptions, Dict[str, Any]]):
        if isinstance(options, dict):
            self.options = CommonSummaryAttributesFactoryOptions(
                application_name=options['application_name'],
                bedrock_configuration=options.get('bedrock_configuration')
            )
        else:
            self.options = options
            
        self.application_name = self.options.application_name
        self.bedrock_configuration = self.options.bedrock_configuration
        
    def create_attributes(
        self,
        id: str,
        request: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        response_time: int = 0,
        response_headers: Optional[Dict[str, Any]] = None,
        response_error: Optional[BedrockError] = None,
        attribute_key_special_treatments: Optional[Dict[str, Dict[str, bool]]] = None
    ) -> Dict[str, Any]:
        """
        공통 요약 속성 생성
        """
        # 기본값
        result_id = id or str(uuid.uuid4())
        
        # 요청에서 모델 정보 추출
        model_id = None
        if 'modelId' in request:
            model_id = request['modelId']
            
        # 응답 모델 (응답 데이터에서 얻을 수 있는 경우)
        response_model = None
        if response_data and 'modelId' in response_data:
            response_model = response_data['modelId']
            
        # 에러 정보 추출
        error_status = None
        error_message = None
        error_type = None
        error_code = None
        
        if response_error:
            error_message = response_error.message
            if hasattr(response_error, 'data') and response_error.data:
                error_data = response_error.data
                if 'message' in error_data:
                    error_message = error_data['message']
                if 'code' in error_data:
                    error_code = error_data['code']
                if 'type' in error_data:
                    error_type = error_data['type']
                    
        # API 키 정보 (마지막 4자리만)
        api_key_last_four_digits = None
        if self.bedrock_configuration and 'aws_access_key_id' in self.bedrock_configuration:
            key = self.bedrock_configuration['aws_access_key_id']
            if key and len(key) >= 4:
                api_key_last_four_digits = key[-4:]
                
        # 사용자 ID
        user_id = None
        if self.bedrock_configuration and 'user_id' in self.bedrock_configuration:
            user_id = self.bedrock_configuration['user_id']
            
        # 요청에서 사용자 ID 추출 (override)
        if request and 'user' in request:
            user_id = request['user']
            
        # 공통 속성 생성
        common_summary_attributes = CommonSummaryAttributes(
            id=result_id,
            application_name=self.application_name,
            request_model=model_id,
            response_model=response_model,
            response_time=response_time,
            api_key_last_four_digits=api_key_last_four_digits,
            user_id=user_id,
            error_message=error_message,
            error_type=error_type,
            error_code=error_code
        )
        
        # 응답 헤더에서 속성 추출 (필요시)
        if response_headers:
            self._extract_response_headers(common_summary_attributes, response_headers)
            
        return common_summary_attributes.to_dict()
    
    def _extract_response_headers(
        self, 
        common_summary_attributes: CommonSummaryAttributes, 
        headers: Dict[str, Any]
    ) -> None:
        """
        응답 헤더에서 필요한 정보를 추출하여 공통 속성에 추가
        """
        # 여기에서 Bedrock API가 반환하는 중요한 헤더 정보를 추출할 수 있습니다
        # 예: 속도 제한, 토큰 사용량 등
        pass 