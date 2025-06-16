import time
import logging
import io  # 추가: 바이트 입출력을 위한 io 모듈
import os  # 추가: New Relic 라이센스 키 자동 감지용
from typing import Dict, Any, Optional, Union, Callable, TypeVar, cast, List
import inspect
import json
import uuid

from .events_client import create_event_client, EventClientOptions
from .event_data_factory import (
    BedrockCompletionEventDataFactory,
    BedrockChatCompletionEventDataFactory,
    BedrockEmbeddingEventDataFactory,
    OpenSearchResultEventDataFactory
)
from .event_types import create_error_from_exception

logger = logging.getLogger(__name__)

T = TypeVar('T')  # 제네릭 타입 변수

def _get_newrelic_license_key(provided_key: Optional[str] = None) -> Optional[str]:
    """
    New Relic 라이센스 키를 다양한 소스에서 자동으로 가져옵니다
    
    우선순위:
    1. 제공된 키 (provided_key)
    2. 환경변수 NEW_RELIC_LICENSE_KEY
    3. newrelic.agent에서 설정 가져오기
    4. newrelic.ini 파일 직접 읽기
    
    :param provided_key: 직접 제공된 라이센스 키
    :return: 발견된 라이센스 키 또는 None
    """
    
    # 1. 제공된 키가 있고 유효한 경우
    if provided_key and provided_key.strip() and provided_key != "XXXXXXXXXXXX":
        return provided_key.strip()
    
    # 2. 환경변수에서 시도
    env_key = os.environ.get("NEW_RELIC_LICENSE_KEY")
    if env_key and env_key.strip() and env_key != "XXXXXXXXXXXX":
        logger.info("New Relic 라이센스 키를 환경변수에서 찾았습니다")
        return env_key.strip()
    
    # 3. newrelic.agent에서 설정 가져오기 시도
    try:
        import newrelic.agent
        app = newrelic.agent.application()
        if app and hasattr(app, 'settings'):
            settings = app.settings
            if hasattr(settings, 'license_key') and settings.license_key:
                logger.info("New Relic 라이센스 키를 에이전트 설정에서 찾았습니다")
                return settings.license_key
    except Exception as e:
        logger.debug(f"New Relic 에이전트에서 라이센스 키를 가져올 수 없습니다: {str(e)}")
    
    # 4. newrelic.ini 파일 직접 읽기 시도
    try:
        import configparser
        
        # 가능한 newrelic.ini 파일 위치들
        possible_paths = [
            'newrelic.ini',
            './newrelic.ini',
            '../newrelic.ini',
            '../../newrelic.ini',
            os.path.expanduser('~/newrelic.ini'),
            '/etc/newrelic.ini'
        ]
        
        for config_path in possible_paths:
            if os.path.exists(config_path):
                config = configparser.ConfigParser()
                config.read(config_path)
                
                # [newrelic] 섹션에서 license_key 찾기
                if config.has_section('newrelic') and config.has_option('newrelic', 'license_key'):
                    license_key = config.get('newrelic', 'license_key')
                    if license_key and license_key.strip():
                        logger.info(f"New Relic 라이센스 키를 newrelic.ini 파일에서 찾았습니다: {config_path}")
                        return license_key.strip()
    except Exception as e:
        logger.debug(f"newrelic.ini 파일을 읽는 중 오류 발생: {str(e)}")
    
    # 모든 방법이 실패한 경우
    logger.warning("New Relic 라이센스 키를 찾을 수 없습니다. 다음 중 하나의 방법으로 설정해주세요:")
    logger.warning("1. monitor_bedrock 호출 시 new_relic_api_key 파라미터 제공")
    logger.warning("2. 환경변수 NEW_RELIC_LICENSE_KEY 설정")
    logger.warning("3. newrelic.ini 파일에 license_key 설정")
    logger.warning("4. New Relic 에이전트가 올바르게 초기화되었는지 확인")
    
    return None

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
        feedback_callback: Optional[Callable] = None,
        auto_generate_ids: bool = True,
        auto_extract_context: bool = True,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auto_record_events: bool = True,
        streamlit_integration: bool = False
    ):
        self.application_name = application_name
        self.new_relic_api_key = new_relic_api_key
        self.host = host
        self.port = port
        self.track_token_usage = track_token_usage
        self.disable_streaming_events = disable_streaming_events
        self.collect_feedback = collect_feedback
        self.feedback_callback = feedback_callback
        self.auto_generate_ids = auto_generate_ids
        self.auto_extract_context = auto_extract_context
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.auto_record_events = auto_record_events
        self.streamlit_integration = streamlit_integration

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
        
        # New Relic 라이센스 키 자동 감지
        auto_detected_key = _get_newrelic_license_key(options.get('new_relic_api_key'))
        
        monitor_options = MonitorBedrockOptions(
            application_name=options['application_name'],
            new_relic_api_key=auto_detected_key,
            host=options.get('host'),
            port=options.get('port'),
            track_token_usage=options.get('track_token_usage', True),
            disable_streaming_events=options.get('disable_streaming_events', False),
            collect_feedback=options.get('collect_feedback', False),
            feedback_callback=options.get('feedback_callback'),
            auto_generate_ids=options.get('auto_generate_ids', True),
            auto_extract_context=options.get('auto_extract_context', True),
            conversation_id=options.get('conversation_id'),
            user_id=options.get('user_id'),
            auto_record_events=options.get('auto_record_events', True),
            streamlit_integration=options.get('streamlit_integration', False)
        )
    else:
        # MonitorBedrockOptions 객체인 경우에도 라이센스 키 자동 감지 적용
        auto_detected_key = _get_newrelic_license_key(options.new_relic_api_key)
        options.new_relic_api_key = auto_detected_key
        monitor_options = options
        
    # Streamlit 통합 활성화 시 자동 세션 초기화
    if monitor_options.streamlit_integration:
        if not monitor_options.conversation_id:
            monitor_options.conversation_id = _initialize_streamlit_session()
        else:
            _initialize_streamlit_session(monitor_options.conversation_id)
        
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
    
    opensearch_result_event_data_factory = OpenSearchResultEventDataFactory(
        application_name=monitor_options.application_name
    )
    
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
            
            # 트레이스 ID와 컨텍스트 데이터 추출 (RAG 워크플로우 연결용)
            trace_id = request.pop('_trace_id', None) if isinstance(request, dict) else None
            context_data = request.pop('_context_data', None) if isinstance(request, dict) else None
            
            # 자동 ID 생성 및 컨텍스트 추출 (옵션이 활성화된 경우)
            if monitor_options.auto_generate_ids:
                if not trace_id:
                    trace_id = str(uuid.uuid4())
                    
                if not context_data:
                    context_data = {}
                    
                if 'completion_id' not in context_data:
                    context_data['completion_id'] = str(uuid.uuid4())
                    
                if monitor_options.conversation_id and 'conversation_id' not in context_data:
                    context_data['conversation_id'] = monitor_options.conversation_id
                    
                if monitor_options.user_id and 'user_id' not in context_data:
                    context_data['user_id'] = monitor_options.user_id
                    
            # 자동 컨텍스트 추출 (옵션이 활성화된 경우)
            if monitor_options.auto_extract_context and isinstance(request, dict):
                if not context_data:
                    context_data = {}
                    
                # 요청 본문에서 사용자 쿼리 추출 시도
                if 'user_query' not in context_data:
                    try:
                        request_body = _parse_body(request.get('body', {}))
                        if 'messages' in request_body:
                            # Claude 메시지 형식에서 사용자 쿼리 추출
                            for message in request_body['messages']:
                                if message.get('role') == 'user':
                                    content = message.get('content', [])
                                    if isinstance(content, list) and len(content) > 0:
                                        text_content = content[0].get('text', '') if isinstance(content[0], dict) else str(content[0])
                                        if text_content:
                                            context_data['user_query'] = text_content
                                            break
                                    elif isinstance(content, str):
                                        context_data['user_query'] = content
                                        break
                        elif 'prompt' in request_body:
                            # 일반 프롬프트 형식
                            context_data['user_query'] = request_body['prompt']
                            
                        # 시스템 프롬프트 추출 (있는 경우)
                        if 'system' in request_body and 'system_prompt' not in context_data:
                            context_data['system_prompt'] = request_body['system']
                            
                    except Exception as e:
                        logger.debug(f"사용자 쿼리 자동 추출 중 오류: {str(e)}")
                        
                # Streamlit 통합 시 추가 정보 추출
                if monitor_options.streamlit_integration:
                    try:
                        import streamlit as st
                        if hasattr(st, 'session_state'):
                            # 메시지 카운트 자동 증가
                            if not hasattr(st.session_state, 'message_count'):
                                st.session_state.message_count = 0
                            st.session_state.message_count += 1
                            context_data['message_index'] = st.session_state.message_count
                    except Exception as e:
                        logger.debug(f"Streamlit 통합 중 오류: {str(e)}")
            
            # 자동 이벤트 기록 함수 (응답 후 호출용)
            def auto_record_events(response_info):
                assistant_response = ""
                
                if monitor_options.auto_record_events:
                    try:
                        # 응답 시간 계산
                        response_time_ms = response_info.get('response_time', 0) * 1000
                        
                        # 응답 데이터 추출
                        response_body = response_info.get('response_data', {}).get('parsed_body', {})
                        
                        # 역할별 이벤트 자동 기록
                        _auto_record_role_based_events(
                            context_data=context_data,
                            trace_id=trace_id,
                            application_name=monitor_options.application_name
                        )
                        
                        # Bedrock 응답 자동 기록 및 텍스트 추출
                        assistant_response = _auto_record_bedrock_response(
                            response_body=response_body,
                            response_time_ms=int(response_time_ms),
                            trace_id=trace_id,
                            context_data=context_data,
                            request=request,
                            application_name=monitor_options.application_name
                        )
                        
                    except Exception as e:
                        logger.error(f"자동 이벤트 기록 중 오류: {str(e)}")
                
                # 기존 처리 계속
                _handle_invoke_model_response(
                    request, 
                    response_info, 
                    completion_event_data_factory, 
                    event_client,
                    trace_id,
                    context_data
                )
                
                # 추출된 응답 텍스트를 response_info에 추가
                if assistant_response:
                    response_info['extracted_text'] = assistant_response
            
            # 트랜잭션 관리
            try:
                import newrelic.agent
                app = newrelic.agent.application()
                if app:
                    # 트랜잭션 시작
                    with newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/invoke_model"):
                        # 트레이스 ID 설정 (있는 경우)
                        if trace_id:
                            newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
                            if context_data and 'user_query' in context_data:
                                newrelic.agent.add_custom_span_attribute('user.query', context_data['user_query'])
                        
                        # 응답 모니터링
                        return monitor_response(
                            lambda: invoke_model_func(*args, **kwargs),
                            auto_record_events
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
                auto_record_events
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
            
            # 트레이스 ID와 컨텍스트 데이터 추출 (RAG 워크플로우 연결용)
            trace_id = request.pop('_trace_id', None) if isinstance(request, dict) else None
            context_data = request.pop('_context_data', None) if isinstance(request, dict) else None
            
            # 자동 ID 생성 및 컨텍스트 추출 (옵션이 활성화된 경우)
            if monitor_options.auto_generate_ids:
                if not trace_id:
                    trace_id = str(uuid.uuid4())
                    
                if not context_data:
                    context_data = {}
                    
                if 'completion_id' not in context_data:
                    context_data['completion_id'] = str(uuid.uuid4())
                    
                if monitor_options.conversation_id and 'conversation_id' not in context_data:
                    context_data['conversation_id'] = monitor_options.conversation_id
                    
                if monitor_options.user_id and 'user_id' not in context_data:
                    context_data['user_id'] = monitor_options.user_id
                    
            # 자동 컨텍스트 추출 (옵션이 활성화된 경우)
            if monitor_options.auto_extract_context and isinstance(request, dict):
                if not context_data:
                    context_data = {}
                    
                # 요청에서 사용자 메시지 추출 시도 (converse API 형식)
                if 'user_query' not in context_data:
                    try:
                        if 'messages' in request:
                            # Converse API 메시지 형식에서 사용자 쿼리 추출
                            for message in request['messages']:
                                if message.get('role') == 'user':
                                    content = message.get('content', [])
                                    if isinstance(content, list) and len(content) > 0:
                                        if isinstance(content[0], dict) and 'text' in content[0]:
                                            context_data['user_query'] = content[0]['text']
                                            break
                                    elif isinstance(content, str):
                                        context_data['user_query'] = content
                                        break
                    except Exception as e:
                        logger.debug(f"사용자 쿼리 자동 추출 중 오류 (converse): {str(e)}")
            
            # 트랜잭션 관리
            try:
                import newrelic.agent
                app = newrelic.agent.application()
                if app:
                    # 트랜잭션 시작
                    with newrelic.agent.BackgroundTask(app, name=f"BedrockAPI/converse"):
                        # 트레이스 ID 설정 (있는 경우)
                        if trace_id:
                            newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
                            if context_data and 'user_query' in context_data:
                                newrelic.agent.add_custom_span_attribute('user.query', context_data['user_query'])
                        
                        # 응답 모니터링
                        return monitor_response(
                            lambda: converse_func(*args, **kwargs),
                            lambda response_info: _handle_converse_response(
                                request, 
                                response_info, 
                                chat_completion_event_data_factory, 
                                event_client,
                                trace_id,
                                context_data
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
                lambda: converse_func(*args, **kwargs),
                lambda response_info: _handle_converse_response(
                    request, 
                    response_info, 
                    chat_completion_event_data_factory, 
                    event_client,
                    trace_id,
                    context_data
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
    client: Any,
    trace_id: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None
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
        'response_error': response_error,
        'trace_id': trace_id,
        'context_data': context_data
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
    client: Any,
    trace_id: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None
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
        'response_error': response_error,
        'trace_id': trace_id,
        'context_data': context_data
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

# 새로운 함수: OpenSearch 검색 결과 모니터링
def monitor_opensearch_results(
    opensearch_client: Any,
    query: str,
    results: List[Dict[str, Any]],
    application_name: str,
    index_name: Optional[str] = None,
    response_time: Optional[int] = None,
    trace_id: Optional[str] = None
) -> None:
    """
    OpenSearch 검색 결과 모니터링
    
    :param opensearch_client: OpenSearch 클라이언트
    :param query: 검색 쿼리
    :param results: 검색 결과 목록 (각 결과는 'content'와 'title' 키 포함)
    :param application_name: 애플리케이션 이름
    :param index_name: 검색한 인덱스 이름 (선택 사항)
    :param response_time: 응답 시간 (밀리초)
    :param trace_id: 트레이스 ID (분산 추적용)
    """
    # 결과 존재 확인
    if not results:
        logger.info("검색 결과가 없어 모니터링 건너뜀")
        return
    
    try:
        # 이벤트 팩토리 생성
        factory = OpenSearchResultEventDataFactory(application_name=application_name)
        
        # 이벤트 데이터 생성
        event_data_list = factory.create_event_data_list({
            'query': query,
            'results': results,
            'index_name': index_name,
            'response_time': response_time or 0,
            'trace_id': trace_id,
            'total_results': len(results)
        })
        
        # New Relic에 직접 이벤트 기록
        try:
            import newrelic.agent
            nr_app = newrelic.agent.application()
            if nr_app:
                for event_data in event_data_list:
                    event_type = event_data.get('event_type')
                    attributes = event_data.get('attributes', {})
                    newrelic.agent.record_custom_event(event_type, attributes, application=nr_app)
                logger.info(f"OpenSearch 결과 {len(event_data_list)}개 New Relic에 기록 성공")
            else:
                logger.warning("New Relic 애플리케이션을 찾을 수 없음, OpenSearch 결과 기록 건너뜀")
        except ImportError:
            logger.warning("New Relic을 임포트할 수 없음, OpenSearch 결과 기록 건너뜀")
        except Exception as e:
            logger.error(f"OpenSearch 결과 기록 중 오류: {str(e)}")
    except Exception as e:
        logger.error(f"OpenSearch 결과 모니터링 중 오류: {str(e)}")

# 새로운 함수: RAG 워크플로우 컨텍스트 연결
def link_rag_workflow(
    user_query: str,
    opensearch_results: List[Dict[str, Any]],
    bedrock_client: Any,
    bedrock_request: Dict[str, Any],
    application_name: str,
    trace_id: Optional[str] = None
) -> str:
    """
    RAG 워크플로우의 컨텍스트를 연결 (OpenSearch 결과와 Bedrock 요청)
    
    :param user_query: 사용자 질문
    :param opensearch_results: OpenSearch 검색 결과
    :param bedrock_client: Bedrock 클라이언트
    :param bedrock_request: Bedrock 요청 (invoke_model 또는 converse에 전달할 매개변수)
    :param application_name: 애플리케이션 이름
    :param trace_id: 트레이스 ID (없으면 생성)
    :return: 트레이스 ID
    """
    # 트레이스 ID 생성 또는 사용
    workflow_trace_id = trace_id or str(uuid.uuid4())
    
    try:
        # 트레이스 정보 기록
        import newrelic.agent
        nr_app = newrelic.agent.application()
        if nr_app:
            # RAG 워크플로우 트레이스 설정
            newrelic.agent.add_custom_span_attribute('rag.workflow', 'true')
            newrelic.agent.add_custom_span_attribute('trace.id', workflow_trace_id)
            newrelic.agent.add_custom_span_attribute('user.query', user_query)
            
            # 현재 트랜잭션에 워크플로우 정보 추가
            current_transaction = newrelic.agent.current_transaction()
            if current_transaction:
                current_transaction.add_custom_attribute('workflow.type', 'rag')
                current_transaction.add_custom_attribute('trace.id', workflow_trace_id)
                current_transaction.add_custom_attribute('user.query', user_query)
        
        # OpenSearch 결과 모니터링
        monitor_opensearch_results(
            opensearch_client=None,  # 실제 클라이언트는 필요 없음 (결과만 사용)
            query=user_query,
            results=opensearch_results,
            application_name=application_name,
            trace_id=workflow_trace_id
        )
        
        # 컨텍스트 데이터 구성
        context_data = {
            'opensearch_results': opensearch_results,
            'user_query': user_query
        }
        
        # Bedrock 요청에 트레이스 ID와 컨텍스트 추가
        if 'modelId' in bedrock_request:
            # Bedrock 클라이언트에 요청 설정
            if 'messages' in bedrock_request:
                # converse API 호출 준비
                bedrock_request['_trace_id'] = workflow_trace_id
                bedrock_request['_context_data'] = context_data
            else:
                # invoke_model API 호출 준비
                bedrock_request['_trace_id'] = workflow_trace_id
                bedrock_request['_context_data'] = context_data
    except Exception as e:
        logger.error(f"RAG 워크플로우 연결 중 오류: {str(e)}")
    
    return workflow_trace_id

def _auto_record_role_based_events(
    context_data: Dict[str, Any],
    trace_id: str,
    application_name: str
) -> None:
    """
    역할별 이벤트 자동 기록 (기존 record_role_based_events 대체)
    """
    try:
        import newrelic.agent
        
        # 기본 이벤트 데이터
        event_data = {
            'trace_id': trace_id,
            'applicationName': application_name,
            'timestamp': int(time.time() * 1000)
        }
        
        # 컨텍스트 데이터 추가
        if context_data:
            if 'user_query' in context_data:
                event_data['user_query'] = context_data['user_query']
            if 'system_prompt' in context_data:
                event_data['system_prompt'] = context_data['system_prompt']
            if 'completion_id' in context_data:
                event_data['completion_id'] = context_data['completion_id']
            if 'conversation_id' in context_data:
                event_data['conversation_id'] = context_data['conversation_id']
            if 'message_index' in context_data:
                event_data['message_index'] = context_data['message_index']
        
        # 역할별 이벤트 기록
        newrelic.agent.record_custom_event('LlmUserRole', event_data)
        newrelic.agent.record_custom_event('LlmSystemRole', event_data)
        
    except Exception as e:
        logger.debug(f"역할별 이벤트 자동 기록 중 오류: {str(e)}")

def _auto_record_bedrock_response(
    response_body: Dict[str, Any],
    response_time_ms: int,
    trace_id: str,
    context_data: Dict[str, Any],
    request: Dict[str, Any],
    application_name: str
) -> str:
    """
    Bedrock 응답 자동 기록 (기존 record_bedrock_response 대체)
    응답 텍스트를 추출하여 반환하므로 앱에서 별도 추출 불필요
    """
    assistant_response = ""
    
    try:
        import newrelic.agent
        
        # 응답 텍스트 자동 추출
        try:
            from .dashboard_helpers import extract_claude_response_text
            assistant_response = extract_claude_response_text(response_body)
        except Exception as e:
            logger.debug(f"응답 텍스트 추출 중 오류: {str(e)}")
            # fallback: 기본 추출 로직
            if 'content' in response_body:
                content = response_body['content']
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict) and 'text' in content[0]:
                        assistant_response = content[0]['text']
        
        # 기본 이벤트 데이터
        event_data = {
            'trace_id': trace_id,
            'applicationName': application_name,
            'response_time_ms': response_time_ms,
            'timestamp': int(time.time() * 1000),
            'model_id': request.get('modelId', ''),
            'kb_used_in_query': False  # Knowledge Base 사용 안함
        }
        
        # 컨텍스트 데이터 추가
        if context_data:
            if 'completion_id' in context_data:
                event_data['completion_id'] = context_data['completion_id']
            if 'conversation_id' in context_data:
                event_data['conversation_id'] = context_data['conversation_id']
            if 'message_index' in context_data:
                event_data['message_index'] = context_data['message_index']
        
        # 응답 텍스트 추가
        if assistant_response:
            event_data['assistant_response'] = assistant_response[:1000]  # 길이 제한
        
        # 토큰 정보 추출
        try:
            usage = response_body.get("usage", {})
            total_tokens = usage.get("total_token_count", 0) or (usage.get("input_tokens", 0) + usage.get("output_tokens", 0))
            input_tokens = usage.get("input_token_count", 0) or usage.get("input_tokens", 0)
            output_tokens = usage.get("output_token_count", 0) or usage.get("output_tokens", 0)
            
            if total_tokens > 0:
                event_data['total_tokens'] = total_tokens
            if input_tokens > 0:
                event_data['prompt_tokens'] = input_tokens
            if output_tokens > 0:
                event_data['completion_tokens'] = output_tokens
        except Exception:
            pass
        
        # 모델 파라미터 추출
        try:
            request_body = _parse_body(request.get('body', {}))
            if 'temperature' in request_body:
                event_data['temperature'] = request_body['temperature']
            if 'top_p' in request_body:
                event_data['top_p'] = request_body['top_p']
        except Exception:
            pass
        
        # Bedrock 응답 이벤트 기록
        newrelic.agent.record_custom_event('LlmBedrockResponse', event_data)
        
    except Exception as e:
        logger.debug(f"Bedrock 응답 자동 기록 중 오류: {str(e)}")
    
    return assistant_response

def _initialize_streamlit_session(conversation_id: Optional[str] = None) -> str:
    """
    Streamlit 세션 자동 초기화
    """
    try:
        import streamlit as st
        
        # 대화 ID 초기화
        if not hasattr(st.session_state, 'conversation_id') or not st.session_state.conversation_id:
            st.session_state.conversation_id = conversation_id or str(uuid.uuid4())
        
        # 메시지 카운트 초기화
        if not hasattr(st.session_state, 'message_count'):
            st.session_state.message_count = 0
            
        return st.session_state.conversation_id
        
    except Exception as e:
        logger.debug(f"Streamlit 세션 초기화 중 오류: {str(e)}")
        return conversation_id or str(uuid.uuid4())

def create_streamlit_evaluation_ui(
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    model_id: str = "",
    response_time_ms: Optional[int] = None,
    total_tokens: Optional[int] = None,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    application_name: str = ""
) -> None:
    """
    Streamlit용 자동 평가 UI 생성 (New Relic 이벤트 자동 전송 포함)
    """
    try:
        import streamlit as st
        import newrelic.agent
        
        st.markdown("### 모델 응답 평가")
        
        with st.form(f"evaluation_form_{completion_id}"):
            col1, col2 = st.columns(2)
            
            with col1:
                overall_score = st.slider("전체 만족도", 1, 10, 5)
                relevance_score = st.slider("질문 관련성", 1, 10, 5)
                accuracy_score = st.slider("정확성", 1, 10, 5)
                
            with col2:
                completeness_score = st.slider("완성도", 1, 10, 5)
                coherence_score = st.slider("일관성", 1, 10, 5)
                helpfulness_score = st.slider("유용성", 1, 10, 5)
            
            feedback_comment = st.text_area("추가 피드백 (선택사항)")
            
            submitted = st.form_submit_button("평가 제출")
            
            if submitted:
                # 평가 데이터 구성
                evaluation_data = {
                    "model_id": model_id,
                    "overall_score": overall_score,
                    "relevance_score": relevance_score,
                    "accuracy_score": accuracy_score,
                    "completeness_score": completeness_score,
                    "coherence_score": coherence_score,
                    "helpfulness_score": helpfulness_score,
                    "evaluation_source": "streamlit-auto",
                    "trace_id": trace_id,
                    "completion_id": completion_id,
                    "temperature": temperature,
                    "top_p": top_p,
                    "application_name": application_name,
                    "timestamp": int(time.time() * 1000)
                }
                
                if feedback_comment:
                    evaluation_data["feedback_comment"] = feedback_comment
                
                if response_time_ms:
                    evaluation_data["response_time_ms"] = response_time_ms
                    
                if total_tokens:
                    evaluation_data["total_tokens"] = total_tokens
                    
                if prompt_tokens:
                    evaluation_data["prompt_tokens"] = prompt_tokens
                    
                if completion_tokens:
                    evaluation_data["completion_tokens"] = completion_tokens
                
                # New Relic에 자동 전송
                try:
                    newrelic.agent.record_custom_event('LlmUserResponseEvaluation', evaluation_data)
                    st.success("평가가 성공적으로 제출되었습니다!")
                except Exception as e:
                    st.error(f"평가 제출 중 오류: {str(e)}")
                    
    except Exception as e:
        logger.error(f"평가 UI 생성 중 오류: {str(e)}")

def create_streamlit_nrql_queries(
    application_name: str,
    trace_id: Optional[str] = None,
    completion_id: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> None:
    """
    Streamlit용 NRQL 쿼리 예제 표시
    """
    try:
        import streamlit as st
        
        with st.expander("📊 New Relic 쿼리 예제", expanded=False):
            st.markdown("### 모니터링 데이터 분석을 위한 NRQL 쿼리")
            
            queries = {
                "기본 완성 데이터": f"FROM LlmCompletion SELECT * WHERE appName = '{application_name}' SINCE 1 hour AGO",
                "토큰 사용량 분석": f"FROM LlmCompletion SELECT sum(total_tokens), average(total_tokens) WHERE appName = '{application_name}' SINCE 1 hour AGO",
                "응답 시간 분석": f"FROM LlmCompletion SELECT average(duration), percentile(duration, 95) WHERE appName = '{application_name}' SINCE 1 hour AGO",
                "사용자 평가 데이터": f"FROM LlmUserResponseEvaluation SELECT * WHERE application_name = '{application_name}' SINCE 1 hour AGO",
                "평가 점수 분석": f"FROM LlmUserResponseEvaluation SELECT average(overall_score), average(relevance_score) WHERE application_name = '{application_name}' SINCE 1 hour AGO"
            }
            
            if trace_id:
                queries["현재 트레이스"] = f"FROM LlmCompletion SELECT * WHERE trace_id = '{trace_id}' SINCE 1 hour AGO"
                
            if completion_id:
                queries["현재 완성"] = f"FROM LlmCompletion SELECT * WHERE completion_id = '{completion_id}' SINCE 1 hour AGO"
                
            if conversation_id:
                queries["대화별 분석"] = f"FROM LlmCompletion SELECT count(*) FACET conversation_id WHERE appName = '{application_name}' SINCE 1 hour AGO"
            
            for title, query in queries.items():
                st.markdown(f"**{title}:**")
                st.code(query, language="sql")
                
    except Exception as e:
        logger.error(f"NRQL 쿼리 생성 중 오류: {str(e)}")

def get_streamlit_session_info() -> Dict[str, Any]:
    """
    Streamlit 세션 정보 자동 추출
    """
    try:
        import streamlit as st
        
        session_info = {}
        
        if hasattr(st, 'session_state'):
            # 대화 ID
            if hasattr(st.session_state, 'conversation_id'):
                session_info['conversation_id'] = st.session_state.conversation_id
            else:
                session_info['conversation_id'] = str(uuid.uuid4())
                st.session_state.conversation_id = session_info['conversation_id']
            
            # 메시지 카운트
            if hasattr(st.session_state, 'message_count'):
                st.session_state.message_count += 1
            else:
                st.session_state.message_count = 1
            session_info['message_index'] = st.session_state.message_count
            
        return session_info
        
    except Exception as e:
        logger.debug(f"Streamlit 세션 정보 추출 중 오류: {str(e)}")
        return {
            'conversation_id': str(uuid.uuid4()),
            'message_index': 1
        } 