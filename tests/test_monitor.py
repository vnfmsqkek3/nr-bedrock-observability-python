import pytest
from unittest.mock import MagicMock, patch
import boto3
import os
import copy

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.nr_bedrock_observability import monitor_bedrock

# 환경 변수로 설정 (코드에 직접 입력하지 않음)
os.environ["AWS_ACCESS_KEY_ID"] = "YOUR_ACCESS_KEY"  # 실행 시 직접 입력하세요
os.environ["AWS_SECRET_ACCESS_KEY"] = "YOUR_SECRET_KEY"  # 실행 시 직접 입력하세요
os.environ["NEW_RELIC_LICENSE_KEY"] = "YOUR_NEW_RELIC_KEY"  # New Relic 키 설정

# 또는 AWS 설정 파일 사용 (~/.aws/credentials)

class TestMonitorBedrock:
    def test_monitor_bedrock_basic(self):
        # Create a mock Bedrock client
        mock_client = MagicMock()
        mock_client._client_config = MagicMock()
        
        # Set up basic attributes for testing and store original references
        original_invoke_model = MagicMock()
        original_converse = MagicMock()
        
        mock_client.invoke_model = original_invoke_model
        mock_client.converse = original_converse
        
        # Configure options
        options = {
            'application_name': 'TestApp',
            'new_relic_api_key': 'test-key'
        }
        
        # Mock the New Relic agent
        with patch('newrelic.agent.record_custom_event', MagicMock()):
            # Call the monitor_bedrock function
            patched_client = monitor_bedrock(mock_client, options)
            
            # Assert that the client has been patched (references should be different)
            assert patched_client.invoke_model is not original_invoke_model
            assert patched_client.converse is not original_converse
            
            # Assert that the client itself was returned (object identity)
            assert patched_client is mock_client
            
    def test_monitor_bedrock_validates_options(self):
        # Create a mock Bedrock client
        mock_client = MagicMock()
        
        # Test with empty options
        with pytest.raises(ValueError, match="application_name is required"):
            monitor_bedrock(mock_client, {})
            
        # Test with None client
        with pytest.raises(ValueError, match="Bedrock client is missing"):
            monitor_bedrock(None, {'application_name': 'TestApp'})
            
    @patch('src.nr_bedrock_observability.monitor.create_event_client')
    def test_monitor_bedrock_creates_event_client(self, mock_create_event_client):
        # Create mock objects
        mock_client = MagicMock()
        mock_client._client_config = MagicMock()
        mock_client.invoke_model = MagicMock()
        mock_client.converse = MagicMock()
        
        mock_event_client = MagicMock()
        mock_create_event_client.return_value = mock_event_client
        
        # Call the function
        options = {'application_name': 'TestApp'}
        with patch('newrelic.agent.record_custom_event', MagicMock()):
            monitor_bedrock(mock_client, options)
            
        # Assert event client was created
        mock_create_event_client.assert_called_once()

# 테스트 실행 (CI에서만 수행)
if 'CI' in os.environ:
    bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
    monitored_client = monitor_bedrock(
        bedrock_client=bedrock_client,
        options={
            'application_name': 'TestBedrockApp'
        }
    )

# 제공된 showcase.py 파일을 수정하지 말고 그대로 실행하세요:
# python nr-bedrock-observability-python/tests/showcase.py 