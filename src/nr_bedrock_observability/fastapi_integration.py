
"""
FastAPI와 NewRelic Bedrock 관측성 통합

이 모듈은 FastAPI 애플리케이션에서 Bedrock 및 RAG 워크플로우를 
자동으로 모니터링하기 위한 미들웨어와 데코레이터를 제공합니다.
"""

import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from functools import wraps

try:
    from fastapi import Request, Response
    from fastapi.middleware.base import BaseHTTPMiddleware
    import newrelic.agent
    from .monitor import monitor_bedrock
    from .event_types import EventType
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # FastAPI가 없는 경우 더미 클래스들 정의
    class BaseHTTPMiddleware:
        def __init__(self, app):
            pass
    
    class Request:
        pass
    
    class Response:
        pass
    
    logging.warning("FastAPI 또는 NewRelic 패키지를 찾을 수 없습니다.")

logger = logging.getLogger(__name__)

class BedrockObservabilityMiddleware(BaseHTTPMiddleware):
    """FastAPI용 Bedrock 관측성 미들웨어"""
    
    def __init__(self, app, application_name: str = "FastAPI-Bedrock-App"):
        super().__init__(app)
        self.application_name = application_name
        self.enabled = FASTAPI_AVAILABLE
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)
            
        # 요청 시작 시간 기록
        start_time = time.time()
        trace_id = str(uuid.uuid4())
        
        # 요청 정보를 NewRelic에 기록
        try:
            request_data = {
                "id": str(uuid.uuid4()),
                "applicationName": self.application_name,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "trace_id": trace_id,
                "timestamp": int(time.time() * 1000),
                "user_agent": request.headers.get("user-agent", ""),
                "client_ip": request.client.host if request.client else ""
            }
            
            # 쿼리 파라미터 기록
            if request.query_params:
                request_data["query_params"] = dict(request.query_params)
            
            newrelic.agent.record_custom_event("FastAPIRequest", request_data)
            
            # 요청 헤더에 trace_id 추가
            request.state.trace_id = trace_id
            
        except Exception as e:
            logger.error(f"요청 이벤트 기록 실패: {e}")
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 시간 계산 및 기록
        try:
            response_time = (time.time() - start_time) * 1000
            
            response_data = {
                "id": str(uuid.uuid4()),
                "applicationName": self.application_name,
                "trace_id": trace_id,
                "status_code": response.status_code,
                "response_time_ms": response_time,
                "timestamp": int(time.time() * 1000)
            }
            
            newrelic.agent.record_custom_event("FastAPIResponse", response_data)
            
            # 응답 헤더에 trace_id 추가
            response.headers["X-Trace-ID"] = trace_id
            
        except Exception as e:
            logger.error(f"응답 이벤트 기록 실패: {e}")
        
        return response

def bedrock_trace(
    operation_name: str = None,
    track_parameters: bool = True,
    track_response: bool = True
):
    """
    Bedrock 작업을 추적하는 데코레이터
    
    Args:
        operation_name: 작업 이름 (기본값: 함수명)
        track_parameters: 파라미터 추적 여부
        track_response: 응답 추적 여부
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not FASTAPI_AVAILABLE:
                return await func(*args, **kwargs)
                
            start_time = time.time()
            operation = operation_name or func.__name__
            trace_id = str(uuid.uuid4())
            
            try:
                # 작업 시작 이벤트 기록
                start_event = {
                    "id": str(uuid.uuid4()),
                    "operation_name": operation,
                    "trace_id": trace_id,
                    "timestamp": int(time.time() * 1000),
                    "function_name": func.__name__
                }
                
                if track_parameters and kwargs:
                    # 민감한 정보 제외하고 파라미터 기록
                    safe_params = {}
                    for key, value in kwargs.items():
                        if key.lower() not in ['password', 'token', 'key', 'secret']:
                            if isinstance(value, (str, int, float, bool)):
                                safe_params[key] = value
                            elif hasattr(value, '__dict__'):
                                safe_params[key] = str(type(value).__name__)
                    start_event["parameters"] = safe_params
                
                newrelic.agent.record_custom_event("BedrockOperationStart", start_event)
                
                # 함수 실행
                result = await func(*args, **kwargs)
                
                # 작업 완료 이벤트 기록
                execution_time = (time.time() - start_time) * 1000
                
                end_event = {
                    "id": str(uuid.uuid4()),
                    "operation_name": operation,
                    "trace_id": trace_id,
                    "execution_time_ms": execution_time,
                    "status": "success",
                    "timestamp": int(time.time() * 1000)
                }
                
                if track_response and result:
                    if isinstance(result, dict):
                        end_event["response_keys"] = list(result.keys())
                        if 'trace_id' not in result:
                            result['trace_id'] = trace_id
                    elif hasattr(result, '__dict__'):
                        end_event["response_type"] = type(result).__name__
                
                newrelic.agent.record_custom_event("BedrockOperationEnd", end_event)
                
                return result
                
            except Exception as e:
                # 오류 이벤트 기록
                execution_time = (time.time() - start_time) * 1000
                
                error_event = {
                    "id": str(uuid.uuid4()),
                    "operation_name": operation,
                    "trace_id": trace_id,
                    "execution_time_ms": execution_time,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:1000],
                    "timestamp": int(time.time() * 1000)
                }
                
                newrelic.agent.record_custom_event("BedrockOperationError", error_event)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not FASTAPI_AVAILABLE:
                return func(*args, **kwargs)
                
            start_time = time.time()
            operation = operation_name or func.__name__
            trace_id = str(uuid.uuid4())
            
            try:
                # 작업 시작 이벤트 기록
                start_event = {
                    "id": str(uuid.uuid4()),
                    "operation_name": operation,
                    "trace_id": trace_id,
                    "timestamp": int(time.time() * 1000),
                    "function_name": func.__name__
                }
                
                if track_parameters and kwargs:
                    # 민감한 정보 제외하고 파라미터 기록
                    safe_params = {}
                    for key, value in kwargs.items():
                        if key.lower() not in ['password', 'token', 'key', 'secret']:
                            if isinstance(value, (str, int, float, bool)):
                                safe_params[key] = value
                            elif hasattr(value, '__dict__'):
                                safe_params[key] = str(type(value).__name__)
                    start_event["parameters"] = safe_params
                
                newrelic.agent.record_custom_event("BedrockOperationStart", start_event)
                
                # 함수 실행
                result = func(*args, **kwargs)
                
                # 작업 완료 이벤트 기록
                execution_time = (time.time() - start_time) * 1000
                
                end_event = {
                    "id": str(uuid.uuid4()),
                    "operation_name": operation,
                    "trace_id": trace_id,
                    "execution_time_ms": execution_time,
                    "status": "success",
                    "timestamp": int(time.time() * 1000)
                }
                
                if track_response and result:
                    if isinstance(result, dict):
                        end_event["response_keys"] = list(result.keys())
                        if 'trace_id' not in result:
                            result['trace_id'] = trace_id
                    elif hasattr(result, '__dict__'):
                        end_event["response_type"] = type(result).__name__
                
                newrelic.agent.record_custom_event("BedrockOperationEnd", end_event)
                
                return result
                
            except Exception as e:
                # 오류 이벤트 기록
                execution_time = (time.time() - start_time) * 1000
                
                error_event = {
                    "id": str(uuid.uuid4()),
                    "operation_name": operation,
                    "trace_id": trace_id,
                    "execution_time_ms": execution_time,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:1000],
                    "timestamp": int(time.time() * 1000)
                }
                
                newrelic.agent.record_custom_event("BedrockOperationError", error_event)
                raise
        
        # 비동기 함수인지 확인
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def record_rag_workflow(
    user_query: str,
    system_prompt: str,
    search_results: List[Dict[str, Any]],
    llm_response: str,
    index_name: str,
    model_id: str,
    trace_id: str = None,
    user_id: str = None,
    temperature: float = None,
    top_k: int = None,
    response_time_ms: float = None
):
    """
    완전한 RAG 워크플로우를 NewRelic에 기록
    
    Args:
        user_query: 사용자 질문
        system_prompt: 시스템 프롬프트
        search_results: 검색 결과 목록
        llm_response: LLM 응답
        index_name: OpenSearch 인덱스 이름
        model_id: 사용된 모델 ID
        trace_id: 트레이스 ID
        user_id: 사용자 ID
        temperature: 모델 temperature 설정
        top_k: 검색 결과 개수
        response_time_ms: 전체 응답 시간
    """
    if not FASTAPI_AVAILABLE:
        return False
        
    try:
        if not trace_id:
            trace_id = str(uuid.uuid4())
        
        timestamp = int(time.time() * 1000)
        
        # 1. 사용자 프롬프트 이벤트
        user_event = {
            "id": str(uuid.uuid4()),
            "applicationName": "FastAPI-RAG",
            "role": "user",
            "content": user_query[:4095],
            "trace_id": trace_id,
            "user_id": user_id or "anonymous",
            "timestamp": timestamp
        }
        newrelic.agent.record_custom_event(EventType.LLM_USER_PROMPT, user_event)
        
        # 2. 시스템 프롬프트 이벤트
        system_event = {
            "id": str(uuid.uuid4()),
            "applicationName": "FastAPI-RAG",
            "role": "system",
            "content": system_prompt[:4095],
            "trace_id": trace_id,
            "timestamp": timestamp
        }
        newrelic.agent.record_custom_event(EventType.LLM_SYSTEM_PROMPT, system_event)
        
        # 3. 검색 결과 이벤트들
        for i, result in enumerate(search_results):
            search_event = {
                "id": str(uuid.uuid4()),
                "applicationName": "FastAPI-RAG",
                "query": user_query[:1000],
                "index_name": index_name,
                "result_content": str(result.get('content', ''))[:4095],
                "result_title": str(result.get('title', ''))[:255],
                "score": float(result.get('score', 0.0)),
                "rank": i + 1,
                "trace_id": trace_id,
                "timestamp": timestamp,
                "total_results": len(search_results)
            }
            newrelic.agent.record_custom_event(EventType.LLM_OPENSEARCH_RESULT, search_event)
        
        # 4. RAG 컨텍스트 이벤트
        context_text = "\n\n".join([str(r.get('content', '')) for r in search_results])
        context_event = {
            "id": str(uuid.uuid4()),
            "applicationName": "FastAPI-RAG",
            "content": context_text[:4095],
            "source_count": len(search_results),
            "trace_id": trace_id,
            "timestamp": timestamp
        }
        newrelic.agent.record_custom_event(EventType.LLM_RAG_CONTEXT, context_event)
        
        # 5. LLM 응답 이벤트
        response_event = {
            "id": str(uuid.uuid4()),
            "applicationName": "FastAPI-RAG",
            "response": llm_response[:4095],
            "model_id": model_id,
            "trace_id": trace_id,
            "timestamp": timestamp,
            "response_length": len(llm_response)
        }
        
        if response_time_ms:
            response_event["response_time_ms"] = response_time_ms
        if temperature is not None:
            response_event["temperature"] = temperature
        if top_k:
            response_event["top_k"] = top_k
            
        newrelic.agent.record_custom_event("LlmResponse", response_event)
        
        return True
        
    except Exception as e:
        logger.error(f"RAG 워크플로우 기록 실패: {e}")
        return False

def get_trace_id_from_request(request: Request) -> Optional[str]:
    """요청에서 trace_id를 추출"""
    try:
        return getattr(request.state, 'trace_id', None)
    except:
        return None

def add_trace_id_to_response(response_data: dict, trace_id: str) -> dict:
    """응답 데이터에 trace_id 추가"""
    if isinstance(response_data, dict) and trace_id:
        response_data['trace_id'] = trace_id
    return response_data 