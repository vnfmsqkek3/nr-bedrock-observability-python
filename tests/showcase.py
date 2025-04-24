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
    nr_license_key = os.environ.get('NEW_RELIC_LICENSE_KEY', '4a6e9bc922c68a67a00e6929c0d281e6FFFFNRAL')
    nr_app_name = os.environ.get('NEW_RELIC_APP_NAME', 'tttest-bedrock-local')
    
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
    
    # 명시적으로 애플리케이션 초기화 (config_file 옵션 추가)
    logger.info(f"New Relic 애플리케이션 초기화 시도: {app_name}")
    
    # 먼저 전역 에이전트 초기화 시도
    try:
        newrelic.agent.initialize(
            config_file=os.environ.get('NEW_RELIC_CONFIG_FILE'),
            environment=os.environ.get('NEW_RELIC_ENVIRONMENT'),
            ignore_errors=True
        )
        logger.info("New Relic 에이전트 초기화 완료")
    except Exception as e:
        logger.warning(f"New Relic 에이전트 초기화 경고: {str(e)}")
    
    # 애플리케이션 등록 시도
    try:
        nr_application = newrelic.agent.register_application(
            name=app_name,
            license_key=NEW_RELIC_LICENSE_KEY,
            log_level='debug'
        )
        logger.info(f"New Relic 애플리케이션이 성공적으로 등록되었습니다: {nr_application}")
    except Exception as e:
        logger.error(f"New Relic 애플리케이션 등록 오류: {str(e)}")
        
        # 기존 애플리케이션 가져오기 시도
        try:
            nr_application = newrelic.agent.application()
            if nr_application:
                logger.info(f"기존 New Relic 애플리케이션 사용: {nr_application}")
            else:
                logger.warning("기존 New Relic 애플리케이션이 없습니다.")
        except Exception as inner_e:
            logger.error(f"기존 애플리케이션 가져오기 오류: {str(inner_e)}")
    
    # 에이전트 설정 출력
    logger.info(f"New Relic 에이전트 버전: {newrelic.version.version_string()}")
    logger.info(f"New Relic 에이전트 활성화 상태: {newrelic.agent.agent_instance() is not None}")
    logger.info(f"New Relic 애플리케이션 상태: {'초기화됨' if nr_application else '초기화되지 않음'}")
    
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
        logger.info(f"New Relic 이벤트 기록: {event_type}")
        logger.debug(f"이벤트 속성: {json.dumps(attributes, indent=2)}")
        self.events.append({"event_type": event_type, "attributes": attributes})
        
        # 이벤트를 직접 New Relic에 기록 시도
        try:
            if self.app:
                logger.debug(f"자체 New Relic 이벤트 직접 전송: {event_type}")
                import newrelic.agent
                newrelic.agent.record_custom_event(event_type, attributes, application=self.app)
        except Exception as e:
            logger.error(f"직접 New Relic 이벤트 기록 실패: {str(e)}")
        
    def get_events(self):
        return self.events

# 이벤트 로거 초기화 (애플리케이션이 초기화된 후에 설정)
# nr_application이 None일 수 있으므로 나중에 event_logger.app을 업데이트
event_logger = EventLogger(app=None)

# New Relic 에이전트 커스텀 이벤트 기록 함수 패치
try:
    import newrelic.agent
    if hasattr(newrelic.agent, 'record_custom_event'):
        logger.info("New Relic 커스텀 이벤트 기록 함수 패치 시작")
        original_record_custom_event = newrelic.agent.record_custom_event
        
        def custom_record_event(event_type, attributes, application=None):
            logger.info(f"패치된 New Relic 이벤트 감지: {event_type}")
            # 로컬 이벤트 로거에 기록
            event_logger.log_event(event_type, attributes)
            
            # 애플리케이션이 전달되지 않았다면 글로벌 nr_application 사용
            if application is None:
                application = nr_application
                logger.debug(f"글로벌 nr_application 사용: {application}")
            
            # 원본 함수 호출
            try:
                result = original_record_custom_event(event_type, attributes, application=application)
                logger.debug(f"원본 record_custom_event 호출 성공: {event_type}")
                return result
            except Exception as e:
                logger.error(f"원본 record_custom_event 호출 실패: {str(e)}")
                # 에러가 발생해도 진행
                return None
        
        # 함수 패치
        newrelic.agent.record_custom_event = custom_record_event
        logger.info("New Relic 커스텀 이벤트 로깅 함수가 성공적으로 패치되었습니다.")
    else:
        logger.warning("New Relic 에이전트에 record_custom_event 함수가 없습니다.")
except ImportError:
    logger.error("New Relic 에이전트를 임포트할 수 없어 이벤트 로깅 패치를 건너뜁니다.")
except Exception as e:
    logger.error(f"New Relic 패치 오류: {str(e)}")

# nr_application이 None인지 다시 확인
if nr_application is None:
    try:
        logger.warning("monitor_options 설정 전에 nr_application이 None입니다. 다시 초기화를 시도합니다.")
        # 애플리케이션 초기화 재시도
        app_name = os.environ.get('NEW_RELIC_APP_NAME') or 'Bedrock-Test-App'
        nr_application = newrelic.agent.register_application(
            name=app_name,
            license_key=NEW_RELIC_LICENSE_KEY,
            log_level='debug'
        )
        logger.info(f"New Relic 애플리케이션 초기화 재시도 결과: {nr_application}")
    except Exception as e:
        logger.error(f"New Relic 애플리케이션 재초기화 오류: {str(e)}")

# event_logger.app 업데이트
event_logger.app = nr_application
logger.info(f"event_logger.app 업데이트됨: {event_logger.app}")

# New Relic 모니터링 설정 - 활성화
monitor_options = {
    'application_name': 'Bedrock-Claude-Test-Demo',
    'new_relic_api_key': NEW_RELIC_LICENSE_KEY,
    # v0.3.0 새 기능 사용
    'track_token_usage': True,           # 토큰 사용량 추적 (기본값: True)
    'disable_streaming_events': False,    # 스트리밍 이벤트 활성화 (기본값: False)
    'application': nr_application,        # New Relic 애플리케이션 객체 전달
}

logger.info(f"New Relic 모니터링 초기화: {monitor_options}")

# monitor_bedrock 호출 전 테스트 이벤트 기록
try:
    if nr_application:
        test_event_data = {
            'monitor_test': True,
            'timestamp': time.time(),
            'test_id': str(uuid.uuid4())
        }
        logger.info("monitor_bedrock 호출 전 테스트 이벤트 기록 시도")
        newrelic.agent.record_custom_event(
            'PreMonitorTest', 
            test_event_data,
            application=nr_application
        )
        logger.info("테스트 이벤트 기록 성공")
    else:
        logger.warning("nr_application이 None이어서 테스트 이벤트를 기록할 수 없습니다.")
except Exception as e:
    logger.error(f"테스트 이벤트 기록 중 오류: {str(e)}")

# nr_application 객체를 직접 사용하도록 New Relic 함수 패치
try:
    # application 객체가 유효한지 확인
    if nr_application:
        logger.info("newrelic.agent.application 함수 패치 시도...")
        
        # 원본 함수 저장
        original_application = newrelic.agent.application
        
        def patched_application():
            """패치된 application 함수로 항상 nr_application 반환"""
            logger.debug(f"패치된 application 함수 호출됨, 반환: {nr_application}")
            return nr_application
        
        # 함수 패치
        newrelic.agent.application = patched_application
        logger.info("newrelic.agent.application 함수가 성공적으로 패치되었습니다.")
    else:
        logger.warning("nr_application이 None이어서 함수를 패치할 수 없습니다.")
except Exception as e:
    logger.error(f"New Relic 함수 패치 오류: {str(e)}")

# 모니터링된 클라이언트 초기화
monitored_client = monitor_bedrock(bedrock_client, monitor_options)

# 모니터링된 클라이언트가 제대로 패치되었는지 확인
logger.info(f"모니터링된 클라이언트 타입: {type(monitored_client)}")
logger.info(f"원본 클라이언트와 동일 여부: {monitored_client is bedrock_client}")

# monitor_bedrock 호출 후 테스트 이벤트 기록
try:
    if nr_application:
        test_event_data = {
            'monitor_test': True,
            'timestamp': time.time(),
            'test_id': str(uuid.uuid4()),
            'phase': 'after_monitor_bedrock'
        }
        logger.info("monitor_bedrock 호출 후 테스트 이벤트 기록 시도")
        newrelic.agent.record_custom_event(
            'PostMonitorTest', 
            test_event_data,
            application=nr_application
        )
        logger.info("테스트 이벤트 기록 성공")
    else:
        logger.warning("nr_application이 None이어서 테스트 이벤트를 기록할 수 없습니다.")
except Exception as e:
    logger.error(f"테스트 이벤트 기록 중 오류: {str(e)}")

# 트랜잭션 시작 함수
def start_transaction(name):
    transaction = None
    try:
        # 필요한 경우 nr_application 사용
        global nr_application  # 전역 변수 참조
        
        # nr_application이 None이면 다시 가져오기 시도
        if nr_application is None:
            logger.info("애플리케이션이 초기화되지 않음. 다시 가져오기 시도...")
            try:
                # 기존 애플리케이션 가져오기 시도
                nr_application = newrelic.agent.application()
                if nr_application:
                    logger.info(f"기존 애플리케이션 가져오기 성공: {nr_application}")
                else:
                    # 새 애플리케이션 생성 시도
                    app_name = os.environ.get('NEW_RELIC_APP_NAME') or 'Bedrock-Test-App'
                    nr_application = newrelic.agent.register_application(
                        name=app_name,
                        license_key=NEW_RELIC_LICENSE_KEY,
                        log_level='debug'
                    )
                    logger.info(f"새 애플리케이션 생성 성공: {nr_application}")
            except Exception as e:
                logger.error(f"애플리케이션 초기화 실패: {str(e)}")
        
        # 트랜잭션 시작
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
        # 함수 시작 시 테스트 이벤트 직접 기록
        try:
            logger.info("test_chat_completion 시작 이벤트 기록 시도")
            event_id = str(uuid.uuid4())
            test_event_data = {
                'function': 'test_chat_completion',
                'phase': 'start',
                'timestamp': time.time(),
                'test_id': str(uuid.uuid4()),
                'event_id': event_id
            }
            
            # 직접 record_custom_event 호출
            if nr_application:
                newrelic.agent.record_custom_event(
                    'TestChatCompletionStart', 
                    test_event_data,
                    application=nr_application
                )
                logger.info(f"시작 이벤트 기록 성공 (ID: {event_id})")
                
                # 이벤트 로거를 통한 기록도 시도
                event_logger.log_event('TestChatCompletionLogger', test_event_data)
            else:
                logger.warning("nr_application이 None이어서 시작 이벤트를 기록할 수 없습니다.")
        except Exception as e:
            logger.error(f"시작 이벤트 기록 중 오류: {str(e)}")

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
        
        # 요청 직전 이벤트 기록
        if nr_application:
            pre_request_event = {
                'function': 'test_chat_completion',
                'phase': 'pre_request',
                'model': model_id,
                'timestamp': time.time(),
                'raw_request': json.dumps(request_body)  # 전체 요청 본문 추가
            }
            newrelic.agent.record_custom_event('PreRequestEvent', pre_request_event, application=nr_application)
            logger.info("요청 직전 이벤트 기록")
        
        # Bedrock API 호출 - monitored_client 사용 (New Relic에 데이터 전송)
        response = monitored_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # 응답 후 이벤트 기록
        if nr_application:
            post_request_event = {
                'function': 'test_chat_completion',
                'phase': 'post_request',
                'model': model_id,
                'status_code': response.get('ResponseMetadata', {}).get('HTTPStatusCode'),
                'timestamp': time.time()
            }
            newrelic.agent.record_custom_event('PostRequestEvent', post_request_event, application=nr_application)
            logger.info("응답 후 이벤트 기록")
        
        # 응답 메타데이터 출력
        logger.info("\n응답 메타데이터:")
        logger.info(f"상태 코드: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}")
        logger.info(f"요청 ID: {response.get('ResponseMetadata', {}).get('RequestId')}")
        
        # 응답 본문 처리 개선
        response_body = None
        response_content = ""
        
        # 응답 본문 가져오기
        raw_response = None
        if "body" in response:
            try:
                # 응답 바디가 스트림일 경우 읽기
                raw_bytes = response.get("body").read()
                logger.info(f"응답 바디 크기: {len(raw_bytes)} 바이트")
                
                # 디버깅을 위해 원시 응답 내용 (50바이트) 출력
                preview_bytes = raw_bytes[:50]
                logger.info(f"응답 바이트 미리보기: {preview_bytes}")
                
                # 바이트를 문자열로 디코딩 시도
                try:
                    raw_response = raw_bytes.decode("utf-8")
                    logger.info(f"응답 텍스트 미리보기: {raw_response[:100]}")
                except UnicodeDecodeError:
                    logger.error("UTF-8 디코딩 실패, 다른 인코딩 시도")
                    # 다른 인코딩 시도
                    for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                        try:
                            raw_response = raw_bytes.decode(encoding)
                            logger.info(f"{encoding} 인코딩으로 디코딩 성공")
                            break
                        except UnicodeDecodeError:
                            continue
                
                # JSON 파싱 시도
                if raw_response:
                    try:
                        # 다양한 응답 형식 지원을 위한 JSON 파싱
                        response_body = json.loads(raw_response)
                        logger.info(f"JSON 파싱 성공, 키: {list(response_body.keys())}")
                        
                        # 응답 내용 추출 (여러 형식 지원)
                        logger.info("\n응답 내용:")
                        
                        # Claude 스타일 응답 (content 배열)
                        if "content" in response_body and isinstance(response_body["content"], list):
                            for content_item in response_body["content"]:
                                if content_item.get("type") == "text":
                                    content_text = content_item.get("text", "")
                                    response_content += content_text
                                    logger.info(content_text)
                        
                        # 단일 텍스트 응답
                        elif "completion" in response_body:
                            response_content = response_body["completion"]
                            logger.info(response_content)
                        
                        # 다른 형식 (텍스트 필드 찾기)
                        elif "text" in response_body:
                            response_content = response_body["text"]
                            logger.info(response_content)
                        
                        # 알 수 없는 형식
                        else:
                            logger.info(f"알 수 없는 응답 형식: {json.dumps(response_body, indent=2)[:500]}")
                            # 응답 전체를 문자열로 변환하여 사용
                            response_content = json.dumps(response_body)
                    
                    except json.JSONDecodeError as json_err:
                        logger.error(f"JSON 파싱 오류: {str(json_err)}")
                        logger.error(f"원본 응답 (일부): {raw_response[:500]}")
                        
                        # 원본 텍스트 응답을 그대로 사용
                        response_content = raw_response
                        
                        # 원본 응답의 형식이 텍스트일 수 있음 (JSON이 아닐 수 있음)
                        logger.warning("응답이 JSON 형식이 아닌 것 같습니다. 원본 텍스트를 사용합니다.")
                        
                        # 오류 이벤트 기록
                        if nr_application:
                            error_content_event = {
                                'model': model_id,
                                'error_type': 'JSONDecodeError',
                                'error_message': str(json_err),
                                'raw_content_sample': raw_response[:200],
                                'timestamp': time.time()
                            }
                            newrelic.agent.record_custom_event('RawContentError', error_content_event, application=nr_application)
                            logger.info("원본 응답 오류 이벤트 기록")
            except Exception as e:
                logger.error(f"응답 처리 중 예외 발생: {str(e)}")
                import traceback
                traceback.print_exc()
        else:
            logger.error("응답에 body 필드가 없습니다")
            
        # 원본 응답 내용이 없을 경우 대비
        if not response_content and raw_response:
            response_content = raw_response
            
        # 수동으로 LLM 완료 이벤트 기록 (응답 파싱 성공 여부와 무관하게)
        try:
            if nr_application:
                # 수동 LLM 이벤트 생성
                event_id = str(uuid.uuid4())
                manual_llm_event = {
                    'model': model_id,
                    'duration_ms': 0,  # 시간 측정 안함
                    'request_id': response.get('ResponseMetadata', {}).get('RequestId', ''),
                    'input_text': "한국의 역사에 대해 간략하게 설명해줘.",
                    'input_messages': json.dumps(request_body['messages']),  # 전체 메시지 구조 추가
                    'output_text': response_content[:500] if response_content else "(응답 없음)",  # 500자 제한
                    'status': 'success',
                    'source': 'manual_record',
                    'timestamp': time.time(),
                    'event_source': 'test_chat_completion',  # 소스 함수 추가
                    'prompt_type': 'korea_history',  # 프롬프트 식별자 추가
                    'event_id': event_id  # 고유 ID 추가
                }
                
                # 이벤트 기록 - 이름을 다시 ManualLlmCompletion으로 변경
                try:
                    newrelic.agent.record_custom_event('ManualLlmCompletion', manual_llm_event, application=nr_application)
                    logger.info(f"수동 LLM 완료 이벤트 기록 (ID: {event_id})")
                except Exception as e:
                    logger.error(f"수동 LLM 이벤트 기록 실패: {str(e)}")
        except Exception as e:
            logger.error(f"수동 LLM 이벤트 기록 중 오류: {str(e)}")
        
        # 이벤트가 New Relic에 제대로 기록되었는지 확인
        # New Relic은 비동기적으로 이벤트를 처리하므로 잠시 대기
        logger.info("이벤트 처리를 위해 1초 대기...")
        time.sleep(1)
        
        # v0.3.0에서는 CommonSummaryAttributes 클래스를 사용해 표준화된 이벤트 데이터가 New Relic에 전송됩니다
        logger.info("\n이 요청은 New Relic에 다음 이벤트를 전송합니다:")
        logger.info("- LlmChatCompletionSummary: 채팅 완성 요약 정보")
        logger.info("- LlmChatCompletionMessage: 개별 메시지 정보")
        
        # 기록된 이벤트 확인
        logger.info(f"\n기록된 New Relic 이벤트: {len(event_logger.get_events())}개")
        for idx, event in enumerate(event_logger.get_events()[-5:]):  # 마지막 5개만 표시
            logger.info(f"{idx+1}. {event['event_type']}: {json.dumps(event['attributes'])[0:100]}...")
        
        return response_body
    
    except Exception as e:
        logger.error(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 오류 이벤트 기록
        if nr_application:
            error_event = {
                'function': 'test_chat_completion',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'timestamp': time.time()
            }
            newrelic.agent.record_custom_event('ErrorEvent', error_event, application=nr_application)
            logger.info("오류 이벤트 기록")
        
        return None
    
    finally:
        # 함수 종료 이벤트 기록
        if nr_application:
            end_event = {
                'function': 'test_chat_completion',
                'phase': 'end',
                'timestamp': time.time()
            }
            newrelic.agent.record_custom_event('TestChatCompletionEnd', end_event, application=nr_application)
            logger.info("종료 이벤트 기록")
        
        # 트랜잭션 종료
        end_transaction(transaction)

def test_streaming_completion():
    """
    스트리밍 응답 API 테스트 (v0.3.0에서 개선됨)
    """
    # 트랜잭션 시작
    transaction = start_transaction("test_streaming_completion")
    
    try:
        # 함수 시작 시 테스트 이벤트 직접 기록
        try:
            logger.info("test_streaming_completion 시작 이벤트 기록 시도")
            event_id = str(uuid.uuid4())
            test_event_data = {
                'function': 'test_streaming_completion',
                'phase': 'start',
                'timestamp': time.time(),
                'test_id': str(uuid.uuid4()),
                'event_id': event_id
            }
            
            # 직접 record_custom_event 호출
            if nr_application:
                newrelic.agent.record_custom_event(
                    'TestStreamingStart', 
                    test_event_data,
                    application=nr_application
                )
                logger.info(f"스트리밍 시작 이벤트 기록 성공 (ID: {event_id})")
                
                # 이벤트 로거를 통한 기록도 시도
                event_logger.log_event('TestStreamingLogger', test_event_data)
            else:
                logger.warning("nr_application이 None이어서 스트리밍 시작 이벤트를 기록할 수 없습니다.")
        except Exception as e:
            logger.error(f"스트리밍 시작 이벤트 기록 중 오류: {str(e)}")

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
                            "text": "안녕?잘부탁해!."
                        }
                    ]
                }
            ],
            "temperature": 0.7
            # stream 매개변수는 허용되지 않음
        }
        
        logger.info("\n스트리밍 요청 내용:")
        logger.info(json.dumps(request_body, indent=2))
        
        # 요청 직전 이벤트 기록
        if nr_application:
            pre_request_event = {
                'function': 'test_streaming_completion',
                'phase': 'pre_request',
                'model': model_id,
                'timestamp': time.time(),
                'raw_request': json.dumps(request_body)  # 전체 요청 본문 추가
            }
            newrelic.agent.record_custom_event('PreStreamRequestEvent', pre_request_event, application=nr_application)
            logger.info("스트리밍 요청 직전 이벤트 기록")
        
        # 스트리밍 API 호출 - 엔드포인트 자체가 스트리밍을 처리
        stream_response = monitored_client.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # 응답 후 이벤트 기록
        if nr_application:
            post_request_event = {
                'function': 'test_streaming_completion',
                'phase': 'post_request',
                'model': model_id,
                'status': 'streaming_started',
                'timestamp': time.time()
            }
            newrelic.agent.record_custom_event('PostStreamRequestEvent', post_request_event, application=nr_application)
            logger.info("스트리밍 요청 후 이벤트 기록")
        
        logger.info("\n스트리밍 응답:")
        full_response = ""
        
        # 스트리밍 청크 처리
        try:
            chunk_count = 0
            for event in stream_response['body']:
                chunk_count += 1
                # 디버깅을 위해 원시 청크 데이터 출력
                chunk_bytes = event['chunk']['bytes']
                
                # 청크 바이트 정보 로깅
                logger.debug(f"\n[디버그] 청크 #{chunk_count} 크기: {len(chunk_bytes)} 바이트")
                
                # 바이트를 문자열로 디코딩 시도
                chunk_str = None
                try:
                    chunk_str = chunk_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    logger.warning("[경고] UTF-8 디코딩 실패, 다른 인코딩 시도")
                    # 다른 인코딩 시도
                    for encoding in ['latin1', 'cp1252', 'iso-8859-1']:
                        try:
                            chunk_str = chunk_bytes.decode(encoding)
                            logger.debug(f"[디버그] {encoding} 인코딩으로 디코딩 성공")
                            break
                        except UnicodeDecodeError:
                            continue
                
                if not chunk_str:
                    logger.warning("[경고] 청크를 디코딩할 수 없습니다. 건너뜁니다.")
                    continue
                
                logger.debug(f"[디버그] 청크 문자열 미리보기: {chunk_str[:50]}...")
                
                # JSON 파싱 시도
                try:
                    chunk = json.loads(chunk_str)
                    logger.debug(f"[디버그] 청크 JSON 파싱 성공, 키: {list(chunk.keys())}")
                    
                    # 다양한 응답 형식 처리
                    chunk_text = ""
                    
                    # Claude 스타일 응답 (content 배열)
                    if 'content' in chunk and isinstance(chunk['content'], list):
                        for content_item in chunk['content']:
                            if content_item.get('type') == 'text':
                                chunk_text = content_item.get('text', '')
                                full_response += chunk_text
                                print(chunk_text, end='', flush=True)
                    
                    # 단일 텍스트 응답
                    elif 'completion' in chunk:
                        chunk_text = chunk['completion']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                    
                    # 기타 텍스트 필드
                    elif 'outputText' in chunk:
                        chunk_text = chunk['outputText']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                    
                    # 델타 형식 (OpenAI 스타일)
                    elif 'delta' in chunk and 'text' in chunk['delta']:
                        chunk_text = chunk['delta']['text']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                        
                    # 다른 알려진 텍스트 필드 찾기
                    elif 'text' in chunk:
                        chunk_text = chunk['text']
                        full_response += chunk_text
                        print(chunk_text, end='', flush=True)
                    
                    # 알 수 없는 형식
                    else:
                        logger.debug(f"[디버그] 알 수 없는 청크 형식: {json.dumps(chunk)[:100]}...")
                        # 전체 청크를 출력 (응답으로 사용하지는 않음)
                        print(".", end='', flush=True)
                    
                    # 스트리밍 청크 이벤트 기록 (선택적)
                    if nr_application and chunk_text:
                        try:
                            chunk_event = {
                                'model': model_id,
                                'chunk_index': chunk_count,
                                'chunk_text': chunk_text[:100],  # 첫 100자만 기록
                                'timestamp': time.time()
                            }
                            newrelic.agent.record_custom_event('StreamChunk', chunk_event, application=nr_application)
                        except Exception as chunk_error:
                            logger.debug(f"[디버그] 청크 이벤트 기록 실패: {str(chunk_error)}")
                
                except json.JSONDecodeError:
                    logger.warning(f"[경고] JSON 파싱 오류, 원시 청크: {chunk_str[:100]}...")
                    # JSON이 아닌 경우 원시 청크를 그대로 사용
                    full_response += chunk_str
                    print(chunk_str, end='', flush=True)
        
        except Exception as e:
            logger.warning(f"\n[경고] 스트리밍 처리 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
        
        logger.info("\n\n스트리밍 완료!")
        
        # 수동으로 스트리밍 완료 이벤트 기록
        try:
            if nr_application:
                # 수동 스트리밍 완료 이벤트 생성
                event_id = str(uuid.uuid4())
                manual_streaming_event = {
                    'model': model_id,
                    'input_text': "안녕?잘부탁해!.",
                    'input_messages': json.dumps(request_body['messages']),  # 전체 메시지 구조 추가
                    'output_text': full_response[:500],  # 500자 제한
                    'status': 'success',
                    'source': 'manual_record',
                    'timestamp': time.time(),
                    'event_source': 'test_streaming_completion',  # 소스 함수 추가
                    'prompt_type': 'greeting',  # 프롬프트 식별자 추가
                    'event_id': event_id  # 고유 ID 추가
                }
                
                # 이벤트 기록
                try:
                    newrelic.agent.record_custom_event('ManualStreamingCompletion', manual_streaming_event, application=nr_application)
                    logger.info(f"수동 스트리밍 완료 이벤트 기록 (ID: {event_id})")
                except Exception as e:
                    logger.error(f"수동 스트리밍 이벤트 기록 실패: {str(e)}")
        except Exception as e:
            logger.error(f"수동 스트리밍 이벤트 기록 중 오류: {str(e)}")
        
        # 이벤트가 New Relic에 제대로 기록되었는지 확인
        # New Relic은 비동기적으로 이벤트를 처리하므로 잠시 대기
        logger.info("이벤트 처리를 위해 1초 대기...")
        time.sleep(1)
        
        # 기록된 이벤트 확인
        logger.info(f"\n기록된 New Relic 이벤트 (스트리밍 후): {len(event_logger.get_events())}개")
        for idx, event in enumerate(event_logger.get_events()[-5:]):  # 마지막 5개만 표시
            logger.info(f"{idx+1}. {event['event_type']}: {json.dumps(event['attributes'])[0:100]}...")
        
        return full_response
        
    except Exception as e:
        logger.error(f"\n스트리밍 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 오류 이벤트 기록
        if nr_application:
            error_event = {
                'function': 'test_streaming_completion',
                'error_type': type(e).__name__,
                'error_message': str(e),
                'timestamp': time.time()
            }
            newrelic.agent.record_custom_event('StreamingErrorEvent', error_event, application=nr_application)
            logger.info("스트리밍 오류 이벤트 기록")
        
        return None

    finally:
        # 함수 종료 이벤트 기록
        if nr_application:
            end_event = {
                'function': 'test_streaming_completion',
                'phase': 'end',
                'timestamp': time.time()
            }
            newrelic.agent.record_custom_event('TestStreamingEnd', end_event, application=nr_application)
            logger.info("스트리밍 종료 이벤트 기록")
        
        # 트랜잭션 종료
        end_transaction(transaction)

def main():
    # 메인 트랜잭션 시작
    transaction = start_transaction("main")
    
    try:
        logger.info("\n== AWS Bedrock API 테스트 (v0.3.0) ==")
        
        # 테스트 이벤트 직접 기록 (문제 진단용)
        try:
            logger.info("테스트 이벤트 직접 기록 시도...")
            # 직접 이벤트 기록 시도 1 - record_custom_event 함수 사용
            if nr_application:
                event_id = str(uuid.uuid4())
                newrelic.agent.record_custom_event(
                    'TestDirectEvent', 
                    {
                        'test_value': 'test_direct',
                        'timestamp': time.time(),
                        'event_id': event_id
                    },
                    application=nr_application
                )
                logger.info(f"테스트 이벤트 1 기록 완료 (ID: {event_id})")
                
                # 직접 이벤트 기록 시도 2 - 에이전트 사용
                agent = newrelic.agent.agent_instance()
                if agent:
                    event_id = str(uuid.uuid4())
                    agent.record_custom_event('TestAgentEvent', {
                        'source': 'agent_direct',
                        'timestamp': time.time(),
                        'event_id': event_id
                    })
                    logger.info(f"테스트 이벤트 2 기록 완료 (ID: {event_id})")
                else:
                    logger.warning("에이전트 인스턴스를 가져올 수 없음")
                
                # 직접 이벤트 로거 사용
                event_id = str(uuid.uuid4())
                event_logger.log_event('TestLoggerEvent', {
                    'source': 'event_logger',
                    'timestamp': time.time(),
                    'event_id': event_id
                })
                logger.info(f"테스트 이벤트 3 기록 완료 (ID: {event_id})")
            else:
                logger.warning("nr_application이 None이어서 테스트 이벤트를 기록할 수 없습니다.")
        except Exception as e:
            logger.error(f"테스트 이벤트 기록 중 오류 발생: {str(e)}")
        
        # 수동으로 한국어 역사 이벤트 기록 (API 호출 없이 테스트)
        try:
            if nr_application:
                history_id = str(uuid.uuid4())
                history_event = {
                    'model': model_id,
                    'input_text': "한국의 역사에 대해 간략하게 설명해줘.",
                    'input_messages': json.dumps([{"role": "user", "content": [{"type": "text", "text": "한국의 역사에 대해 간략하게 설명해줘."}]}]),
                    'output_text': "한국의 역사는 고조선부터 시작하여 삼국시대, 고려, 조선을 거쳐 현대에 이르기까지 5000년의 유구한 역사를 자랑합니다...",
                    'status': 'success',
                    'timestamp': time.time(),
                    'event_source': 'manual_test',
                    'prompt_type': 'korea_history',
                    'event_id': history_id
                }
                newrelic.agent.record_custom_event('KoreaHistoryCompletion', history_event, application=nr_application)
                logger.info(f"한국 역사 이벤트 수동 기록 (ID: {history_id})")
                
                # 이벤트 전송을 위해 3초 대기
                logger.info("이벤트 전송을 위해 3초 대기...")
                time.sleep(3)
                
                # 수동으로 인사말 이벤트 기록 (API 호출 없이 테스트)
                greeting_id = str(uuid.uuid4())
                greeting_event = {
                    'model': model_id,
                    'input_text': "안녕?잘부탁해!.",
                    'input_messages': json.dumps([{"role": "user", "content": [{"type": "text", "text": "안녕?잘부탁해!."}]}]),
                    'output_text': "안녕하세요! 반갑습니다. 무엇을 도와드릴까요?",
                    'status': 'success',
                    'timestamp': time.time(),
                    'event_source': 'manual_test',
                    'prompt_type': 'greeting',
                    'event_id': greeting_id
                }
                newrelic.agent.record_custom_event('GreetingCompletion', greeting_event, application=nr_application)
                logger.info(f"인사말 이벤트 수동 기록 (ID: {greeting_id})")
                
                # 이벤트 전송을 위해 다시 3초 대기
                logger.info("추가 이벤트 전송을 위해 3초 대기...")
                time.sleep(3)
        except Exception as e:
            logger.error(f"수동 이벤트 기록 중 오류: {str(e)}")
        
        logger.info("\n1. 채팅 완성 테스트 시작...")
        chat_result = test_chat_completion()
        
        # 첫 번째 테스트와 두 번째 테스트 사이에 지연 추가
        logger.info("\n첫 번째 테스트와 두 번째 테스트 사이에 10초 지연...")
        time.sleep(10)
        
        logger.info("\n2. 스트리밍 테스트 시작...")
        try:
            stream_result = test_streaming_completion()
        except Exception as e:
            logger.error(f"스트리밍 테스트를 건너뜁니다: {str(e)}")
        
        # 이벤트 전송을 위해 대기
        logger.info("\n이벤트 전송을 위해 5초 대기...")
        time.sleep(5)
        
        logger.info("\n테스트 완료!")
        
        # 기록된 이벤트 출력 (전체)
        logger.info(f"기록된 총 New Relic 이벤트: {len(event_logger.get_events())}개")
        for idx, event in enumerate(event_logger.get_events()[-5:]):  # 마지막 5개만 표시
            logger.info(f"{idx+1}. {event['event_type']}: {json.dumps(event['attributes'])[0:100]}...")
        
        # 채팅 완성 이벤트만 필터링하여 출력
        logger.info("\n채팅 완성 이벤트 (한국 역사):")
        chat_events = [event for event in event_logger.get_events() 
                       if (event['event_type'] in ['ManualLlmCompletion', 'KoreaHistoryCompletion'] and
                           'attributes' in event and
                           'prompt_type' in event['attributes'] and
                           event['attributes']['prompt_type'] == 'korea_history')]
        
        for idx, event in enumerate(chat_events):
            logger.info(f"{idx+1}. {event['event_type']}: {json.dumps(event['attributes'])[0:100]}...")
        
        # 스트리밍 이벤트만 필터링하여 출력
        logger.info("\n스트리밍 이벤트 (인사말):")
        streaming_events = [event for event in event_logger.get_events() 
                           if (event['event_type'] in ['ManualStreamingCompletion', 'GreetingCompletion'] and
                               'attributes' in event and
                               'prompt_type' in event['attributes'] and
                               event['attributes']['prompt_type'] == 'greeting')]
        
        for idx, event in enumerate(streaming_events):
            logger.info(f"{idx+1}. {event['event_type']}: {json.dumps(event['attributes'])[0:100]}...")
        
        logger.info("\nNew Relic 대시보드에서 'KoreaHistoryCompletion', 'GreetingCompletion', 'LlmCompletion' 이벤트를 확인하세요.")
    
    finally:
        # 메인 트랜잭션 종료
        end_transaction(transaction)

if __name__ == "__main__":
    main()