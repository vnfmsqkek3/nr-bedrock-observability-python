import os
import json
import boto3
import time
from botocore.config import Config
# 패키지 임포트
from nr_bedrock_observability import monitor_bedrock

# 환경 변수 또는 직접 라이센스 키를 설정할 수 있습니다.
# API 키가 없어도 테스트용 키로 실행 가능 (v0.3.0 기능)
NEW_RELIC_LICENSE_KEY = os.environ.get("NEW_RELIC_LICENSE_KEY", "")

# AWS 자격 증명 출력
print("Access Key ID: ", os.environ.get("AWS_ACCESS_KEY_ID", "환경 변수 미설정")[-4:] if os.environ.get("AWS_ACCESS_KEY_ID") else "없음")
print("Secret Access Key: ", "설정됨" if os.environ.get("AWS_SECRET_ACCESS_KEY") else "없음")
print("Session Token: ", "설정됨" if os.environ.get("AWS_SESSION_TOKEN") else "없음")

# AWS Bedrock 클라이언트 설정
bedrock_region = "ap-northeast-2"  # 리전 필수 지정 (v0.3.0에서 강조)
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet
print(f"리전: {bedrock_region}, 모델 ID: {model_id}")

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

# New Relic 모니터링 설정 - 활성화
monitored_client = monitor_bedrock(bedrock_client, {
    'application_name': 'Bedrock-Claude-Test-Demo',
    'new_relic_api_key': NEW_RELIC_LICENSE_KEY,
    # v0.3.0 새 기능 사용
    'track_token_usage': True,           # 토큰 사용량 추적 (기본값: True)
    'disable_streaming_events': False,    # 스트리밍 이벤트 활성화 (기본값: False)
})

# 로깅 설정
def create_custom_logger():
    import logging
    logger = logging.getLogger('new_relic_monitor')
    logger.setLevel(logging.DEBUG)  # 더 상세한 로깅을 위해 DEBUG 레벨로 설정
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = create_custom_logger()

def test_chat_completion():
    """
    Claude 3.5 Sonnet을 사용한 채팅 완성 API 테스트
    이 함수는 README.md의 예제와 일관성을 유지합니다.
    """
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
        
        print("\n요청 내용:")
        print(json.dumps(request_body, indent=2))
        
        # Bedrock API 호출 - monitored_client 사용 (New Relic에 데이터 전송)
        response = monitored_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # 응답 메타데이터 출력
        print("\n응답 메타데이터:")
        print(f"상태 코드: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}")
        print(f"요청 ID: {response.get('ResponseMetadata', {}).get('RequestId')}")
        
        # 응답 본문 처리
        raw_response = response.get("body").read()
        response_body = json.loads(raw_response.decode("utf-8"))
        
        print("\n응답 내용:")
        if "content" in response_body and len(response_body["content"]) > 0:
            for content_item in response_body["content"]:
                if content_item.get("type") == "text":
                    print(content_item.get("text", ""))
        
        # v0.3.0에서는 CommonSummaryAttributes 클래스를 사용해 표준화된 이벤트 데이터가 New Relic에 전송됩니다
        print("\n이 요청은 New Relic에 다음 이벤트를 전송합니다:")
        print("- LlmChatCompletionSummary: 채팅 완성 요약 정보")
        print("- LlmChatCompletionMessage: 개별 메시지 정보")
        
        return response_body
    
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_streaming_completion():
    """
    스트리밍 응답 API 테스트 (v0.3.0에서 개선됨)
    """
    try:
        # Titan 모델 요청 형식 (스트리밍용)
        request_body = {
            'inputText': '구름에 대한 짧은 시를 써줘.',
            'textGenerationConfig': {
                'maxTokenCount': 512,
                'temperature': 0.7
            }
        }
        
        print("\n스트리밍 요청 내용:")
        print(json.dumps(request_body, indent=2))
        
        # 스트리밍 API 호출
        stream_response = monitored_client.invoke_model_with_response_stream(
            modelId="amazon.titan-text-express-v1",
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        print("\n스트리밍 응답:")
        full_response = ""
        
        # 스트리밍 청크 처리
        for event in stream_response['body']:
            chunk = json.loads(event['chunk']['bytes'].decode())
            if 'outputText' in chunk:
                chunk_text = chunk['outputText']
                full_response += chunk_text
                print(chunk_text, end='', flush=True)
        
        print("\n\n스트리밍 완료!")
        return full_response
        
    except Exception as e:
        print(f"\n스트리밍 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("\n== AWS Bedrock API 테스트 (v0.3.0) ==")
    
    print("\n1. 채팅 완성 테스트 시작...")
    chat_result = test_chat_completion()
    
    print("\n2. 스트리밍 테스트 시작...")
    try:
        stream_result = test_streaming_completion()
    except Exception as e:
        print(f"스트리밍 테스트를 건너뜁니다: {str(e)}")
    
    print("\n테스트 완료!")
    print("New Relic 대시보드에서 'LlmCompletion', 'LlmChatCompletionSummary', 'LlmChatCompletionMessage' 이벤트를 확인하세요.")

if __name__ == "__main__":
    main()