import time
import logging
from typing import Dict, Any, Optional, Union, Callable, TypeVar, cast, List
import inspect
import json
import newrelic.agent

from .events_client import create_event_client, EventClientOptions
from .event_data_factory import (
    BedrockCompletionEventDataFactory,
    BedrockChatCompletionEventDataFactory,
    BedrockEmbeddingEventDataFactory
)
from .event_types import create_error_from_exception

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
        port: Optional[int] = None,
        track_token_usage: bool = True,
        disable_streaming_events: bool = False,
        collect_feedback: bool = False,
        feedback_callback: Optional[Callable[[str, str], Dict[str, Any]]] = None
    ):
        self.application_name = application_name
        self.new_relic_api_key = new_relic_api_key
        self.host = host
        self.port = port
        self.track_token_usage = track_token_usage
        self.disable_streaming_events = disable_streaming_events
        self.collect_feedback = collect_feedback
        self.feedback_callback = feedback_callback

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
            port=options.get('port'),
            track_token_usage=options.get('track_token_usage', True),
            disable_streaming_events=options.get('disable_streaming_events', False),
            collect_feedback=options.get('collect_feedback', False),
            feedback_callback=options.get('feedback_callback')
        )
    else:
        monitor_options = options
        
    # Bedrock 설정 추출
    bedrock_configuration = None
    if hasattr(bedrock_client, '_client_config'):
        bedrock_configuration = bedrock_client._client_config.__dict__
        
    # 이벤트 클라이언트 생성
    event_client = create_event_client({
        'application_name': monitor_options.application_name,
        'new_relic_api_key': monitor_options.new_relic_api_key,
        'host': monitor_options.host,
        'port': monitor_options.port
    })
    
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
    original_invoke_model_with_response_stream = getattr(bedrock_client, 'invoke_model_with_response_stream', None)
    original_converse = getattr(bedrock_client, 'converse', None)
    original_generate_with_model = getattr(bedrock_client, 'generate_with_model', None)
    
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
            
            # New Relic 애플리케이션 객체 가져오기
            app = None
            if hasattr(bedrock_client, '_monitor_options') and hasattr(bedrock_client._monitor_options, 'application'):
                app = bedrock_client._monitor_options.application
            
            # 트랜잭션 관리
            transaction = None
            if app:
                try:
                    # 현재 활성 트랜잭션이 있는지 확인
                    current_transaction = newrelic.agent.current_transaction()
                    if not current_transaction:
                        # 활성 트랜잭션이 없는 경우에만 새 트랜잭션 생성
                        transaction = newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/invoke_model")
                        transaction.__enter__()
                except Exception as e:
                    logger.warning(f"New Relic transaction initialization failed: {str(e)}")
            
            try:
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
            finally:
                # 트랜잭션 종료
                if transaction:
                    try:
                        transaction.__exit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"New Relic transaction cleanup failed: {str(e)}")
            
        return patched_invoke_model
    
    def patch_invoke_model_with_response_stream(
        invoke_model_with_response_stream_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        invoke_model_with_response_stream 함수 패치
        """
        def patched_invoke_model_with_response_stream(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_invoke_model_with_response_stream)
            
            # New Relic 애플리케이션 객체 가져오기
            app = None
            if hasattr(bedrock_client, '_monitor_options') and hasattr(bedrock_client._monitor_options, 'application'):
                app = bedrock_client._monitor_options.application
            
            # 트랜잭션 관리
            transaction = None
            if app:
                try:
                    # 현재 활성 트랜잭션이 있는지 확인
                    current_transaction = newrelic.agent.current_transaction()
                    if not current_transaction:
                        # 활성 트랜잭션이 없는 경우에만 새 트랜잭션 생성
                        transaction = newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/invoke_model_with_response_stream")
                        transaction.__enter__()
                except Exception as e:
                    logger.warning(f"New Relic transaction initialization failed: {str(e)}")
            
            try:
                # 스트리밍 이벤트 비활성화 확인
                if monitor_options.disable_streaming_events:
                    # 이벤트 없이 원본 함수 호출
                    return invoke_model_with_response_stream_func(*args, **kwargs)
                
                # 응답 모니터링
                return monitor_streaming_response(
                    lambda: invoke_model_with_response_stream_func(*args, **kwargs),
                    lambda response_info: _handle_invoke_model_stream_response(
                        request, 
                        response_info, 
                        completion_event_data_factory, 
                        event_client
                    )
                )
            finally:
                # 트랜잭션 종료
                if transaction:
                    try:
                        transaction.__exit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"New Relic transaction cleanup failed: {str(e)}")
            
        return patched_invoke_model_with_response_stream
    
    def patch_converse(
        converse_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        converse 함수 패치
        """
        def patched_converse(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_converse)
            
            # New Relic 애플리케이션 객체 가져오기
            app = None
            if hasattr(bedrock_client, '_monitor_options') and hasattr(bedrock_client._monitor_options, 'application'):
                app = bedrock_client._monitor_options.application
            
            # 트랜잭션 관리
            transaction = None
            if app:
                try:
                    # 현재 활성 트랜잭션이 있는지 확인
                    current_transaction = newrelic.agent.current_transaction()
                    if not current_transaction:
                        # 활성 트랜잭션이 없는 경우에만 새 트랜잭션 생성
                        transaction = newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/converse")
                        transaction.__enter__()
                except Exception as e:
                    logger.warning(f"New Relic transaction initialization failed: {str(e)}")
            
            try:
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
            finally:
                # 트랜잭션 종료
                if transaction:
                    try:
                        transaction.__exit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"New Relic transaction cleanup failed: {str(e)}")
            
        return patched_converse
    
    def patch_generate_with_model(
        generate_with_model_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        generate_with_model 함수 패치 (AWS Bedrock용 RAG API)
        """
        def patched_generate_with_model(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_generate_with_model)
            
            # New Relic 애플리케이션 객체 가져오기
            app = None
            if hasattr(bedrock_client, '_monitor_options') and hasattr(bedrock_client._monitor_options, 'application'):
                app = bedrock_client._monitor_options.application
            
            # 트랜잭션 관리
            transaction = None
            if app:
                try:
                    # 현재 활성 트랜잭션이 있는지 확인
                    current_transaction = newrelic.agent.current_transaction()
                    if not current_transaction:
                        # 활성 트랜잭션이 없는 경우에만 새 트랜잭션 생성
                        transaction = newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/generate_with_model")
                        transaction.__enter__()
                except Exception as e:
                    logger.warning(f"New Relic transaction initialization failed: {str(e)}")
            
            try:
                # 응답 모니터링
                return monitor_response(
                    lambda: generate_with_model_func(*args, **kwargs),
                    lambda response_info: _handle_generate_with_model_response(
                        request, 
                        response_info, 
                        completion_event_data_factory, 
                        event_client
                    )
                )
            finally:
                # 트랜잭션 종료
                if transaction:
                    try:
                        transaction.__exit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"New Relic transaction cleanup failed: {str(e)}")
            
        return patched_generate_with_model
    
    def patch_create_embedding(
        create_embedding_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        create_embedding 함수 패치
        """
        def patched_create_embedding(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_create_embedding)
            
            # New Relic 애플리케이션 객체 가져오기
            app = None
            if hasattr(bedrock_client, '_monitor_options') and hasattr(bedrock_client._monitor_options, 'application'):
                app = bedrock_client._monitor_options.application
            
            # 트랜잭션 관리
            transaction = None
            if app:
                try:
                    # 현재 활성 트랜잭션이 있는지 확인
                    current_transaction = newrelic.agent.current_transaction()
                    if not current_transaction:
                        # 활성 트랜잭션이 없는 경우에만 새 트랜잭션 생성
                        transaction = newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/create_embedding")
                        transaction.__enter__()
                except Exception as e:
                    logger.warning(f"New Relic transaction initialization failed: {str(e)}")
            
            try:
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
            finally:
                # 트랜잭션 종료
                if transaction:
                    try:
                        transaction.__exit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"New Relic transaction cleanup failed: {str(e)}")
            
        return patched_create_embedding

def monitor_response(
    call: Callable[[], T],
    on_response: Callable[[Dict[str, Any]], None]
) -> T:
    """
    응답 모니터링
    """
    start_time = time.time()
    error = None
    response = None
    
    try:
        response = call()
        return response
    except Exception as e:
        error = e
        raise
    finally:
        try:
            # 응답 정보 수집
            response_info = {
                'duration': time.time() - start_time,
                'error': error,
                'response': response
            }
            
            # 응답 처리
            on_response(response_info)
        except Exception as e:
            logger.error(f"Response monitoring error: {str(e)}")

def monitor_streaming_response(
    call: Callable[[], T],
    on_response: Callable[[Dict[str, Any]], None]
) -> T:
    """
    스트리밍 응답 모니터링
    """
    start_time = time.time()
    error = None
    response = None
    
    try:
        response = call()
        return response
    except Exception as e:
        error = e
        raise
    finally:
        try:
            # 응답 정보 수집
            response_info = {
                'duration': time.time() - start_time,
                'error': error,
                'response': response
            }
            
            # 응답 처리
            on_response(response_info)
        except Exception as e:
            logger.error(f"Streaming response monitoring error: {str(e)}")

def _extract_request_from_args_kwargs(args, kwargs, original_func):
    """
    요청 정보 추출
    """
    # 함수 시그니처 분석
    sig = inspect.signature(original_func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()
    
    # 요청 정보 추출
    request = {}
    
    # modelId 추출
    if 'modelId' in bound_args.arguments:
        request['model_id'] = bound_args.arguments['modelId']
    
    # body 추출
    if 'body' in bound_args.arguments:
        body = bound_args.arguments['body']
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass
        request['body'] = body
    
    return request

def _parse_body(body):
    """
    요청 본문 파싱
    """
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body
    return body

def _extract_response_data(response):
    """
    응답 데이터 추출
    """
    if not response:
        return None
        
    try:
        if hasattr(response, 'get'):
            return response.get('body', None)
        return response
    except Exception as e:
        logger.error(f"Response data extraction error: {str(e)}")
        return None

def _handle_invoke_model_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockCompletionEventDataFactory,
    client: Any
) -> None:
    """
    invoke_model 응답 처리
    """
    try:
        # 응답 데이터 추출
        response_data = _extract_response_data(response_info['response'])
        
        # 이벤트 데이터 생성
        event_data = factory.create_event_data(
            request=request,
            response=response_data,
            duration=response_info['duration'],
            error=response_info['error']
        )
        
        # 이벤트 전송
        client.send_event(event_data)
    except Exception as e:
        logger.error(f"Invoke model response handling error: {str(e)}")

def _handle_invoke_model_stream_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockCompletionEventDataFactory,
    client: Any
) -> None:
    """
    invoke_model_with_response_stream 응답 처리
    """
    try:
        # 응답 데이터 추출
        response_data = _extract_response_data(response_info['response'])
        
        # 이벤트 데이터 생성
        event_data = factory.create_event_data(
            request=request,
            response=response_data,
            duration=response_info['duration'],
            error=response_info['error']
        )
        
        # 이벤트 전송
        client.send_event(event_data)
    except Exception as e:
        logger.error(f"Invoke model stream response handling error: {str(e)}")

def _handle_converse_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockChatCompletionEventDataFactory,
    client: Any
) -> None:
    """
    converse 응답 처리
    """
    try:
        # 응답 데이터 추출
        response_data = _extract_response_data(response_info['response'])
        
        # 이벤트 데이터 생성
        event_data = factory.create_event_data(
            request=request,
            response=response_data,
            duration=response_info['duration'],
            error=response_info['error']
        )
        
        # 이벤트 전송
        client.send_event(event_data)
    except Exception as e:
        logger.error(f"Converse response handling error: {str(e)}")

def _handle_embedding_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockEmbeddingEventDataFactory,
    client: Any
) -> None:
    """
    create_embedding 응답 처리
    """
    try:
        # 응답 데이터 추출
        response_data = _extract_response_data(response_info['response'])
        
        # 이벤트 데이터 생성
        event_data = factory.create_event_data(
            request=request,
            response=response_data,
            duration=response_info['duration'],
            error=response_info['error']
        )
        
        # 이벤트 전송
        client.send_event(event_data)
    except Exception as e:
        logger.error(f"Embedding response handling error: {str(e)}")

def _handle_generate_with_model_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockCompletionEventDataFactory,
    client: Any
) -> None:
    """
    generate_with_model 응답 처리
    """
    try:
        # 응답 데이터 추출
        response_data = _extract_response_data(response_info['response'])
        
        # 이벤트 데이터 생성
        event_data = factory.create_event_data(
            request=request,
            response=response_data,
            duration=response_info['duration'],
            error=response_info['error']
        )
        
        # 이벤트 전송
        client.send_event(event_data)
    except Exception as e:
        logger.error(f"Generate with model response handling error: {str(e)}") 