import os
import logging
import json
import time
from typing import Dict, Any, Optional, List, Union, Callable

try:
    import newrelic.agent
    NEWRELIC_AVAILABLE = True
except ImportError:
    NEWRELIC_AVAILABLE = False

from .event_types import EventData

logger = logging.getLogger(__name__)

class EventClientOptions:
    """
    이벤트 클라이언트 옵션
    """
    def __init__(
        self,
        application_name: Optional[str] = None,
        new_relic_api_key: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        self.application_name = application_name
        self.new_relic_api_key = new_relic_api_key
        self.host = host
        self.port = port

class BedrockEventClient:
    """
    New Relic에 Bedrock 이벤트 데이터 전송하는 클라이언트
    """
    def __init__(self, api_key: str, host: Optional[str] = None, port: Optional[int] = None):
        self.api_key = api_key
        self.host = host
        self.port = port
        self.event_queue: List[Dict[str, Any]] = []
        self._setup_newrelic_agent()

    def _setup_newrelic_agent(self) -> None:
        """
        뉴렐릭 에이전트 설정
        """
        if not NEWRELIC_AVAILABLE:
            logger.warning("New Relic Python Agent is not installed. Some functionality may be limited.")
            return
            
        try:
            # 에이전트 구성 업데이트 (필요한 경우)
            if self.host:
                newrelic.agent.global_settings().event_collector_host = self.host
            if self.port:
                newrelic.agent.global_settings().event_collector_port = self.port
        except Exception as e:
            logger.error(f"Failed to configure New Relic agent: {str(e)}")

    def send(self, event_data: EventData) -> None:
        """
        이벤트 데이터를 New Relic에 전송
        
        :param event_data: 전송할 이벤트 데이터
        """
        if not event_data:
            return
            
        try:
            event_type = event_data.get('eventType')
            attributes = event_data.get('attributes', {})
            
            if not event_type:
                logger.error("Event type is required")
                return
                
            if NEWRELIC_AVAILABLE:
                # New Relic Python Agent로 이벤트 직접 전송
                try:
                    # 애플리케이션 객체 가져오기
                    app = newrelic.agent.application()
                    if app:
                        # 트랜잭션 내에서 이벤트 기록
                        with newrelic.agent.BackgroundTask(app, name=f"EventRecording/{event_type}"):
                            newrelic.agent.record_custom_event(event_type, attributes, application=app)
                            logger.debug(f"Event sent to New Relic within transaction: {event_type}")
                    else:
                        # 애플리케이션 없이 기록 시도
                        newrelic.agent.record_custom_event(event_type, attributes)
                        logger.debug(f"Event sent to New Relic without application: {event_type}")
                except Exception as e:
                    logger.error(f"Error recording event with transaction: {str(e)}")
                    # 에러 발생 시 기본 방식으로 다시 시도
                    try:
                newrelic.agent.record_custom_event(event_type, attributes)
                        logger.debug(f"Event sent to New Relic using fallback: {event_type}")
                    except Exception as e2:
                        logger.error(f"Error recording event using fallback: {str(e2)}")
            else:
                # 에이전트 없이 사용 시 이벤트 대기열에 추가 (향후 구현)
                self.event_queue.append({
                    'eventType': event_type,
                    'attributes': attributes,
                    'timestamp': int(time.time() * 1000)
                })
                logger.debug(f"Event queued (New Relic agent not available): {event_type}")
        except Exception as e:
            logger.error(f"Error sending event to New Relic: {str(e)}")

def create_event_client(
    options: Union[EventClientOptions, Any] = None
) -> BedrockEventClient:
    """
    Bedrock 이벤트 클라이언트 생성
    
    :param options: 클라이언트 옵션
    :return: Bedrock 이벤트 클라이언트
    """
    # 환경 변수 확인
    environment = {
        'new_relic_api_key': os.environ.get('NEW_RELIC_LICENSE_KEY'),
        'insert_key': os.environ.get('NEW_RELIC_INSERT_KEY'),
        'host': os.environ.get('EVENT_CLIENT_HOST'),
    }

    # 옵션 처리
    if isinstance(options, dict):
        options_obj = EventClientOptions(
            application_name=options.get('application_name'),
            new_relic_api_key=options.get('new_relic_api_key'),
            host=options.get('host'),
            port=options.get('port')
        )
    elif hasattr(options, 'new_relic_api_key'):
        options_obj = options
    else:
        options_obj = EventClientOptions()

    # API 키 확인
    api_key = (
        options_obj.new_relic_api_key or
        environment['new_relic_api_key'] or
        environment['insert_key']
    )
    
    if not api_key:
        logger.warning("New Relic API Key wasn't found, using mock key for testing")
        api_key = "mock-key-for-testing"

    # 클라이언트 생성 및 반환
    return BedrockEventClient(
        api_key=api_key,
        host=options_obj.host or environment['host'],
        port=options_obj.port
    ) 