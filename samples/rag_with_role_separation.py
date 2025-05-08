"""
메시지 역할별 분리, OpenSearch 결과 분리, 시스템 프롬프트 세부 분류 예제

이 샘플 코드는 다음을 보여줍니다:
1. 시스템 프롬프트를 별도의 이벤트로 분리하여 기록
2. 사용자 질문을 별도의 이벤트로 분리하여 기록
3. OpenSearch 검색 결과를 별도의 이벤트로 분리하여 기록
4. RAG 컨텍스트를 별도의 이벤트로 분리하여 기록
5. 전체 워크플로우 트레이싱 연결
"""

import json
import time
import uuid
import boto3
import newrelic.agent
from nr_bedrock_observability import monitor_bedrock, link_rag_workflow, monitor_opensearch_results

# Bedrock 클라이언트 설정
def get_bedrock_client(region_name='ap-northeast-2'):
    return boto3.client('bedrock-runtime', region_name=region_name)

# 가상 OpenSearch 결과 생성 (실제 OpenSearch 없이 예제 시연)
def get_mock_opensearch_results(query):
    """가상 OpenSearch 결과 생성"""
    # 쿼리에 따라 다른 결과 반환
    if '인공지능' in query or 'AI' in query:
        return [
            {
                'title': '인공지능 소개',
                'content': '인공지능(AI)은 인간의 지능을 모방하도록 설계된 시스템입니다. 기계 학습, 딥러닝, 자연어 처리 등의 기술을 포함합니다.',
                'score': 0.92
            },
            {
                'title': '딥러닝 기초',
                'content': '딥러닝은 인공신경망을 여러 계층으로 쌓아 복잡한 패턴을 학습하는 기술입니다. 이미지 인식, 자연어 처리 등에 사용됩니다.',
                'score': 0.85
            },
            {
                'title': 'AI 윤리',
                'content': 'AI 윤리는 인공지능 기술 개발과 사용에 있어 윤리적 고려사항을 다룹니다. 투명성, 공정성, 책임성이 중요한 요소입니다.',
                'score': 0.78
            }
        ]
    elif '클라우드' in query or 'cloud' in query:
        return [
            {
                'title': 'AWS 클라우드 소개',
                'content': 'AWS(Amazon Web Services)는 아마존이 제공하는 클라우드 컴퓨팅 플랫폼입니다. EC2, S3, Lambda 등 다양한 서비스를 제공합니다.',
                'score': 0.94
            },
            {
                'title': '클라우드 컴퓨팅의 이점',
                'content': '클라우드 컴퓨팅은 확장성, 유연성, 비용 효율성을 제공합니다. 필요에 따라 리소스를 조정할 수 있고 초기 투자 비용이 적습니다.',
                'score': 0.87
            }
        ]
    else:
        return [
            {
                'title': '일반 정보',
                'content': '귀하의 질문에 관련된 정보가 데이터베이스에 충분하지 않습니다. 더 자세한 질문을 해주세요.',
                'score': 0.6
            }
        ]

# 피드백 콜백 함수 (사용자 피드백 처리)
def feedback_callback(input_text, output_text):
    """사용자 피드백 콜백 함수"""
    # 실제 상황에서는 사용자로부터 피드백을 수집하는 로직
    # 예제에서는 하드코딩된 값 반환
    return {
        'feedback': 'positive',  # 'positive', 'negative', 'neutral'
        'sentiment': 0.9,  # -1.0에서 1.0 사이 감정 점수
        'feedback_message': '정확하고 유용한 정보를 제공해주었습니다.'
    }

# RAG 샘플 함수 (역할별 메시지 분리)
@newrelic.agent.background_task(name='rag_with_role_separation')
def rag_with_role_separation(
    user_query, 
    system_instruction=None,
    application_name='RAG-Role-Separation-Demo'
):
    """
    역할별 메시지 분리와 OpenSearch 결과 분리를 시연하는 RAG 예제
    
    :param user_query: 사용자 질문
    :param system_instruction: 시스템 프롬프트 (없으면 기본값 사용)
    :param application_name: 애플리케이션 이름
    :return: 프로세스의 결과
    """
    # 기본 시스템 프롬프트 설정
    if not system_instruction:
        system_instruction = "당신은 도움이 되는 AI 비서입니다. 주어진 컨텍스트 정보를 기반으로 정확하고 간결하게 답변해주세요."
    
    # Bedrock 클라이언트 생성 및 모니터링 설정
    bedrock_client = get_bedrock_client()
    monitored_client = monitor_bedrock(bedrock_client, {
        'application_name': application_name,
        'collect_feedback': True,
        'feedback_callback': feedback_callback
    })
    
    # 가상 OpenSearch 검색 결과 가져오기
    opensearch_results = get_mock_opensearch_results(user_query)
    
    # 컨텍스트 텍스트 구성
    context_text = "\n\n".join([
        f"제목: {result.get('title', 'No Title')}\n내용: {result.get('content', 'No Content')}"
        for result in opensearch_results
    ])
    
    # 시간 측정 시작
    start_time = time.time()
    
    # OpenSearch 결과 모니터링 (검색 함수 호출 없이 결과만 전달)
    monitor_opensearch_results(
        opensearch_client=None,  # 실제 클라이언트 필요 없음
        query=user_query,
        results=opensearch_results,
        application_name=application_name,
        response_time=int((time.time() - start_time) * 1000)  # 밀리초 단위
    )
    
    # Bedrock 요청 구성
    request = {
        'modelId': 'anthropic.claude-3-sonnet-20240229-v1:0',
        'body': json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "system",
                    "content": system_instruction
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            다음 정보에 기반하여 질문에 답변해주세요:
                            
                            컨텍스트:
                            {context_text}
                            
                            질문: {user_query}
                            """
                        }
                    ]
                }
            ],
            "temperature": 0.7
        })
    }
    
    # RAG 워크플로우 연결 (트레이스 ID 생성 및 OpenSearch 결과 기록)
    trace_id = link_rag_workflow(
        user_query=user_query,
        opensearch_results=opensearch_results,
        bedrock_client=monitored_client,
        bedrock_request=request,
        application_name=application_name
    )
    
    # Claude 3 호출
    response = monitored_client.invoke_model(**request)
    
    # 응답 처리
    response_body = json.loads(response['body'].read().decode('utf-8'))
    generated_text = ""
    
    if "content" in response_body and len(response_body["content"]) > 0:
        for content_item in response_body["content"]:
            if content_item["type"] == "text":
                generated_text += content_item["text"]
    
    # 결과 반환
    return {
        'query': user_query,
        'system_instruction': system_instruction,
        'opensearch_results': opensearch_results,
        'context_text': context_text,
        'llm_response': generated_text,
        'trace_id': trace_id
    }

# 메인 함수
def main():
    """
    메인 실행 함수
    """
    print("=== 메시지 역할별 분리와 OpenSearch 결과 분리 예제 ===\n")
    
    # New Relic 애플리케이션 초기화
    # 실제 환경에서는 newrelic.ini 설정 파일을 사용하거나 환경 변수 설정 필요
    
    # 테스트 쿼리로 RAG 실행
    test_queries = [
        "인공지능의 기본 개념에 대해 설명해주세요.",
        "클라우드 컴퓨팅의 장점은 무엇인가요?",
        "최신 자연어 처리 기술에는 어떤 것들이 있나요?"
    ]
    
    for query in test_queries:
        print(f"\n질문: {query}")
        result = rag_with_role_separation(query)
        print(f"답변: {result['llm_response'][:200]}...\n")
        print(f"트레이스 ID: {result['trace_id']}")
        print("-" * 80)
        
        # 사용자가 응답을 확인할 수 있도록 잠시 대기
        time.sleep(1)
    
    print("\n결과를 New Relic에서 확인하세요. 다음 NRQL 쿼리를 사용할 수 있습니다:")
    print("""
    -- 전체 RAG 워크플로우 보기
    FROM Span WHERE rag.workflow = 'true' FACET name LIMIT 100
    
    -- 시스템 프롬프트 조회
    FROM LlmSystemPrompt LIMIT 100
    
    -- 사용자 프롬프트 조회
    FROM LlmUserPrompt LIMIT 100
    
    -- OpenSearch 결과 조회
    FROM LlmOpenSearchResult LIMIT 100
    
    -- RAG 컨텍스트 조회
    FROM LlmRagContext LIMIT 100
    
    -- 채팅 메시지 역할별 조회
    FROM LlmChatCompletionMessage FACET role LIMIT 100
    """)

if __name__ == "__main__":
    main() 