import os
import json
import boto3
import time
import logging
import uuid
from botocore.config import Config
# 패키지 임포트
from nr_bedrock_observability import monitor_bedrock

# 로깅 설정 초기화 (제일 먼저 설정)
def setup_logging():
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 기존 핸들러 제거 (중복 로깅 방지)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 콘솔 핸들러 추가
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    root_logger.addHandler(console)
    
    # New Relic 관련 로거 설정
    nr_logger = logging.getLogger('newrelic')
    nr_logger.setLevel(logging.DEBUG)
    
    # nr_bedrock_observability 로거 설정
    nr_bedrock_logger = logging.getLogger('nr_bedrock_observability')
    nr_bedrock_logger.setLevel(logging.DEBUG)
    
    return root_logger

# 로깅 설정
logger = setup_logging()
logger.info("로깅 시스템 초기화 완료")

# New Relic 설정 확인
def check_newrelic_config():
    nr_config_file = os.environ.get('NEW_RELIC_CONFIG_FILE', '')
    nr_license_key = os.environ.get('NEW_RELIC_LICENSE_KEY', '')
    nr_app_name = os.environ.get('NEW_RELIC_APP_NAME', '')
    
    logger.info(f"New Relic 설정 확인:")
    logger.info(f"- 설정 파일: {nr_config_file}")
    logger.info(f"- 라이센스 키: {'설정됨' if nr_license_key else '설정되지 않음'}")
    logger.info(f"- 앱 이름: {nr_app_name if nr_app_name else '설정되지 않음'}")
    
    if os.environ.get('NEW_RELIC_CONFIG_FILE'):
        try:
            with open(os.environ.get('NEW_RELIC_CONFIG_FILE'), 'r') as f:
                logger.info("New Relic 설정 파일 내용:")
                for line in f.readlines():
                    if 'license_key' not in line and 'password' not in line:
                        logger.info(f"  {line.strip()}")
        except Exception as e:
            logger.error(f"설정 파일 읽기 오류: {str(e)}")
    
    return nr_license_key

# New Relic 키 설정 (디버깅을 위해 임시 테스트 키 사용)
NEW_RELIC_LICENSE_KEY = check_newrelic_config() or "test_license_key_for_debugging"

# New Relic 애플리케이션 설정
nr_application = None
try:
    # New Relic 에이전트 임포트
    import newrelic.agent
    
    # 앱 이름 설정
    app_name = os.environ.get('NEW_RELIC_APP_NAME') or 'Bedrock-Test-App'
    
    # 명시적으로 애플리케이션 초기화
    if not newrelic.agent.application():
        logger.info(f"New Relic 애플리케이션 초기화: {app_name}")
        try:
            # 애플리케이션 등록
            nr_application = newrelic.agent.register_application(
                name=app_name,
                license_key=NEW_RELIC_LICENSE_KEY,
                log_level='debug'
            )
            logger.info(f"New Relic 애플리케이션이 성공적으로 등록되었습니다. app_name={app_name}")
        except Exception as e:
            logger.error(f"New Relic 애플리케이션 등록 오류: {str(e)}")
    else:
        nr_application = newrelic.agent.application()
        logger.info(f"기존 New Relic 애플리케이션 사용: {nr_application}")
    
    # 에이전트 설정 출력
    logger.info(f"New Relic 에이전트 버전: {newrelic.version.version_string()}")
    logger.info(f"New Relic 에이전트 활성화 상태: {newrelic.agent.agent_instance() is not None}")
    
except ImportError:
    logger.warning("New Relic 에이전트가 설치되어 있지 않습니다.")
    nr_application = None
except Exception as e:
    logger.error(f"New Relic 에이전트 초기화 오류: {str(e)}")
    nr_application = None

# AWS Bedrock 클라이언트 설정
bedrock_region = "ap-northeast-2"  # 리전 필수 지정 (v0.3.0에서 강조)
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet
logger.info(f"리전: {bedrock_region}, 모델 ID: {model_id}")

# boto3 클라이언트 설정
boto_config = Config(
    retries = {
        'max_attempts': 3,
        'mode': 'standard'
    },
    connect_timeout=5,
    read_timeout=60
)

# Bedrock 런타임 클라이언트 초기화 (리전 필수 지정)
bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=bedrock_region,
    config=boto_config
)

# 커스텀 이벤트 리스너 클래스 정의
class EventLogger:
    def __init__(self, app=None):
        self.events = []
        self.app = app
    
    def log_event(self, event_type, attributes):
        logger.info(f"New Relic 이벤트 전송: {event_type}")
        logger.debug(f"이벤트 속성: {json.dumps(attributes, indent=2)}")
        self.events.append({"event_type": event_type, "attributes": attributes})
        
    def get_events(self):
        return self.events

# 이벤트 로거 초기화
event_logger = EventLogger(app=nr_application)

# New Relic 에이전트 커스텀 이벤트 기록 함수 패치
try:
    if nr_application and hasattr(newrelic.agent, 'record_custom_event'):
        original_record_custom_event = newrelic.agent.record_custom_event
        
        def custom_record_event(event_type, attributes, application=None):
            logger.info(f"New Relic 이벤트 감지: {event_type}")
            event_logger.log_event(event_type, attributes)
            # 명시적으로 애플리케이션 객체 전달
            return original_record_custom_event(event_type, attributes, application=nr_application)
        
        newrelic.agent.record_custom_event = custom_record_event
        logger.info("New Relic 커스텀 이벤트 로깅이 활성화되었습니다.")
except Exception as e:
    logger.error(f"New Relic 패치 오류: {str(e)}")

# New Relic 모니터링 설정 - 활성화
monitor_options = {
    'application_name': 'Bedrock-Claude-Test-Demo',
    'new_relic_api_key': NEW_RELIC_LICENSE_KEY,
    # v0.3.0 새 기능 사용
    'track_token_usage': True,           # 토큰 사용량 추적 (기본값: True)
    'disable_streaming_events': False,    # 스트리밍 이벤트 활성화 (기본값: False)
}

logger.info(f"New Relic 모니터링 초기화: {monitor_options}")
monitored_client = monitor_bedrock(bedrock_client, monitor_options)

# 트랜잭션 시작 함수
def start_transaction(name):
    transaction = None
    try:
        if nr_application:
            transaction_name = f"Python/{name}"
            logger.info(f"New Relic 트랜잭션 시작: {transaction_name}")
            transaction = newrelic.agent.BackgroundTask(nr_application, name=transaction_name)
            transaction.__enter__()
            logger.info("트랜잭션이 성공적으로 시작되었습니다.")
        else:
            logger.warning("New Relic 애플리케이션이 초기화되지 않아 트랜잭션을 시작할 수 없습니다.")
    except Exception as e:
        logger.error(f"트랜잭션 시작 오류: {str(e)}")
        transaction = None
    return transaction

# 트랜잭션 종료 함수
def end_transaction(transaction):
    try:
        if transaction:
            logger.info("New Relic 트랜잭션 종료")
            transaction.__exit__(None, None, None)
            logger.info("트랜잭션이 성공적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"트랜잭션 종료 오류: {str(e)}")

def test_chat_completion():
    """
    Claude 3.5 Sonnet을 사용한 채팅 완성 API 테스트
    이 함수는 README.md의 예제와 일관성을 유지합니다.
    """
    # 트랜잭션 시작
    transaction = start_transaction("test_chat_completion")
    
    try:
        # Claude 3.5 Sonnet 모델 요청 형식
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "한국의 역사에 대해 간략하게 설명해줘."
                        }
                    ]
                }
            ],
            "temperature": 0.7
        }
        
        logger.info("\n요청 내용:")
        logger.info(json.dumps(request_body, indent=2))
        
        # Bedrock API 호출 - monitored_client 사용 (New Relic에 데이터 전송)
        response = monitored_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # 응답 메타데이터 출력
        logger.info("\n응답 메타데이터:")
        logger.info(f"상태 코드: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}")
        logger.info(f"요청 ID: {response.get('ResponseMetadata', {}).get('RequestId')}")
        
        # 응답 본문 처리
        raw_response = response.get("body").read()
        response_body = json.loads(raw_response.decode("utf-8"))
        
        logger.info("\n응답 내용:")
        if "content" in response_body and len(response_body["content"]) > 0:
            for content_item in response_body["content"]:
                if content_item.get("type") == "text":
                    logger.info(content_item.get("text", ""))
        
        # 이벤트가 New Relic에 제대로 기록되었는지 확인
        # New Relic은 비동기적으로 이벤트를 처리하므로 잠시 대기
        time.sleep(1)
        
        # v0.3.0에서는 CommonSummaryAttributes 클래스를 사용해 표준화된 이벤트 데이터가 New Relic에 전송됩니다
        logger.info("\n이 요청은 New Relic에 다음 이벤트를 전송합니다:")
        logger.info("- LlmChatCompletionSummary: 채팅 완성 요약 정보")
        logger.info("- LlmChatCompletionMessage: 개별 메시지 정보")
        
        # 기록된 이벤트 확인
        logger.info(f"\n기록된 New Relic 이벤트: {len(event_logger.get_events())}개")
        for idx, event in enumerate(event_logger.get_events()):
            logger.info(f"{idx+1}. {event['event_type']}")
        
        return response_body
    
    except Exception as e:
        logger.error(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # 트랜잭션 종료
        end_transaction(transaction)

def test_streaming_completion():
    """
    스트리밍 응답 API 테스트 (v0.3.0에서 개선됨)
    """
    # 트랜잭션 시작
    transaction = start_transaction("test_streaming_completion")
    
    try:
        # Claude 3.5 Sonnet 모델 요청 형식 (스트리밍용)
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "구름에 대한 짧은 시를 써줘."
                        }
                    ]
                }
            ],
            "temperature": 0.7
            # stream 매개변수는 허용되지 않음
        }
        
        logger.info("\n스트리밍 요청 내용:")
        logger.info(json.dumps(request_body, indent=2))
        
        # 스트리밍 API 호출 - 엔드포인트 자체가 스트리밍을 처리
        stream_response = monitored_client.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        logger.info("\n스트리밍 응답:")
        full_response = ""
        
        # 스트리밍 청크 처리
        try:
            for event in stream_response['body']:
                # 디버깅을 위해 원시 청크 데이터 출력
                chunk_bytes = event['chunk']['bytes']
                chunk_str = chunk_bytes.decode('utf-8')
                logger.debug(f"\n[디버그] 원시 청크: {chunk_str[:100]}..." if len(chunk_str) > 100 else chunk_str)
                
                try:
                    chunk = json.loads(chunk_str)
                    logger.debug(f"[디버그] 청크 키: {list(chunk.keys())}")
                    
                    # 다양한 응답 형식 처리
                    if 'content' in chunk and len(chunk['content']) > 0:
                        for content_item in chunk['content']:
                            if content_item.get('type') == 'text':
                                chunk_text = content_item.get('text', '')
                                full_response += chunk_text
                                print(chunk_text, end='', flush=True)
                    elif 'completion' in chunk:
                        chunk_text = chunk['completion']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                    elif 'outputText' in chunk:
                        chunk_text = chunk['outputText']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                    elif 'delta' in chunk and 'text' in chunk['delta']:
                        chunk_text = chunk['delta']['text']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                except json.JSONDecodeError:
                    logger.warning(f"[경고] JSON 파싱 오류: {chunk_str}")
        except Exception as e:
            logger.warning(f"\n[경고] 스트리밍 처리 중 오류: {str(e)}")
        
        logger.info("\n\n스트리밍 완료!")
        
        # 기록된 이벤트 확인
        logger.info(f"\n기록된 New Relic 이벤트 (스트리밍 후): {len(event_logger.get_events())}개")
        for idx, event in enumerate(event_logger.get_events()):
            logger.info(f"{idx+1}. {event['event_type']}")
        
        return full_response
        
    except Exception as e:
        logger.error(f"\n스트리밍 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # 트랜잭션 종료
        end_transaction(transaction)


def main():
    # 메인 트랜잭션 시작
    transaction = start_transaction("main")
    
    try:
        logger.info("\n== AWS Bedrock API 테스트 (v0.3.0) ==")
        
        logger.info("\n1. 채팅 완성 테스트 시작...")
        chat_result = test_chat_completion()
        
        logger.info("\n2. 스트리밍 테스트 시작...")
        try:
            stream_result = test_streaming_completion()
        except Exception as e:
            logger.error(f"스트리밍 테스트를 건너뜁니다: {str(e)}")
        
        logger.info("\n테스트 완료!")
        logger.info(f"기록된 총 New Relic 이벤트: {len(event_logger.get_events())}개")
        for idx, event in enumerate(event_logger.get_events()):
            logger.info(f"{idx+1}. {event['event_type']}")
        
        logger.info("New Relic 대시보드에서 'LlmCompletion', 'LlmChatCompletionSummary', 'LlmChatCompletionMessage' 이벤트를 확인하세요.")
    
    finally:
        # 메인 트랜잭션 종료
        end_transaction(transaction)

if __name__ == "__main__":
    main()