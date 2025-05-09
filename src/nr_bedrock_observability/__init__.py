"""
New Relic AWS Bedrock 모니터링 라이브러리
"""

# 모듈을 직접 import하면 monitor_bedrock 함수 사용 가능
from .monitor import monitor_bedrock, monitor_opensearch_results, link_rag_workflow, MonitorBedrockOptions
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

# 패키지 버전 정보
__version__ = "2.0.0"

# 공개 API
__all__ = [
    'monitor_bedrock',
    'monitor_opensearch_results',
    'link_rag_workflow',
    'ResponseEvaluationCollector',
    'create_response_evaluation_collector',
    'EventType',
    'UserResponseEvaluationAttributes',
    # 범용 평가 수집 도구
    'get_evaluation_collector',
    'reset_evaluation_collector',
    'send_evaluation',
    'send_evaluation_with_newrelic_agent',
    # Streamlit 평가 수집 도구
    'init_response_evaluation_collector',
    'ensure_evaluation_state',
    'update_evaluation_state',
    'create_update_callback',
    'create_evaluation_ui',
    'create_evaluation_debug_ui',
    # 새로 추가한 대시보드 헬퍼 함수들
    'record_role_based_events',
    'record_search_results',
    'record_bedrock_response',
    'extract_claude_response_text',
    'get_sample_nrql_queries',
    'search_knowledge_base'
]

# monitor_bedrock이 이미 .monitor에서 import되어 있으므로
# 래퍼는 필요하지 않음

# def monitor_bedrock_wrapper(*args, **kwargs):
#     """
#     monitor_bedrock 함수의 래퍼
#     """
#     return monitor_bedrock(*args, **kwargs)

# monitor_bedrock = monitor_bedrock_wrapper 