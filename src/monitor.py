import time
import logging
from typing import Dict, Any, Optional, Union, Callable, TypeVar, cast
import inspect
import json

from .events_client import create_event_client, EventClientOptions, BedrockEventClient
from .event_data_factory import (
    BedrockCompletionEventDataFactory,
    BedrockChatCompletionEventDataFactory,
    BedrockEmbeddingEventDataFactory
)

logger = logging.getLogger(__name__)

T = TypeVar('T')  # 제네릭 타입 변수

class MonitorBedrockOptions:
    """
    AWS Bedrock 모니터링 옵션
    """
    def __init__(
        self,
        application_name: str,
        new_relic_api_key: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        self.application_name = application_name
        self.new_relic_api_key = new_relic_api_key
        self.host = host
        self.port = port

def monitor_bedrock(
    bedrock_client: Any,
    options: Union[MonitorBedrockOptions, Dict[str, Any]]
) -> Any:
    """
    AWS Bedrock 클라이언트를 모니터링하기 위해 패치
    
    :param bedrock_client: boto3.client('bedrock-runtime') 인스턴스
    :param options: 모니터링 옵션
    :return: 패치된 Bedrock 클라이언트
    """
    if not bedrock_client:
        raise ValueError("Bedrock client is missing")
        
    # 옵션 처리
    if isinstance(options, dict):
        if 'application_name' not in options:
            raise ValueError("application_name is required")
        monitor_options = MonitorBedrockOptions(
            application_name=options['application_name'],
            new_relic_api_key=options.get('new_relic_api_key'),
            host=options.get('host'),
            port=options.get('port')
        )
    else:
        monitor_options = options
        
    # Bedrock 설정 추출
    bedrock_configuration = None
    if hasattr(bedrock_client, '_client_config'):
        bedrock_configuration = bedrock_client._client_config.__dict__
        
    # 이벤트 클라이언트 생성
    event_client = create_event_client(monitor_options)
    
    # 이벤트 데이터 팩토리 생성
    completion_event_data_factory = BedrockCompletionEventDataFactory({
        'application_name': monitor_options.application_name,
        'bedrock_configuration': bedrock_configuration
    })
    
    chat_completion_event_data_factory = BedrockChatCompletionEventDataFactory({
        'application_name': monitor_options.application_name,
        'bedrock_configuration': bedrock_configuration
    })
    
    embedding_event_data_factory = BedrockEmbeddingEventDataFactory({
        'application_name': monitor_options.application_name,
        'bedrock_configuration': bedrock_configuration
    })
    
    # 원본 메서드 저장
    original_invoke_model = bedrock_client.invoke_model
    original_converse = bedrock_client.converse
    
    # API 패치 함수
    def patch_invoke_model(
        invoke_model_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        invoke_model 함수 패치
        """
        def patched_invoke_model(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_invoke_model)
            
            # 응답 모니터링
            return monitor_response(
                lambda: invoke_model_func(*args, **kwargs),
                lambda response_info: _handle_invoke_model_response(
                    request, 
                    response_info, 
                    completion_event_data_factory, 
                    event_client
                )
            )
            
        return patched_invoke_model
    
    def patch_converse(
        converse_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        converse 함수 패치
        """
        def patched_converse(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_converse)
            
            # 응답 모니터링
            return monitor_response(
                lambda: converse_func(*args, **kwargs),
                lambda response_info: _handle_converse_response(
                    request, 
                    response_info, 
                    chat_completion_event_data_factory, 
                    event_client
                )
            )
            
        return patched_converse
    
    # Bedrock 클라이언트 패치
    bedrock_client.invoke_model = patch_invoke_model(original_invoke_model)
    bedrock_client.converse = patch_converse(original_converse)
    
    # 임베딩 메서드가 있는지 확인
    if hasattr(bedrock_client, 'create_embedding'):
        original_create_embedding = bedrock_client.create_embedding
        
        def patch_create_embedding(
            create_embedding_func: Callable[..., Any]
        ) -> Callable[..., Any]:
            """
            create_embedding 함수 패치
            """
            def patched_create_embedding(*args, **kwargs):
                # 요청 정보 추출
                request = _extract_request_from_args_kwargs(args, kwargs, original_create_embedding)
                
                # 응답 모니터링
                return monitor_response(
                    lambda: create_embedding_func(*args, **kwargs),
                    lambda response_info: _handle_embedding_response(
                        request, 
                        response_info, 
                        embedding_event_data_factory, 
                        event_client
                    )
                )
                
            return patched_create_embedding
            
        bedrock_client.create_embedding = patch_create_embedding(original_create_embedding)
    
    # New Relic에 패치 정보 기록
    logger.info(f"AWS Bedrock client patched for New Relic monitoring.")
    
    return bedrock_client

def monitor_response(
    call: Callable[[], T],
    on_response: Callable[[Dict[str, Any]], None]
) -> T:
    """
    응답을 모니터링하고 New Relic에 데이터 전송
    
    :param call: API 호출 함수
    :param on_response: 응답 처리 콜백
    :return: API 호출 결과
    """
    start_time = time.time()
    
    try:
        response = call()
        try:
            on_response({
                'response': response,
                'response_error': None,
                'duration': int((time.time() - start_time) * 1000)  # 밀리초 단위
            })
        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            
        return response
        
    except Exception as error:
        try:
            on_response({
                'response': None,
                'response_error': error,
                'duration': int((time.time() - start_time) * 1000)  # 밀리초 단위
            })
        except Exception as e:
            logger.error(f"Error processing error response: {str(e)}")
            
        raise

def _extract_request_from_args_kwargs(args, kwargs, original_func):
    """
    함수 인자에서 요청 정보 추출
    """
    request = {}
    
    # 함수 파라미터 목록 가져오기
    signature = inspect.signature(original_func)
    parameters = list(signature.parameters.keys())
    
    # 위치 인자 처리
    for i, arg in enumerate(args):
        if i < len(parameters):
            param_name = parameters[i]
            request[param_name] = arg
    
    # 키워드 인자 처리
    for param_name, value in kwargs.items():
        request[param_name] = value
    
    return request

def _handle_invoke_model_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockCompletionEventDataFactory,
    client: BedrockEventClient
) -> None:
    """
    invoke_model 응답 처리
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    
    # 이벤트 데이터 생성
    event_data = factory.create_event_data({
        'request': request,
        'response_data': response,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 데이터 전송
    client.send(event_data)

def _handle_converse_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockChatCompletionEventDataFactory,
    client: BedrockEventClient
) -> None:
    """
    converse 응답 처리
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    
    # 이벤트 데이터 리스트 생성
    event_data_list = factory.create_event_data_list({
        'request': request,
        'response_data': response,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 데이터 전송
    for event_data in event_data_list:
        client.send(event_data)

def _handle_embedding_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockEmbeddingEventDataFactory,
    client: BedrockEventClient
) -> None:
    """
    embedding 응답 처리
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    
    # 이벤트 데이터 생성
    event_data = factory.create_event_data({
        'request': request,
        'response_data': response,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 데이터 전송
    client.send(event_data) 