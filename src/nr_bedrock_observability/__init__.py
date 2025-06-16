"""
New Relic AWS Bedrock 모니터링 라이브러리
"""

# 모듈을 직접 import하면 monitor_bedrock 함수 사용 가능
from .monitor import (
    monitor_bedrock,
    monitor_response,
    monitor_streaming_response,
    monitor_opensearch_results,
    link_rag_workflow,
    create_streamlit_evaluation_ui,
    create_streamlit_nrql_queries,
    get_streamlit_session_info,
    MonitorBedrockOptions
)
from .response_evaluation import (
    ResponseEvaluationCollector, 
    create_response_evaluation_collector
)
from .event_types import EventType, UserResponseEvaluationAttributes

# 범용 평가 수집 도구 import
from .generic_response_evaluation import (
    get_evaluation_collector,
    reset_evaluation_collector,
    send_evaluation,
    send_evaluation_with_newrelic_agent
)

# Streamlit 평가 수집 도구 import
from .streamlit_response_evaluation import (
    init_response_evaluation_collector,
    ensure_evaluation_state,
    update_evaluation_state,
    create_update_callback,
    create_evaluation_ui,
    create_evaluation_debug_ui
)

# 새로 추가한 대시보드 헬퍼 함수들을 노출
from .bedrock_dashboard_helpers import (
    record_role_based_events,
    record_search_results,
    record_bedrock_response,
    extract_claude_response_text,
    get_sample_nrql_queries,
    search_knowledge_base
)

# FastAPI 통합 기능들을 노출
from .fastapi_integration import (
    BedrockObservabilityMiddleware,
    bedrock_trace,
    record_rag_workflow,
    get_trace_id_from_request,
    add_trace_id_to_response
)

# 패키지 버전 정보
__version__ = "2.2.0"

# 자동 패치 기능 - boto3.client('bedrock-runtime') 호출 시 자동으로 모니터링 활성화
_auto_patch_enabled = False
_default_app_name = "auto-bedrock-app"

def enable_auto_patch(application_name: str = None, **kwargs):
    """
    boto3.client('bedrock-runtime') 자동 패치 활성화
    이 함수 호출 후 모든 bedrock-runtime 클라이언트가 자동으로 모니터링됨
    """
    global _auto_patch_enabled, _default_app_name
    
    if application_name:
        _default_app_name = application_name
    
    _auto_patch_enabled = True
    
    # boto3 패치
    try:
        import boto3
        
        # 원본 함수 저장
        if not hasattr(boto3, '_original_client'):
            boto3._original_client = boto3.client
            
        def auto_patched_client(service_name, *args, **client_kwargs):
            client = boto3._original_client(service_name, *args, **client_kwargs)
            
            # bedrock-runtime 클라이언트인 경우 자동으로 모니터링 활성화
            if service_name == 'bedrock-runtime' and _auto_patch_enabled:
                from .monitor import monitor_bedrock
                
                monitor_options = {
                    'application_name': _default_app_name,
                    'streamlit_integration': True,
                    'auto_generate_ids': True,
                    'auto_extract_context': True,
                    'auto_record_events': True,
                    **kwargs  # 추가 옵션
                }
                
                return monitor_bedrock(client, monitor_options)
            
            return client
        
        # boto3.client 패치
        boto3.client = auto_patched_client
        
    except ImportError:
        pass  # boto3가 없는 환경에서는 패치하지 않음

def disable_auto_patch():
    """자동 패치 비활성화"""
    global _auto_patch_enabled
    _auto_patch_enabled = False
    
    try:
        import boto3
        if hasattr(boto3, '_original_client'):
            boto3.client = boto3._original_client
    except ImportError:
        pass

# 공개 API
__all__ = [
    # 버전 정보
    "__version__",
    
    # 자동 패치 함수
    "enable_auto_patch",
    "disable_auto_patch",
    
    # 모니터링 함수
    "monitor_bedrock",
    "monitor_response", 
    "monitor_streaming_response",
    "monitor_opensearch_results",
    "link_rag_workflow",
    "create_streamlit_evaluation_ui",
    "create_streamlit_nrql_queries", 
    "get_streamlit_session_info",
    "MonitorBedrockOptions",
    
    # 응답 평가 수집
    "ResponseEvaluationCollector",
    "init_response_evaluation_collector",
    "ensure_evaluation_state",
    "update_evaluation_state", 
    "create_update_callback",
    "create_evaluation_ui",
    "create_evaluation_debug_ui",
    "send_evaluation_with_newrelic_agent",
    "get_evaluation_collector",
    "reset_evaluation_collector",
    
    # 대시보드 헬퍼 함수
    "record_role_based_events",
    "record_search_results", 
    "record_bedrock_response",
    "extract_claude_response_text",
    "get_sample_nrql_queries",
    "search_knowledge_base",
    
    # 이벤트 타입
    "EventType",
    
    # FastAPI 통합 기능들
    "BedrockObservabilityMiddleware",
    "bedrock_trace",
    "record_rag_workflow",
    "get_trace_id_from_request",
    "add_trace_id_to_response"
]

# monitor_bedrock이 이미 .monitor에서 import되어 있으므로
# 래퍼는 필요하지 않음

# def monitor_bedrock_wrapper(*args, **kwargs):
#     """
#     monitor_bedrock 함수의 래퍼
#     """
#     return monitor_bedrock(*args, **kwargs)

# monitor_bedrock = monitor_bedrock_wrapper 