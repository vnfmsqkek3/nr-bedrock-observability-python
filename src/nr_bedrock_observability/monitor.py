import time
import logging
import io  # 추가: 바이트 입출력을 위한 io 모듈
from typing import Dict, Any, Optional, Union, Callable, TypeVar, cast, List
import inspect
import json

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
        disable_streaming_events: bool = False
    ):
        self.application_name = application_name
        self.new_relic_api_key = new_relic_api_key
        self.host = host
        self.port = port
        self.track_token_usage = track_token_usage
        self.disable_streaming_events = disable_streaming_events

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
            disable_streaming_events=options.get('disable_streaming_events', False)
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
            
            # 트랜잭션 관리
            try:
                import newrelic.agent
                app = newrelic.agent.application()
                if app:
                    # 트랜잭션 시작
                    with newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/invoke_model"):
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
                else:
                    logger.warning("New Relic 애플리케이션을 찾을 수 없습니다. 트랜잭션 없이 진행합니다.")
            except ImportError:
                logger.debug("New Relic 에이전트를 임포트할 수 없습니다. 트랜잭션 없이 진행합니다.")
            except Exception as e:
                logger.error(f"트랜잭션 생성 중 오류: {str(e)}")
            
            # 트랜잭션 없이 진행 (에러 발생 또는 New Relic 없음)
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
    
    def patch_invoke_model_with_response_stream(
        invoke_model_with_response_stream_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        invoke_model_with_response_stream 함수 패치
        """
        def patched_invoke_model_with_response_stream(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_invoke_model_with_response_stream)
            
            # 스트리밍 이벤트 비활성화 확인
            if monitor_options.disable_streaming_events:
                # 이벤트 없이 원본 함수 호출
                return invoke_model_with_response_stream_func(*args, **kwargs)
            
            # 트랜잭션 관리
            try:
                import newrelic.agent
                app = newrelic.agent.application()
                if app:
                    # 트랜잭션 시작
                    with newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/invoke_model_with_response_stream"):
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
                else:
                    logger.warning("New Relic 애플리케이션을 찾을 수 없습니다. 트랜잭션 없이 진행합니다.")
            except ImportError:
                logger.debug("New Relic 에이전트를 임포트할 수 없습니다. 트랜잭션 없이 진행합니다.")
            except Exception as e:
                logger.error(f"트랜잭션 생성 중 오류: {str(e)}")
            
            # 트랜잭션 없이 진행 (에러 발생 또는 New Relic 없음)
            return monitor_streaming_response(
                lambda: invoke_model_with_response_stream_func(*args, **kwargs),
                lambda response_info: _handle_invoke_model_stream_response(
                    request, 
                    response_info, 
                    completion_event_data_factory, 
                    event_client
                )
            )
            
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
    
    def patch_generate_with_model(
        generate_with_model_func: Callable[..., Any]
    ) -> Callable[..., Any]:
        """
        generate_with_model 함수 패치 (AWS Bedrock용 RAG API)
        """
        def patched_generate_with_model(*args, **kwargs):
            # 요청 정보 추출
            request = _extract_request_from_args_kwargs(args, kwargs, original_generate_with_model)
            
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
            
        return patched_generate_with_model
    
    # Bedrock 클라이언트 패치
    patched_invoke_model = patch_invoke_model(original_invoke_model)
    bedrock_client.invoke_model = patched_invoke_model
    
    # Stream API가 있는 경우 패치
    if original_invoke_model_with_response_stream:
        patched_invoke_model_with_response_stream = patch_invoke_model_with_response_stream(
            original_invoke_model_with_response_stream
        )
        bedrock_client.invoke_model_with_response_stream = patched_invoke_model_with_response_stream
    
    # Converse API가 있는 경우 패치
    if original_converse:
        patched_converse = patch_converse(original_converse)
        bedrock_client.converse = patched_converse
    
    # generate_with_model API가 있는 경우 패치
    if original_generate_with_model:
        patched_generate_with_model = patch_generate_with_model(
            original_generate_with_model
        )
        bedrock_client.generate_with_model = patched_generate_with_model
    
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
            # 응답에 StreamingBody가 있는 경우 복제
            if response and isinstance(response, dict) and 'body' in response and hasattr(response['body'], 'read'):
                logger.debug("StreamingBody 있음, 복제 중...")
                copy_for_monitoring, original_restored = _copy_streaming_body(response['body'])
                
                # 복제본은 모니터링용, 원본은 사용자에게 반환
                monitoring_response = response.copy()
                monitoring_response['body'] = copy_for_monitoring
                
                # 원본 응답 복원
                response['body'] = original_restored
                
                # 모니터링 응답을 사용하여 이벤트 처리
                on_response({
                    'response': monitoring_response,
                    'response_error': None,
                    'duration': int((time.time() - start_time) * 1000)  # 밀리초 단위
                })
            else:
                # 일반 응답 처리
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
            error_obj = create_error_from_exception(error)
            on_response({
                'response': None,
                'response_error': error_obj,
                'duration': int((time.time() - start_time) * 1000)  # 밀리초 단위
            })
        except Exception as e:
            logger.error(f"Error processing error response: {str(e)}")
            
        raise

def monitor_streaming_response(
    call: Callable[[], T],
    on_response: Callable[[Dict[str, Any]], None]
) -> T:
    """
    스트리밍 응답을 모니터링하고 New Relic에 데이터 전송
    
    :param call: API 호출 함수
    :param on_response: 응답 처리 콜백
    :return: 래핑된 스트리밍 응답
    """
    start_time = time.time()
    
    try:
        response = call()
        
        # 응답 메타데이터 처리
        try:
            # 응답 헤더 및 메타데이터만 처리
            stream_metadata = {
                'ResponseMetadata': response.get('ResponseMetadata', {}),
                'contentType': response.get('contentType', ''),
                'is_streaming': True
            }
            
            # 스트리밍 이벤트 시작 시 기록
            on_response({
                'response': stream_metadata,
                'response_error': None,
                'duration': int((time.time() - start_time) * 1000),
                'is_stream_start': True
            })
            
            # 원래 응답을 그대로 반환
            return response
            
        except Exception as e:
            logger.error(f"Error processing streaming response metadata: {str(e)}")
            return response
            
    except Exception as error:
        try:
            error_obj = create_error_from_exception(error)
            on_response({
                'response': None,
                'response_error': error_obj,
                'duration': int((time.time() - start_time) * 1000)
            })
        except Exception as e:
            logger.error(f"Error processing streaming error response: {str(e)}")
            
        raise

def _extract_request_from_args_kwargs(args, kwargs, original_func):
    """
    함수 인자에서 요청 정보 추출
    """
    if not original_func:
        return {}
        
    request = {}
    
    # 함수 파라미터 목록 가져오기
    try:
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
    except Exception as e:
        logger.error(f"Error extracting request parameters: {str(e)}")
    
    return request

def _parse_body(body):
    """
    요청 또는 응답 본문 파싱
    """
    if not body:
        return {}
        
    if isinstance(body, bytes):
        try:
            body_str = body.decode('utf-8')
            return json.loads(body_str)
        except Exception:
            return {'raw': str(body)}
    elif isinstance(body, str):
        try:
            return json.loads(body)
        except Exception:
            return {'raw': body}
    elif isinstance(body, dict):
        return body
    else:
        return {'raw': str(body)}

def _extract_response_data(response):
    """
    응답에서 데이터 추출
    """
    if not response:
        return {}
        
    response_data = {}
    
    if hasattr(response, 'get'):
        # Dict-like response
        response_data = response
    else:
        # API 응답 객체
        for key in ['body', 'response', 'responseBody', 'ResponseMetadata', 'contentType', 'generation']:
            if hasattr(response, key):
                value = getattr(response, key)
                response_data[key] = value

    # body가 있는 경우 파싱
    # 이미 _copy_streaming_body에 의해 복제된 경우 read 가능
    if 'body' in response_data:
        try:
            if hasattr(response_data['body'], 'read'):
                # 이미 복제된 StreamingBody 객체 사용
                body_content = response_data['body'].read()
                if isinstance(body_content, bytes):
                    body_str = body_content.decode('utf-8')
                    response_data['parsed_body'] = json.loads(body_str)
                else:
                    response_data['parsed_body'] = json.loads(body_content)
            elif isinstance(response_data['body'], (bytes, bytearray)):
                body_str = response_data['body'].decode('utf-8')
                response_data['parsed_body'] = json.loads(body_str)
            elif isinstance(response_data['body'], str):
                response_data['parsed_body'] = json.loads(response_data['body'])
        except Exception as e:
            logger.debug(f"Could not parse response body: {str(e)}")
    
    return response_data

def _handle_invoke_model_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockCompletionEventDataFactory,
    client: Any
) -> None:
    """
    invoke_model 응답 처리
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    
    # 요청 본문 파싱
    request_body = request.get('body', {})
    if isinstance(request_body, (bytes, str)):
        request_body = _parse_body(request_body)
    
    # 응답 데이터 추출
    response_data = _extract_response_data(response) if response else {}
    
    # 이벤트 데이터 생성
    event_data = factory.create_event_data({
        'request': {
            **request,
            'parsed_body': request_body
        },
        'response_data': response_data,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 전송
    if event_data:
        # 디버그 로깅을 위한 추가
        logger.info(f"LLM 이벤트 생성: {event_data.get('eventType', 'Unknown')} - New Relic 전송 중")
        
        # 직접 New Relic에 이벤트 기록 시도
        try:
            import newrelic.agent
            nr_app = newrelic.agent.application()
            if nr_app:
                # 이벤트 타입과 속성 추출
                event_type = event_data.get('eventType')
                attributes = event_data.get('attributes', {})
                # New Relic에 직접 이벤트 기록
                newrelic.agent.record_custom_event(event_type, attributes, application=nr_app)
                logger.info(f"New Relic에 직접 이벤트 기록 성공: {event_type}")
            else:
                # 앱이 없으면 일반적인 방식으로 이벤트 전송
                client.send(event_data)
                logger.info("일반 이벤트 클라이언트를 통해 이벤트 전송")
        except ImportError:
            # New Relic이 없으면 일반적인 방식으로 이벤트 전송
            client.send(event_data)
            logger.info("New Relic을 임포트할 수 없음, 일반 클라이언트로 전송")
        except Exception as e:
            logger.error(f"직접 이벤트 기록 중 오류: {str(e)}")
            # 오류 발생 시 일반적인 방식으로 이벤트 전송
            client.send(event_data)

def _handle_invoke_model_stream_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockCompletionEventDataFactory,
    client: Any
) -> None:
    """
    invoke_model_with_response_stream 응답 처리
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    is_stream_start = response_info.get('is_stream_start', False)
    
    # 요청 본문 파싱
    request_body = request.get('body', {})
    if isinstance(request_body, (bytes, str)):
        request_body = _parse_body(request_body)
    
    # 응답 데이터 추출
    response_data = {}
    if response and (hasattr(response, 'get') or isinstance(response, dict)):
        response_data = response if isinstance(response, dict) else dict(response)
    
    # 추가 메타 데이터
    streaming_metadata = {
        'is_streaming': True,
        'stream_event_type': 'start' if is_stream_start else 'chunk'
    }
    
    # 이벤트 데이터 생성
    event_data = factory.create_event_data({
        'request': {
            **request,
            'parsed_body': request_body,
            **streaming_metadata
        },
        'response_data': response_data,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 전송
    if event_data:
        # 디버그 로깅을 위한 추가
        logger.info(f"LLM 스트리밍 이벤트 생성: {event_data.get('eventType', 'Unknown')} - New Relic 전송 중")
        
        # 직접 New Relic에 이벤트 기록 시도
        try:
            import newrelic.agent
            nr_app = newrelic.agent.application()
            if nr_app:
                # 이벤트 타입과 속성 추출
                event_type = event_data.get('eventType')
                attributes = event_data.get('attributes', {})
                # New Relic에 직접 이벤트 기록
                newrelic.agent.record_custom_event(event_type, attributes, application=nr_app)
                logger.info(f"New Relic에 직접 스트리밍 이벤트 기록 성공: {event_type}")
            else:
                # 앱이 없으면 일반적인 방식으로 이벤트 전송
                client.send(event_data)
                logger.info("일반 이벤트 클라이언트를 통해 스트리밍 이벤트 전송")
        except ImportError:
            # New Relic이 없으면 일반적인 방식으로 이벤트 전송
            client.send(event_data)
            logger.info("New Relic을 임포트할 수 없음, 일반 클라이언트로 스트리밍 이벤트 전송")
        except Exception as e:
            logger.error(f"직접 스트리밍 이벤트 기록 중 오류: {str(e)}")
            # 오류 발생 시 일반적인 방식으로 이벤트 전송
            client.send(event_data)

def _handle_converse_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockChatCompletionEventDataFactory,
    client: Any
) -> None:
    """
    converse 응답 처리
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    
    # 요청 본문 추출
    request_messages = request.get('messages', [])
    
    # 응답 데이터 추출
    response_data = _extract_response_data(response) if response else {}
    
    # 이벤트 데이터 생성
    event_data_list = factory.create_event_data_list({
        'request': request,
        'response_data': response_data,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 전송
    if event_data_list:
        for event_data in event_data_list:
            client.send(event_data)

def _handle_embedding_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockEmbeddingEventDataFactory,
    client: Any
) -> None:
    """
    create_embedding 응답 처리
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    
    # 요청 본문 파싱
    request_body = request.get('body', {})
    if isinstance(request_body, (bytes, str)):
        request_body = _parse_body(request_body)
    
    # 응답 데이터 추출
    response_data = _extract_response_data(response) if response else {}
    
    # 이벤트 데이터 생성
    event_data = factory.create_event_data({
        'request': {
            **request,
            'parsed_body': request_body
        },
        'response_data': response_data,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 전송
    if event_data:
        client.send(event_data)

def _handle_generate_with_model_response(
    request: Dict[str, Any],
    response_info: Dict[str, Any],
    factory: BedrockCompletionEventDataFactory,
    client: Any
) -> None:
    """
    generate_with_model 응답 처리 (RAG API)
    """
    response = response_info.get('response')
    response_error = response_info.get('response_error')
    response_time = response_info.get('duration', 0)
    
    # 요청 정보 처리
    processed_request = {
        **request,
        'parsed_body': request.get('inferenceConfig', {}),
        'modelId': request.get('modelId'),
        'api_type': 'rag'
    }
    
    # 응답 데이터 추출 및 처리
    response_data = {}
    if response:
        # generation 필드가 있는 경우 응답 텍스트로 사용
        if hasattr(response, 'generation'):
            response_data['generation'] = response.generation
            
        # citations이 있는 경우 추가
        if hasattr(response, 'citations'):
            response_data['citations'] = response.citations
            
        # 메타데이터 추가
        if hasattr(response, 'ResponseMetadata'):
            response_data['ResponseMetadata'] = response.ResponseMetadata
    
    # 이벤트 데이터 생성
    event_data = factory.create_event_data({
        'request': processed_request,
        'response_data': response_data,
        'response_time': response_time,
        'response_error': response_error
    })
    
    # 이벤트 전송
    if event_data:
        client.send(event_data)

def _copy_streaming_body(body):
    """
    StreamingBody 객체를 복제하여 원본을 보존
    
    :param body: StreamingBody 객체 또는 다른 응답 본문
    :return: (복제본, 원본) 튜플
    """
    if not body or not hasattr(body, 'read'):
        return None, body
        
    try:
        # 원본 내용 읽기
        content = body.read()
        
        # 복제본 생성 (모니터링용)
        copy_for_monitoring = io.BytesIO(content)
        
        # 원본 재생성 (사용자에게 반환)
        original_restored = io.BytesIO(content)
        
        return copy_for_monitoring, original_restored
    except Exception as e:
        logger.error(f"StreamingBody 복제 중 오류: {str(e)}")
        return None, body 