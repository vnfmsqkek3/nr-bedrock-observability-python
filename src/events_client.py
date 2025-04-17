import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
import newrelic.agent
from .event_types import EventData

logger = logging.getLogger(__name__)

class EventClientOptions:
    """
    New Relic 이벤트 클라이언트에 대한 옵션
    """
    def __init__(
        self,
        application_name: str,
        new_relic_api_key: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        self.application_name = application_name
        self.new_relic_api_key = new_relic_api_key
        self.host = host
        self.port = port

class BedrockEventClient:
    """
    New Relic에 AWS Bedrock 이벤트 데이터를 전송하는 클라이언트
    """
    def __init__(self, options: Union[EventClientOptions, Dict[str, Any]]):
        if isinstance(options, dict):
            if 'application_name' not in options:
                raise ValueError("application_name is required")
            self.options = EventClientOptions(
                application_name=options['application_name'],
                new_relic_api_key=options.get('new_relic_api_key'),
                host=options.get('host'),
                port=options.get('port')
            )
        else:
            self.options = options
            
        # 환경 변수에서 API 키 가져오기
        self.api_key = (
            self.options.new_relic_api_key or 
            os.environ.get('NEW_RELIC_LICENSE_KEY') or 
            os.environ.get('NEW_RELIC_INSERT_KEY')
        )
        
        if not self.api_key:
            raise ValueError("New Relic API Key wasn't found. Please provide it in options or set environment variables.")
            
        self.host = self.options.host or os.environ.get('EVENT_CLIENT_HOST')
        self.port = self.options.port
        
    def send(self, *event_data_list: EventData) -> None:
        """
        New Relic에 이벤트 데이터 전송
        """
        try:
            for event_data in event_data_list:
                # New Relic 에이전트를 통해 이벤트 기록
                event_dict = {
                    'eventType': event_data.event_type,
                    **event_data.attributes
                }
                
                # New Relic 에이전트에 사용자 지정 이벤트 기록
                newrelic.agent.record_custom_event(
                    event_data.event_type,
                    event_data.attributes
                )
                
                logger.debug(f"Sent event to New Relic: {json.dumps(event_dict)}")
                
        except Exception as e:
            logger.error(f"Error sending event to New Relic: {str(e)}")

def create_event_client(options: Union[EventClientOptions, Dict[str, Any]]) -> BedrockEventClient:
    """
    이벤트 클라이언트 생성
    """
    return BedrockEventClient(options) 