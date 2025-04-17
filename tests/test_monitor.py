import pytest
from unittest.mock import MagicMock, patch
import boto3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import monitor_bedrock

class TestMonitorBedrock:
    def test_monitor_bedrock_basic(self):
        # Create a mock Bedrock client
        mock_client = MagicMock()
        mock_client._client_config = MagicMock()
        
        # Set up basic attributes for testing
        mock_client.invoke_model = MagicMock()
        mock_client.converse = MagicMock()
        
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
            assert patched_client.invoke_model != mock_client.invoke_model
            assert patched_client.converse != mock_client.converse
            
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
            
    @patch('src.events_client.create_event_client')
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