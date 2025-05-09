"""
OpenSearch와 Bedrock을 사용한 RAG 워크플로우를 하나의 트레이싱으로 연결하는 예제

이 예제는 다음 워크플로우를 하나의 트레이싱으로 연결합니다:
1. 사용자 질문 입력
2. AWS OpenSearch를 통한 검색
3. 검색 결과 반환
4. AWS Bedrock을 사용한 LLM 응답 생성
"""

import json
import time
import uuid
import boto3
import newrelic.agent
from newrelic.api.transaction import current_transaction
from newrelic.api.time_trace import TimeTrace
from newrelic.common.object_wrapper import wrap_function_wrapper
from nr_bedrock_observability import monitor_bedrock

# OpenSearch 클라이언트 설정
def get_opensearch_client(region_name='ap-northeast-2'):
    return boto3.client('opensearch', region_name=region_name)

# Bedrock 클라이언트 설정
def get_bedrock_client(region_name='ap-northeast-2'):
    return boto3.client('bedrock-runtime', region_name=region_name)

# 커스텀 함수 트레이스를 위한 컨텍스트 매니저
class CustomFunctionTrace(TimeTrace):
    def __init__(self, name, group='Custom', trace_id=None):
        # TimeTrace.__init__()는 name과 group을 파라미터로 받지 않음
        super(CustomFunctionTrace, self).__init__()
        self.name = name
        self.group = group
        self.trace_id = trace_id
        
    def __enter__(self):
        result = super(CustomFunctionTrace, self).__enter__()
        
        transaction = current_transaction()
        if transaction and self.trace_id:
            # 현재 스팬에 트레이스 ID와 기타 필요한 메타데이터 추가
            newrelic.agent.add_custom_span_attribute('trace.id', self.trace_id)
            
        return result

# OpenSearch 검색 함수
def search_opensearch(domain_endpoint, index_name, query_text, trace_id=None):
    """OpenSearch에서 검색 실행"""
    
    with CustomFunctionTrace(name='search_opensearch', trace_id=trace_id):
        # 트레이스 ID 및 관련 메타데이터 스팬에 추가
        if trace_id:
            newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
            newrelic.agent.add_custom_span_attribute('openSearch.query', query_text)
            newrelic.agent.add_custom_span_attribute('openSearch.index', index_name)
            newrelic.agent.add_custom_span_attribute('rag.workflow', 'true')
        
        try:
            # OpenSearch 클라이언트 생성
            opensearch_client = get_opensearch_client()
            
            # 검색 요청 구성
            search_body = {
                'query': {
                    'multi_match': {
                        'query': query_text,
                        'fields': ['content', 'title']
                    }
                }
            }
            
            # OpenSearch 검색 API 호출 시뮬레이션
            # 실제 환경에서는 아래 주석 해제하여 실제 OpenSearch API 사용
            # response = opensearch_client.search(
            #     Body=json.dumps(search_body),
            #     Index=index_name
            # )
            
            # 테스트를 위한 가상 응답
            response = {
                'hits': {
                    'hits': [
                        {
                            '_source': {
                                'content': '인공지능(AI)은 인간의 지능을 모방하도록 설계된 시스템입니다.',
                                'title': '인공지능 소개'
                            },
                            '_score': 0.9
                        },
                        {
                            '_source': {
                                'content': '딥러닝은 인공신경망을 여러 계층으로 쌓아 복잡한 패턴을 학습하는 기술입니다.',
                                'title': '딥러닝 기초'
                            },
                            '_score': 0.7
                        }
                    ],
                    'total': {
                        'value': 2
                    }
                }
            }
            
            # 검색 결과 추출
            search_results = [hit['_source'] for hit in response['hits']['hits']]
            
            # New Relic에 검색 결과 정보 추가
            if trace_id:
                newrelic.agent.add_custom_span_attribute('openSearch.resultsCount', len(search_results))
            
            return search_results
            
        except Exception as e:
            # 오류 정보를 New Relic에 기록
            if trace_id:
                newrelic.agent.add_custom_span_attribute('openSearch.error', str(e))
            raise

# Bedrock을 사용한 텍스트 생성 함수
def generate_text_with_bedrock(prompt, context_text, trace_id=None):
    """Bedrock 모델을 사용하여 텍스트 생성"""
    
    with CustomFunctionTrace(name='generate_text_with_bedrock', trace_id=trace_id):
        # 트레이스 ID 및 관련 메타데이터 스팬에 추가
        if trace_id:
            newrelic.agent.add_custom_span_attribute('trace.id', trace_id)
            newrelic.agent.add_custom_span_attribute('bedrock.model', 'anthropic.claude-3-sonnet-20240229-v1:0')
            newrelic.agent.add_custom_span_attribute('rag.workflow', 'true')
            
        try:
            # Bedrock 클라이언트 생성 및 모니터링 설정
            bedrock_client = get_bedrock_client()
            monitor_options = {
                'application_name': 'RAG-Workflow-Demo',
                'track_token_usage': True
            }
            monitored_client = monitor_bedrock(bedrock_client, monitor_options)
            
            # Claude 형식의 프롬프트 구성
            full_prompt = f"""
            다음 정보에 기반하여 질문에 답변해주세요:
            
            컨텍스트:
            {context_text}
            
            질문: {prompt}
            
            답변:
            """
            
            # Claude 3 호출
            response = monitored_client.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": full_prompt
                                }
                            ]
                        }
                    ],
                    "temperature": 0.7
                })
            )
            
            # 응답 처리
            response_body = json.loads(response['body'].read().decode('utf-8'))
            generated_text = ""
            
            if "content" in response_body and len(response_body["content"]) > 0:
                for content_item in response_body["content"]:
                    if content_item["type"] == "text":
                        generated_text += content_item["text"]
            
            return generated_text
            
        except Exception as e:
            # 오류 정보를 New Relic에 기록
            if trace_id:
                newrelic.agent.add_custom_span_attribute('bedrock.error', str(e))
            raise

# 통합 RAG 워크플로우 함수
@newrelic.agent.background_task(name='rag_workflow')
def rag_workflow(user_query, opensearch_domain, index_name):
    """
    통합 RAG 워크플로우 실행:
    1. 트랜잭션 ID 생성 및 설정
    2. OpenSearch 검색 실행
    3. 검색 결과를 컨텍스트로 사용
    4. Bedrock LLM 모델로 응답 생성
    """
    try:
        # 고유 트레이스 ID 생성
        trace_id = str(uuid.uuid4())
        
        # 트랜잭션에 메타데이터 추가
        transaction = current_transaction()
        if transaction:
            transaction.add_custom_attribute('trace.id', trace_id)
            transaction.add_custom_attribute('workflow.type', 'rag')
            transaction.add_custom_attribute('user.query', user_query)
            
            # 트레이스 ID를 New Relic의 distributed tracing 시스템에 연결
            # 이를 통해 전체 워크플로우를 하나의 트레이스로 볼 수 있음
            current_trace_id = newrelic.agent.current_trace_id()
            if current_trace_id:
                transaction.add_custom_attribute('nr.trace_id', current_trace_id)
        
        # 1. OpenSearch 검색 수행
        search_results = search_opensearch(
            domain_endpoint=opensearch_domain,
            index_name=index_name,
            query_text=user_query,
            trace_id=trace_id
        )
        
        # 검색 결과를 컨텍스트로 변환
        context_text = "\n\n".join([
            f"제목: {result.get('title', 'No Title')}\n내용: {result.get('content', 'No Content')}"
            for result in search_results
        ])
        
        # 2. Bedrock을 사용하여 응답 생성
        llm_response = generate_text_with_bedrock(
            prompt=user_query,
            context_text=context_text,
            trace_id=trace_id
        )
        
        # 결과 반환
        return {
            'query': user_query,
            'search_results': search_results,
            'llm_response': llm_response,
            'trace_id': trace_id
        }
        
    except Exception as e:
        # 트랜잭션에 오류 기록
        if transaction:
            transaction.notice_error(error=e)
        raise

# 메인 실행 함수
def main():
    # New Relic 애플리케이션 초기화
    newrelic.agent.initialize('newrelic.ini')
    
    # 사용자 쿼리 설정
    user_query = "인공지능이란 무엇인가요?"
    
    # OpenSearch 설정
    opensearch_domain = "my-opensearch-domain.us-east-1.es.amazonaws.com"
    index_name = "knowledge-base"
    
    try:
        # RAG 워크플로우 실행
        result = rag_workflow(user_query, opensearch_domain, index_name)
        
        # 결과 출력
        print("\n===== RAG 워크플로우 결과 =====")
        print(f"사용자 질문: {result['query']}")
        print("\n검색 결과:")
        for i, item in enumerate(result['search_results'], 1):
            print(f"{i}. {item.get('title', 'No Title')}: {item.get('content', 'No Content')[:100]}...")
        
        print("\nLLM 응답:")
        print(result['llm_response'])
        print(f"\n트레이스 ID: {result['trace_id']}")
        print("이 트레이스 ID로 New Relic에서 전체 워크플로우를 조회할 수 있습니다.")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
    finally:
        # New Relic 에이전트 종료
        newrelic.agent.shutdown_agent()

if __name__ == "__main__":
    main() 