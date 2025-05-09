"""
Bedrock 대시보드 및 모니터링 헬퍼 함수

이 모듈은 Streamlit 기반 Bedrock 모니터링 앱을 위한 도우미 함수들을 제공합니다.
"""

import streamlit as st
import boto3
import json
import uuid
import time
import newrelic.agent
from .event_types import EventType

# 이벤트 타입 상수 정의
EVENT_TYPE_SYSTEM_PROMPT = EventType.LLM_SYSTEM_PROMPT
EVENT_TYPE_USER_PROMPT = EventType.LLM_USER_PROMPT
EVENT_TYPE_OPENSEARCH_RESULT = EventType.LLM_OPENSEARCH_RESULT
EVENT_TYPE_RAG_CONTEXT = EventType.LLM_RAG_CONTEXT
EVENT_TYPE_LLM_RESPONSE = "LlmResponse"  # Bedrock 응답용 이벤트 타입 추가

def record_role_based_events(
    user_query, 
    system_prompt, 
    search_results, 
    context_text, 
    trace_id, 
    completion_id=None, 
    application_name="Bedrock-Monitoring-App",
    conversation_id=None,
    message_index=0
):
    """
    사용자 질문, 시스템 프롬프트, 검색 결과를 개별 이벤트로 New Relic에 기록
    
    :param user_query: 사용자 질문
    :param system_prompt: 시스템 프롬프트
    :param search_results: 검색 결과 목록
    :param context_text: 검색 결과로 구성된 컨텍스트 텍스트
    :param trace_id: 트레이스 ID
    :param completion_id: 완성 ID (없으면 trace_id 사용)
    :param application_name: 애플리케이션 이름
    :param conversation_id: 대화 ID
    :param message_index: 메시지 인덱스
    :return: 기록 성공 여부
    """
    try:
        # 트랜잭션 및 애플리케이션 확인
        nr_app = newrelic.agent.application()
        
        if not nr_app:
            st.warning("New Relic 애플리케이션을 찾을 수 없습니다. 역할별 이벤트를 기록할 수 없습니다.")
            return False
        
        completion_id = completion_id or trace_id
        conversation_id = conversation_id or str(uuid.uuid4())
        timestamp = int(time.time() * 1000)
        
        # 별도의 트랜잭션 생성하여 이벤트 기록
        with newrelic.agent.BackgroundTask(nr_app, name=f"EventRecording/RoleBasedEvents"):
            # 1. 시스템 프롬프트 이벤트 기록
            system_prompt_event = {
                "id": str(uuid.uuid4()),
                "applicationName": application_name,
                "role": "system",
                "content": system_prompt,
                "trace_id": trace_id,
                "completion_id": completion_id,
                "conversation_id": conversation_id,
                "message_index": message_index,
                "timestamp": timestamp
            }
            newrelic.agent.record_custom_event(EVENT_TYPE_SYSTEM_PROMPT, system_prompt_event, application=nr_app)
            
            # 2. 사용자 프롬프트 이벤트 기록
            user_prompt_event = {
                "id": str(uuid.uuid4()),
                "applicationName": application_name,
                "role": "user",
                "content": user_query,
                "trace_id": trace_id,
                "completion_id": completion_id,
                "conversation_id": conversation_id,
                "message_index": message_index,
                "timestamp": timestamp
            }
            newrelic.agent.record_custom_event(EVENT_TYPE_USER_PROMPT, user_prompt_event, application=nr_app)
            
            # 3. RAG 컨텍스트 이벤트 기록
            rag_context_event = {
                "id": str(uuid.uuid4()),
                "applicationName": application_name,
                "content": context_text,
                "trace_id": trace_id,
                "completion_id": completion_id,
                "conversation_id": conversation_id,
                "message_index": message_index,
                "timestamp": timestamp,
                "total_results": len(search_results)
            }
            newrelic.agent.record_custom_event(EVENT_TYPE_RAG_CONTEXT, rag_context_event, application=nr_app)
        
        return True
        
    except Exception as e:
        st.error(f"역할별 이벤트 기록 중 오류: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False

def record_search_results(
    user_query, 
    search_results, 
    search_response_time,
    trace_id, 
    application_name="Bedrock-Monitoring-App",
    kb_id=None,
    kb_name=None,
    conversation_id=None,
    message_index=0
):
    """
    검색 결과를 New Relic에 이벤트로 기록
    
    :param user_query: 사용자 질문
    :param search_results: 검색 결과 목록
    :param search_response_time: 검색 응답 시간 (ms)
    :param trace_id: 트레이스 ID
    :param application_name: 애플리케이션 이름
    :param kb_id: 지식 기반 ID
    :param kb_name: 지식 기반 이름
    :param conversation_id: 대화 ID
    :param message_index: 메시지 인덱스
    :return: 기록 성공 여부
    """
    try:
        nr_app = newrelic.agent.application()
        if not nr_app:
            st.warning("New Relic 애플리케이션을 찾을 수 없어 검색 결과를 기록하지 않았습니다.")
            return False
            
        timestamp = int(time.time() * 1000)
        
        # 각 검색 결과에 대해 이벤트 기록
        for i, result in enumerate(search_results):
            event_data = {
                "id": str(uuid.uuid4()),
                "applicationName": application_name,
                "query": user_query,
                "index_name": kb_name,
                "result_content": result.get('content', '')[:4095],  # 길이 제한
                "result_title": result.get('title', '')[:255],
                "score": result.get('score', 0.0),
                "sequence": i,
                "trace_id": trace_id,
                "timestamp": timestamp,
                "total_results": len(search_results),
                "response_time": search_response_time,
                "kb_id": kb_id,
                "kb_name": kb_name,
                "kb_data_source_count": len(search_results),
                "kb_used_in_query": True,
                "conversation_id": conversation_id,
                "message_index": message_index
            }
            
            # 이벤트 기록
            with newrelic.agent.BackgroundTask(nr_app, name=f"EventRecording/OpenSearchResult/{i}"):
                newrelic.agent.record_custom_event(EVENT_TYPE_OPENSEARCH_RESULT, event_data, application=nr_app)
        
        return True
    except Exception as e:
        st.warning(f"OpenSearch 결과 모니터링 중 오류: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False

def record_bedrock_response(
    assistant_response,
    response_body,
    trace_id,
    completion_id,
    application_name="Bedrock-Monitoring-App",
    model_id=None,
    kb_id=None,
    kb_name=None,
    conversation_id=None,
    message_index=0,
    response_time_ms=0,
    temperature=None,
    top_p=None
):
    """
    Bedrock API 응답 데이터를 New Relic에 기록
    
    :param assistant_response: 모델 생성 응답 텍스트
    :param response_body: Bedrock API 응답 본문
    :param trace_id: 트레이스 ID
    :param completion_id: 완성 ID
    :param application_name: 애플리케이션 이름
    :param model_id: 모델 ID
    :param kb_id: 지식 기반 ID
    :param kb_name: 지식 기반 이름
    :param conversation_id: 대화 ID
    :param message_index: 메시지 인덱스
    :param response_time_ms: 응답 시간 (ms)
    :param temperature: 모델 temperature 값
    :param top_p: 모델 top_p 값
    :return: 기록 성공 여부
    """
    try:
        nr_app = newrelic.agent.application()
        if not nr_app:
            st.warning("New Relic 애플리케이션을 찾을 수 없어 Bedrock 응답을 기록하지 않았습니다.")
            return False
            
        # 토큰 사용량 추출
        total_tokens = response_body.get("usage", {}).get("total_token_count", 0)
        input_tokens = response_body.get("usage", {}).get("input_token_count", 0)
        output_tokens = response_body.get("usage", {}).get("output_token_count", 0)

        # Claude 3.5에서 사용하는 토큰 필드 추가 확인
        if total_tokens == 0 and input_tokens == 0 and output_tokens == 0:
            # Claude 3.5 토큰 형식 - usage 딕셔너리 내부 확인
            usage = response_body.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens
            
        timestamp = int(time.time() * 1000)
        
        # LLM 응답 이벤트 생성
        llm_response_event = {
            "id": str(uuid.uuid4()),
            "applicationName": application_name,
            "role": "assistant",
            "content": assistant_response,
            "trace_id": trace_id,
            "completion_id": completion_id,
            "conversation_id": conversation_id,
            "message_index": message_index,
            "timestamp": timestamp,
            "token_count": output_tokens,
            "total_tokens": total_tokens,
            "prompt_tokens": input_tokens,
            "model_id": model_id,
            "kb_id": kb_id,
            "kb_name": kb_name,
            "kb_used_in_query": True if kb_id else False,
            "response_time_ms": response_time_ms
        }
        
        # temperature와 top_p 값이 있으면 이벤트에 추가
        if temperature is not None:
            try:
                llm_response_event['temperature'] = float(temperature)
            except (ValueError, TypeError):
                pass
                
        if top_p is not None:
            try:
                llm_response_event['top_p'] = float(top_p)
            except (ValueError, TypeError):
                pass
        
        # 이벤트 기록
        with newrelic.agent.BackgroundTask(nr_app, name=f"EventRecording/LlmResponse"):
            newrelic.agent.record_custom_event(EVENT_TYPE_LLM_RESPONSE, llm_response_event, application=nr_app)
        
        return True
    except Exception as e:
        st.warning(f"Bedrock 응답 기록 중 오류: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return False

def extract_claude_response_text(response_body):
    """
    Claude API 응답에서 텍스트 추출
    
    :param response_body: Claude API 응답 본문
    :return: 추출된 응답 텍스트
    """
    assistant_response = ""
    if "content" in response_body and len(response_body["content"]) > 0:
        for content_item in response_body["content"]:
            if content_item["type"] == "text":
                assistant_response += content_item["text"]
    return assistant_response

def get_sample_nrql_queries(trace_id=None, completion_id=None, conversation_id=None, kb_id=None):
    """
    샘플 NRQL 쿼리 생성
    
    :param trace_id: 트레이스 ID
    :param completion_id: 완성 ID
    :param conversation_id: 대화 ID
    :param kb_id: 지식 기반 ID
    :return: 샘플 NRQL 쿼리 딕셔너리
    """
    queries = {
        "토큰_사용량_분석": f"""
        # 토큰 사용량과 만족도 상관관계
        FROM LlmUserResponseEvaluation SELECT 
        prompt_tokens + completion_tokens AS '총 토큰',
        overall_score AS '만족도'
        WHERE prompt_tokens IS NOT NULL AND completion_tokens IS NOT NULL
        SINCE 1 hour AGO
        LIMIT 1000
        """,
        
        "토큰_필드_확인": f"""
        # 모든 토큰 관련 필드 확인
        FROM LlmUserResponseEvaluation SELECT 
          count(*) AS '이벤트 수',
          percentage(count(*), WHERE total_tokens IS NOT NULL) AS '총 토큰 정보 있음',
          percentage(count(*), WHERE completion_tokens IS NOT NULL) AS '완성 토큰 정보 있음',
          percentage(count(*), WHERE prompt_tokens IS NOT NULL) AS '프롬프트 토큰 정보 있음'
        SINCE 1 hour AGO
        """,
        
        "모델별_토큰_사용량": f"""
        # 모델별 토큰 사용량
        FROM LlmUserResponseEvaluation SELECT 
          average(prompt_tokens) AS '평균 프롬프트 토큰',
          average(completion_tokens) AS '평균 완성 토큰',
          average(prompt_tokens + completion_tokens) AS '평균 총 토큰',
          sum(prompt_tokens + completion_tokens) / uniqueCount(trace_id) AS '대화당 평균 토큰'
        FACET model_id, kb_id
        WHERE prompt_tokens IS NOT NULL AND completion_tokens IS NOT NULL
        SINCE 1 hour AGO
        LIMIT MAX
        """
    }
    
    # ID 관련 쿼리 추가
    if conversation_id:
        queries["대화_조회"] = f"""
        # 대화 전체 조회
        FROM {EVENT_TYPE_SYSTEM_PROMPT} SELECT *
        WHERE conversation_id = '{conversation_id}'
        ORDER BY message_index ASC
        SINCE 1 hour AGO

        FROM {EVENT_TYPE_USER_PROMPT} SELECT *
        WHERE conversation_id = '{conversation_id}'
        ORDER BY message_index ASC
        SINCE 1 hour AGO

        FROM {EVENT_TYPE_RAG_CONTEXT} SELECT *
        WHERE conversation_id = '{conversation_id}'
        ORDER BY message_index ASC
        SINCE 1 hour AGO
        """
    
    if completion_id:
        queries["특정_응답_조회"] = f"""
        # 특정 완성 ID의 모델 평가 이벤트 조회
        FROM LlmUserResponseEvaluation SELECT *
        WHERE completion_id = '{completion_id}'
        SINCE 1 hour AGO
        
        # 특정 완성 ID의 Bedrock 응답 조회
        FROM {EVENT_TYPE_LLM_RESPONSE} SELECT *
        WHERE completion_id = '{completion_id}'
        SINCE 1 hour AGO
        """
    
    if kb_id:
        queries["지식_기반_성능"] = f"""
        # 특정 지식 기반 ID의 모델 평가 이벤트 조회
        FROM LlmUserResponseEvaluation SELECT *
        WHERE kb_id = '{kb_id}'
        ORDER BY timestamp DESC
        SINCE 1 hour AGO

        # 모델 ID와 지식 기반 ID별 평가 이벤트 수 조회
        FROM LlmUserResponseEvaluation SELECT count(*) 
        FACET model_id, kb_id 
        WHERE kb_id IS NOT NULL
        SINCE 1 hour AGO
        """
    
    return queries

def search_knowledge_base(query, bedrock_agent_client, kb_id, max_results=5):
    """
    지식 기반에서 쿼리와 관련된 정보 검색
    
    :param query: 검색 쿼리
    :param bedrock_agent_client: Bedrock Agent 클라이언트
    :param kb_id: 지식 기반 ID
    :param max_results: 최대 결과 수
    :return: (검색 결과 목록, 응답 시간)
    """
    try:
        # 검색 실행
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': max_results
                }
            }
        )
        
        # 검색 결과 처리
        search_results = []
        for result in response.get('retrievalResults', []):
            content = result.get('content', {}).get('text', '')
            title = result.get('location', {}).get('s3Location', {}).get('uri', 'No Title')
            if '/' in title:
                title = title.split('/')[-1]  # S3 키에서 파일 이름만 추출
                
            search_results.append({
                'title': title,
                'content': content,
                'score': result.get('score', 0.0)
            })
        
        # 검색 시간 (밀리초)
        response_time = int(response.get('responseMetadata', {}).get('totalTime', 0) * 1000)
        
        return search_results, response_time
    except Exception as e:
        raise Exception(f"지식 기반 검색 오류: {str(e)}") 