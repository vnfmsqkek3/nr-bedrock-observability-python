"""
RAG 워크플로우 트레이싱 기능 테스트
"""

import json
import uuid
from unittest import mock
import pytest

import boto3
import newrelic.agent

from samples.rag_workflow_tracing import (
    search_opensearch,
    generate_text_with_bedrock,
    rag_workflow,
    CustomFunctionTrace
)


@pytest.fixture
def mock_opensearch_client():
    """OpenSearch 클라이언트 모킹"""
    mock_client = mock.MagicMock()
    
    # 검색 결과 모킹
    mock_response = {
        'hits': {
            'hits': [
                {
                    '_source': {
                        'title': '테스트 제목',
                        'content': '테스트 내용입니다.'
                    },
                    '_score': 0.9
                }
            ],
            'total': {
                'value': 1
            }
        }
    }
    
    mock_client.search.return_value = mock_response
    
    with mock.patch('boto3.client', return_value=mock_client) as mock_boto:
        yield mock_client


@pytest.fixture
def mock_bedrock_client():
    """Bedrock 클라이언트 모킹"""
    mock_client = mock.MagicMock()
    
    # invoke_model 응답 모킹
    mock_response_body = {
        "content": [
            {
                "type": "text",
                "text": "모킹된 LLM 응답입니다."
            }
        ]
    }
    
    # body 객체 모킹
    mock_body = mock.MagicMock()
    mock_body.read.return_value = json.dumps(mock_response_body).encode('utf-8')
    
    # invoke_model 응답 모킹
    mock_client.invoke_model.return_value = {
        'body': mock_body,
        'ResponseMetadata': {
            'RequestId': 'mock-request-id',
            'HTTPStatusCode': 200
        }
    }
    
    with mock.patch('boto3.client', return_value=mock_client) as mock_boto:
        yield mock_client


@pytest.fixture
def mock_nr_transaction():
    """New Relic 트랜잭션 모킹"""
    mock_transaction = mock.MagicMock()
    # 속성을 딕셔너리로 저장
    mock_transaction.custom_attributes = {}
    
    # add_custom_attribute 메서드를 모킹
    def add_custom_attribute(key, value):
        mock_transaction.custom_attributes[key] = value
    
    mock_transaction.add_custom_attribute = mock.MagicMock(side_effect=add_custom_attribute)
    
    # mock_transaction.add_custom_attribute = mock.MagicMock()
    
    with mock.patch('newrelic.api.transaction.current_transaction', 
                   return_value=mock_transaction):
        yield mock_transaction


@pytest.fixture
def mock_nr_agent():
    """New Relic 에이전트 함수 모킹"""
    with mock.patch('newrelic.agent.add_custom_span_attribute') as mock_add_attr:
        with mock.patch('newrelic.agent.current_trace_id', 
                       return_value='mock-trace-id'):
            yield mock_add_attr


@pytest.fixture
def mock_monitor_bedrock():
    """nr_bedrock_observability.monitor_bedrock 모킹"""
    def mock_monitor(client, options):
        return client
    
    with mock.patch('samples.rag_workflow_tracing.monitor_bedrock', 
                   side_effect=mock_monitor) as mock_monitor:
        yield mock_monitor


def test_custom_function_trace():
    """CustomFunctionTrace 클래스 테스트"""
    with mock.patch('newrelic.agent.add_custom_span_attribute') as mock_add_attr:
        trace_id = str(uuid.uuid4())
        
        # CustomFunctionTrace 사용
        with CustomFunctionTrace(name='test_span', trace_id=trace_id):
            pass
        
        # trace.id 속성이 추가되었는지 확인
        mock_add_attr.assert_called_with('trace.id', trace_id)


def test_search_opensearch(mock_opensearch_client, mock_nr_agent):
    """OpenSearch 검색 함수 테스트"""
    trace_id = str(uuid.uuid4())
    
    # 함수 호출
    results = search_opensearch(
        domain_endpoint='test-domain',
        index_name='test-index',
        query_text='테스트 쿼리',
        trace_id=trace_id
    )
    
    # 결과 확인
    assert isinstance(results, list)
    assert len(results) == 1
    assert 'title' in results[0]
    assert 'content' in results[0]
    
    # New Relic 속성이 추가되었는지 확인
    expected_calls = [
        mock.call('trace.id', trace_id),
        mock.call('openSearch.query', '테스트 쿼리'),
        mock.call('openSearch.index', 'test-index'),
        mock.call('rag.workflow', 'true'),
        mock.call('openSearch.resultsCount', 1)
    ]
    mock_nr_agent.assert_has_calls(expected_calls, any_order=True)


def test_generate_text_with_bedrock(mock_bedrock_client, mock_nr_agent, mock_monitor_bedrock):
    """Bedrock 텍스트 생성 함수 테스트"""
    trace_id = str(uuid.uuid4())
    
    # 함수 호출
    response = generate_text_with_bedrock(
        prompt='테스트 질문',
        context_text='테스트 컨텍스트',
        trace_id=trace_id
    )
    
    # 결과 확인
    assert isinstance(response, str)
    assert "모킹된 LLM 응답입니다." in response
    
    # New Relic 속성이 추가되었는지 확인
    expected_calls = [
        mock.call('trace.id', trace_id),
        mock.call('bedrock.model', 'anthropic.claude-3-sonnet-20240229-v1:0'),
        mock.call('rag.workflow', 'true')
    ]
    mock_nr_agent.assert_has_calls(expected_calls, any_order=True)
    
    # Bedrock 모델이 올바르게 호출되었는지 확인
    mock_bedrock_client.invoke_model.assert_called_once()
    args, kwargs = mock_bedrock_client.invoke_model.call_args
    assert kwargs['modelId'] == 'anthropic.claude-3-sonnet-20240229-v1:0'
    
    # monitor_bedrock이 호출되었는지 확인
    mock_monitor_bedrock.assert_called_once()


@mock.patch('samples.rag_workflow_tracing.search_opensearch')
@mock.patch('samples.rag_workflow_tracing.generate_text_with_bedrock')
def test_rag_workflow(mock_generate, mock_search, mock_nr_transaction, mock_nr_agent):
    """통합 RAG 워크플로우 테스트"""
    # 모킹된 함수의 반환값 설정
    mock_search.return_value = [
        {'title': '테스트 제목', 'content': '테스트 내용입니다.'}
    ]
    mock_generate.return_value = "모킹된 LLM 응답입니다."
    
    # 워크플로우 실행
    result = rag_workflow(
        user_query='테스트 질문',
        opensearch_domain='test-domain',
        index_name='test-index'
    )
    
    # 결과 확인
    assert isinstance(result, dict)
    assert 'query' in result
    assert 'search_results' in result
    assert 'llm_response' in result
    assert 'trace_id' in result
    assert result['query'] == '테스트 질문'
    assert result['llm_response'] == "모킹된 LLM 응답입니다."
    
    # 직접 add_custom_attribute 호출 여부 확인 대신
    # 속성이 추가되었는지 확인
    assert 'workflow.type' in mock_nr_transaction.custom_attributes
    assert mock_nr_transaction.custom_attributes['workflow.type'] == 'rag'
    assert 'user.query' in mock_nr_transaction.custom_attributes
    assert mock_nr_transaction.custom_attributes['user.query'] == '테스트 질문'
    
    # 함수가 올바르게 호출되었는지 확인
    mock_search.assert_called_once()
    mock_generate.assert_called_once()
    
    # 동일한 trace_id가 전달되었는지 확인
    search_args, search_kwargs = mock_search.call_args
    generate_args, generate_kwargs = mock_generate.call_args
    
    assert search_kwargs['trace_id'] == result['trace_id']
    assert generate_kwargs['trace_id'] == result['trace_id'] 