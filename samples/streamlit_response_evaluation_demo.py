#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit에서 모델 만족도 평가 데모

이 샘플은 Streamlit UI를 사용하여 AWS Bedrock 모델의 응답에 대한
만족도 평가를 수집하는 방법을 보여줍니다.

실행 방법: streamlit run streamlit_response_evaluation_demo.py
"""

import os
import json
import uuid
import boto3
import time
import logging
import streamlit as st

# LangChain 임포트 (선택 사항)
try:
    import langchain
    import langchain.llms
    from langchain.memory import ConversationBufferMemory
    from langchain.chains import ConversationalRetrievalChain
    LANGCHAIN_AVAILABLE = True
    LANGCHAIN_VERSION = langchain.__version__
except ImportError:
    LANGCHAIN_AVAILABLE = False
    LANGCHAIN_VERSION = None

from nr_bedrock_observability import (
    monitor_bedrock,
    create_response_evaluation_collector,
    create_streamlit_response_evaluation_collector
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit 앱 설정
st.set_page_config(
    page_title="Bedrock 모델 만족도 평가 데모",
    page_icon="🤖",
    layout="wide"
)

def get_bedrock_client():
    """
    AWS Bedrock 클라이언트 생성
    """
    try:
        return boto3.client('bedrock-runtime')
    except Exception as e:
        st.error(f"Bedrock 클라이언트 생성 중 오류: {str(e)}")
        return None

def get_bedrock_kb_client():
    """
    AWS Bedrock 지식 기반 클라이언트 생성
    """
    try:
        return boto3.client('bedrock-agent-runtime')
    except Exception as e:
        logger.warning(f"Bedrock 지식 기반 클라이언트 생성 중 오류: {str(e)}")
        return None

def get_monitored_client(bedrock_client, application_name, nr_api_key, trace_id):
    """
    New Relic 모니터링이 적용된 Bedrock 클라이언트 생성
    """
    try:
        return monitor_bedrock(bedrock_client, {
            'application_name': application_name,
            'new_relic_api_key': nr_api_key,
            'trace_id': trace_id
        })
    except Exception as e:
        st.error(f"모니터링 클라이언트 생성 중 오류: {str(e)}")
        return None

def invoke_model(client, model_id, prompt, kb_id=None):
    """
    Bedrock 모델 호출 (지식 기반 사용 옵션 포함)
    """
    try:
        start_time = time.time()
        
        if kb_id:
            # 지식 기반을 사용하는 경우
            kb_client = get_bedrock_kb_client()
            if not kb_client:
                st.warning("지식 기반 클라이언트를 생성할 수 없어 일반 모델을 사용합니다.")
                return invoke_model(client, model_id, prompt)
                
            response = kb_client.retrieve_and_generate(
                knowledgeBaseId=kb_id,
                input={
                    "text": prompt
                },
                retrieveAndGenerateConfiguration={
                    "type": "KNOWLEDGE_BASE",
                    "knowledgeBaseConfiguration": {
                        "modelId": model_id,
                        "generationConfiguration": {
                            "temperature": 0.5,
                            "maxTokens": 1000
                        }
                    }
                }
            )
            
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)
            
            return {
                "text": response["output"]["text"], 
                "response_time": response_time,
                "kb_used": True
            }
        else:
            # 일반 모델 호출
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ]
                })
            )
            
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)
            
            response_body = json.loads(response['body'].read().decode('utf-8'))
            return {
                "text": response_body['content'][0]['text'],
                "response_time": response_time,
                "kb_used": False,
                "token_info": {
                    "input_tokens": response_body.get("usage", {}).get("input_tokens", 0),
                    "output_tokens": response_body.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": response_body.get("usage", {}).get("total_tokens", 0)
                }
            }
    except Exception as e:
        st.error(f"모델 호출 중 오류: {str(e)}")
        return None

def invoke_with_langchain(client, model_id, prompt):
    """
    LangChain을 사용하여 Bedrock 모델 호출
    """
    if not LANGCHAIN_AVAILABLE:
        st.error("LangChain이 설치되어 있지 않습니다.")
        return None
    
    try:
        from langchain.llms import Bedrock
        
        start_time = time.time()
        
        # LangChain Bedrock LLM 설정
        llm = Bedrock(
            model_id=model_id,
            client=client
        )
        
        # 단순 생성 요청
        response = llm.predict(prompt)
        
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)
        
        # 입력과 출력 토큰 수 예측 (정확하지 않을 수 있음)
        input_tokens = len(prompt.split()) * 1.3  # 대략적인 추정값
        output_tokens = len(response.split()) * 1.3  # 대략적인 추정값
        
        return {
            "text": response,
            "response_time": response_time,
            "kb_used": False,
            "langchain_used": True,
            "langchain_version": LANGCHAIN_VERSION,
            "langchain_chain_type": "SimpleLLMChain",
            "token_info": {
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "total_tokens": int(input_tokens + output_tokens)
            }
        }
    except Exception as e:
        st.error(f"LangChain 실행 중 오류: {str(e)}")
        return None

def main():
    # 앱 제목
    st.title("AWS Bedrock 모델 만족도 평가 데모")
    st.subheader("모델 응답 만족도 평가 예제")
    
    # 사이드바 설정
    with st.sidebar:
        st.header("설정")
        
        # New Relic API 키 설정
        nr_api_key = st.text_input(
            "New Relic API 키",
            value=os.environ.get('NEW_RELIC_API_KEY', 'test-api-key'),
            type="password"
        )
        
        # 애플리케이션 이름 설정
        application_name = st.text_input(
            "애플리케이션 이름",
            value="Streamlit-Model-Evaluation-Demo"
        )
        
        # 모델 선택
        model_id = st.selectbox(
            "사용할 모델",
            [
                "anthropic.claude-3-sonnet-20240229-v1:0",
                "anthropic.claude-3-haiku-20240307-v1:0",
                "anthropic.claude-3-opus-20240229-v1:0",
                "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "anthropic.claude-3-5-sonnet-20241022-v2:0"
            ]
        )
        
        # 통합 옵션
        st.subheader("통합 옵션")
        
        # Bedrock 지식 기반 옵션
        use_kb = st.checkbox("Bedrock 지식 기반 사용", value=False)
        
        kb_id = None
        kb_name = None
        
        if use_kb:
            kb_id = st.text_input("지식 기반 ID")
            kb_name = st.text_input("지식 기반 이름 (선택사항)")
            
        # LangChain 옵션
        use_langchain = st.checkbox("LangChain 사용", value=False, disabled=not LANGCHAIN_AVAILABLE)
        
        if not LANGCHAIN_AVAILABLE and use_langchain:
            st.warning("LangChain 패키지가 설치되어 있지 않습니다.")
        
        # 세션 초기화
        if st.button("세션 초기화"):
            st.session_state.clear()
            st.experimental_rerun()
        
        # 모델 성능 통계
        st.subheader("모델 평가 통계")
        if "evaluation_stats" not in st.session_state:
            st.session_state.evaluation_stats = {}
        
        for model in ["anthropic.claude-3-sonnet", "anthropic.claude-3-haiku", "anthropic.claude-3-opus"]:
            if model in st.session_state.evaluation_stats:
                stats = st.session_state.evaluation_stats[model]
                st.metric(
                    label=f"{model}",
                    value=f"{stats['overall_avg']:.1f}/10",
                    delta=f"정확성: {stats['accuracy_avg']:.1f}"
                )
    
    # 트레이스 ID 초기화 (세션 시작시)
    if "trace_id" not in st.session_state:
        st.session_state.trace_id = str(uuid.uuid4())
    
    # 평가 유형 선택 (기본 또는 상세)
    evaluation_type = st.radio(
        "평가 유형 선택",
        ["기본 평가", "상세 평가"],
        horizontal=True
    )
    
    # 쿼리 유형 선택
    query_types = ["일반 지식", "창의적 생성", "코딩/기술", "분석/추론"]
    selected_type = st.radio("질문 유형", query_types, horizontal=True)
    
    # 도메인 선택
    domain_types = ["일반", "기술", "과학", "비즈니스", "예술", "기타"]
    selected_domain = st.selectbox("도메인 분야", domain_types)
    
    # 쿼리 유형별 예제 프롬프트
    example_prompts = {
        "일반 지식": "인공지능의 역사와 발전 과정에 대해 설명해주세요.",
        "창의적 생성": "안개가 자욱한 고성이 배경인 판타지 소설의 첫 문단을 작성해주세요.",
        "코딩/기술": "React에서 상태를 관리하는 방법들과 각 방법의 장단점을 설명해주세요.",
        "분석/추론": "기후 변화가 글로벌 식량 안보에 미치는 영향과 가능한 해결책을 분석해주세요."
    }
    
    # 프롬프트 입력 폼
    with st.form("prompt_form"):
        prompt = st.text_area(
            "Bedrock에 보낼 프롬프트를 입력하세요",
            value=example_prompts[selected_type],
            height=100
        )
        submit_button = st.form_submit_button("응답 생성")
    
    # 폼 제출 처리
    if submit_button:
        # 세션에 새 응답 생성 표시
        st.session_state.new_response = True
        st.session_state.current_model_id = model_id
        
        # Bedrock 클라이언트 생성
        bedrock_client = get_bedrock_client()
        if not bedrock_client:
            return
        
        # 모니터링 클라이언트 생성
        monitored_client = get_monitored_client(
            bedrock_client,
            application_name,
            nr_api_key,
            st.session_state.trace_id
        )
        if not monitored_client:
            return
        
        # 로딩 스피너 표시
        with st.spinner("Bedrock에서 응답을 생성 중입니다..."):
            # 실행 방법 선택
            if use_langchain and LANGCHAIN_AVAILABLE:
                result_data = invoke_with_langchain(monitored_client, model_id, prompt)
            elif use_kb and kb_id:
                result_data = invoke_model(monitored_client, model_id, prompt, kb_id=kb_id)
            else:
                result_data = invoke_model(monitored_client, model_id, prompt)
        
        if result_data:
            # 응답 및 메타데이터 저장
            st.session_state.result = result_data["text"]
            st.session_state.response_time = result_data.get("response_time", 0)
            st.session_state.kb_used = result_data.get("kb_used", False)
            st.session_state.kb_id = kb_id if use_kb else None
            st.session_state.kb_name = kb_name if use_kb else None
            
            # LangChain 메타데이터
            st.session_state.langchain_used = result_data.get("langchain_used", False)
            st.session_state.langchain_version = result_data.get("langchain_version", LANGCHAIN_VERSION)
            st.session_state.langchain_chain_type = result_data.get("langchain_chain_type", None)
            
            # 토큰 정보
            token_info = result_data.get("token_info", {})
            st.session_state.prompt_tokens = token_info.get("input_tokens", 0)
            st.session_state.completion_tokens = token_info.get("output_tokens", 0)
            st.session_state.total_tokens = token_info.get("total_tokens", 0)
            
            # 시작 시간 기록
            st.session_state.query_type = selected_type
            st.session_state.domain = selected_domain
            
            # 성공 메시지
            st.success("응답이 생성되었습니다")
    
    # 응답 표시
    if "result" in st.session_state:
        st.subheader("Bedrock 응답")
        
        # 모델 ID 정보
        model_name = st.session_state.current_model_id.split(':')[0]
        st.info(f"모델: {model_name}")
        
        # 응답 내용
        st.markdown(st.session_state.result)
        
        # 응답 메타데이터 표시
        metadata_cols = st.columns(4)
        with metadata_cols[0]:
            st.metric("응답 시간", f"{st.session_state.response_time}ms")
        
        with metadata_cols[1]:
            total_tokens = st.session_state.get("total_tokens", 0)
            st.metric("총 토큰 수", f"{total_tokens}")
        
        with metadata_cols[2]:
            kb_used = "사용함" if st.session_state.get("kb_used", False) else "사용 안함"
            st.metric("지식 기반", kb_used)
            
        with metadata_cols[3]:
            langchain_used = "사용함" if st.session_state.get("langchain_used", False) else "사용 안함"
            st.metric("LangChain", langchain_used)
        
        # 구분선
        st.divider()
        
        # 응답 평가 수집기 생성
        if "response_evaluation_collector" not in st.session_state:
            st.session_state.response_evaluation_collector = create_response_evaluation_collector(
                application_name=application_name,
                trace_id=st.session_state.trace_id
            )
        
        # Streamlit 평가 수집기 생성
        if "streamlit_evaluation_collector" not in st.session_state:
            st.session_state.streamlit_evaluation_collector = create_streamlit_response_evaluation_collector(
                application_name=application_name,
                response_evaluation_collector=st.session_state.response_evaluation_collector
            )
        
        # 새 응답이 생성된 경우 평가 상태 초기화
        if st.session_state.get("new_response", False):
            st.session_state.streamlit_evaluation_collector.reset_evaluation()
            st.session_state.new_response = False
        
        # 선택한 평가 유형에 따라 UI 렌더링
        if evaluation_type == "기본 평가":
            evaluation_data = st.session_state.streamlit_evaluation_collector.render_basic_evaluation_ui(
                model_id=st.session_state.current_model_id
            )
        else:
            evaluation_data = st.session_state.streamlit_evaluation_collector.render_detailed_evaluation_ui(
                model_id=st.session_state.current_model_id
            )
        
        # 평가가 제출되면 데이터 표시 및 통계 업데이트
        if evaluation_data:
            # 모델 평가에 추가 정보 추가
            if "response_evaluation_collector" in st.session_state:
                collector = st.session_state.response_evaluation_collector
                
                # 추가 모델 메타데이터
                model_provider = evaluation_data["model_id"].split('.')[0] if '.' in evaluation_data["model_id"] else None
                
                # 지식 기반 및 LangChain 정보
                kb_data = {
                    "kb_id": st.session_state.get("kb_id"),
                    "kb_name": st.session_state.get("kb_name"),
                    "kb_used_in_query": st.session_state.get("kb_used", False)
                }
                
                langchain_data = {
                    "langchain_used": st.session_state.get("langchain_used", False),
                    "langchain_version": st.session_state.get("langchain_version"),
                    "langchain_chain_type": st.session_state.get("langchain_chain_type")
                }
                
                token_data = {
                    "total_tokens": st.session_state.get("total_tokens", 0),
                    "prompt_tokens": st.session_state.get("prompt_tokens", 0),
                    "completion_tokens": st.session_state.get("completion_tokens", 0)
                }
                
                # 응답 시간
                response_time_data = {
                    "response_time_ms": st.session_state.get("response_time", 0)
                }
                
                # 새로운 평가 기록 생성
                try:
                    augmented_eval = collector.record_evaluation(
                        model_id=evaluation_data["model_id"],
                        model_provider=model_provider,
                        overall_score=evaluation_data["overall_score"],
                        relevance_score=evaluation_data.get("relevance_score"),
                        accuracy_score=evaluation_data.get("accuracy_score"),
                        completeness_score=evaluation_data.get("completeness_score"),
                        coherence_score=evaluation_data.get("coherence_score"),
                        helpfulness_score=evaluation_data.get("helpfulness_score"),
                        query_type=st.session_state.get("query_type"),
                        domain=st.session_state.get("domain"),
                        **kb_data,
                        **langchain_data,
                        **token_data,
                        **response_time_data,
                        feedback_comment=evaluation_data.get("feedback_comment"),
                        evaluation_source="streamlit"
                    )
                    evaluation_data = augmented_eval
                except Exception as e:
                    st.error(f"평가 데이터 업데이트 중 오류: {str(e)}")
            
            # 모델 통계 업데이트
            model_base = model_name.split('-v')[0]
            
            if "evaluation_stats" not in st.session_state:
                st.session_state.evaluation_stats = {}
                
            if model_base not in st.session_state.evaluation_stats:
                st.session_state.evaluation_stats[model_base] = {
                    "count": 0,
                    "overall_sum": 0,
                    "accuracy_sum": 0,
                    "overall_avg": 0,
                    "accuracy_avg": 0
                }
                
            stats = st.session_state.evaluation_stats[model_base]
            stats["count"] += 1
            stats["overall_sum"] += evaluation_data["overall_score"]
            
            if "accuracy_score" in evaluation_data:
                stats["accuracy_sum"] += evaluation_data["accuracy_score"]
                
            stats["overall_avg"] = stats["overall_sum"] / stats["count"]
            
            if stats["count"] > 0:
                stats["accuracy_avg"] = stats["accuracy_sum"] / stats["count"]
            
            # 제출된 평가 데이터 표시
            st.subheader("제출된 평가 데이터")
            
            # 핵심 메트릭 표시
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("전체 만족도", f"{evaluation_data['overall_score']}/10")
            
            if "relevance_score" in evaluation_data:
                with col2:
                    st.metric("관련성", f"{evaluation_data['relevance_score']}/10")
            
            if "accuracy_score" in evaluation_data:
                with col3:
                    st.metric("정확성", f"{evaluation_data['accuracy_score']}/10")
            
            # 사용된 기술 표시
            tech_cols = st.columns(3)
            with tech_cols[0]:
                if "kb_used_in_query" in evaluation_data and evaluation_data["kb_used_in_query"]:
                    st.success("Bedrock 지식 기반 사용됨")
                    if "kb_name" in evaluation_data and evaluation_data["kb_name"]:
                        st.caption(f"KB: {evaluation_data['kb_name']}")
            
            with tech_cols[1]:
                if "langchain_used" in evaluation_data and evaluation_data["langchain_used"]:
                    st.success("LangChain 사용됨")
                    if "langchain_version" in evaluation_data and evaluation_data["langchain_version"]:
                        st.caption(f"버전: {evaluation_data['langchain_version']}")
            
            with tech_cols[2]:
                if "total_tokens" in evaluation_data and evaluation_data["total_tokens"]:
                    st.info(f"총 토큰: {evaluation_data['total_tokens']}")
                    prompt_tokens = evaluation_data.get("prompt_tokens", 0)
                    completion_tokens = evaluation_data.get("completion_tokens", 0)
                    st.caption(f"입력: {prompt_tokens}, 출력: {completion_tokens}")
            
            # 모델 평가 기록 표시
            if "feedback_comment" in evaluation_data and evaluation_data["feedback_comment"]:
                st.info(f"피드백: {evaluation_data['feedback_comment']}")
            
            # 상세 데이터(옵션)
            with st.expander("모든 평가 데이터", expanded=False):
                st.json(evaluation_data)

if __name__ == "__main__":
    main() 