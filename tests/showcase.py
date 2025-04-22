import os
import json
import boto3
import time
from botocore.config import Config
# 이제 절대 경로로 임포트
from nr_bedrock_observability import monitor_bedrock

# 환경 변수 또는 직접 라이센스 키를 설정할 수 있습니다.
NEW_RELIC_LICENSE_KEY = os.environ.get("NEW_RELIC_LICENSE_KEY", "4a6e9bc922c68a67a00e6929c0d281e6FFFFNRAL")

# AWS 자격 증명 출력
print("Access Key ID: ", os.environ.get("AWS_ACCESS_KEY_ID", "환경 변수 미설정")[-4:] if os.environ.get("AWS_ACCESS_KEY_ID") else "없음")
print("Secret Access Key: ", "설정됨" if os.environ.get("AWS_SECRET_ACCESS_KEY") else "없음")
print("Session Token: ", "설정됨" if os.environ.get("AWS_SESSION_TOKEN") else "없음")

# AWS Bedrock 클라이언트 설정
bedrock_region = "ap-northeast-2"  # 서울 리전
# 다시 Claude 3.5 Sonnet 모델 사용
model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"  # Claude 3.5 Sonnet
print("리전: ", bedrock_region)
print("모델 ID: ", model_id)

# boto3 클라이언트 설정 - 디버깅용 로깅 추가
boto_config = Config(
    retries = {
        'max_attempts': 3,
        'mode': 'standard'
    },
    connect_timeout=5,
    read_timeout=60
)

# Bedrock 런타임 클라이언트 초기화
bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=bedrock_region,
    config=boto_config
)

#New Relic 모니터링 설정은 문제 해결을 위해 비활성화
monitored_client = monitor_bedrock(bedrock_client, {
    'application_name': 'Bedrock-Claude-Test-Local',
    'new_relic_api_key': NEW_RELIC_LICENSE_KEY,
})

def create_custom_logger():
    import logging
    logger = logging.getLogger('new_relic_monitor')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = create_custom_logger()

# 간소화된 자체 모니터링 함수 구현
def custom_monitor(func):
    def wrapper(*args, **kwargs):
        print(f"\n== API 호출: {func.__name__} ==")
        
        # 요청 정보 출력
        request_info = {}
        for i, arg in enumerate(args):
            request_info[f"arg_{i}"] = str(arg)[:100] + "..." if isinstance(arg, str) and len(str(arg)) > 100 else arg
        
        for key, value in kwargs.items():
            request_info[key] = str(value)[:100] + "..." if isinstance(value, str) and len(str(value)) > 100 else value
        
        print(f"요청 파라미터: {json.dumps(request_info, default=str)}")
        
        # 함수 호출
        try:
            start_time = time.time()
            response = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            print(f"응답 시간: {duration:.2f}ms")
            
            # 응답 메타데이터 출력
            if hasattr(response, 'get') and callable(response.get):
                metadata = response.get('ResponseMetadata', {})
                print(f"응답 메타데이터: {json.dumps(metadata, default=str)}")
            
            # 응답 본문 읽기 (StreamingBody를 위한 처리)
            if 'body' in response and hasattr(response['body'], 'read'):
                body_data = response['body'].read()
                print(f"응답 본문 크기: {len(body_data)} bytes")
                
                # JSON 파싱 시도
                try:
                    if body_data:
                        json_data = json.loads(body_data.decode('utf-8'))
                        print(f"응답 본문 (JSON): {json.dumps(json_data, indent=2)[:500]}..." if len(json.dumps(json_data)) > 500 else json.dumps(json_data, indent=2))
                    else:
                        print("응답 본문이 비어 있습니다.")
                except Exception as e:
                    print(f"응답 본문 파싱 오류: {str(e)}")
                    print(f"원시 응답 본문 (처음 200바이트): {body_data[:200]}")
                
                # StreamingBody 객체 재설정
                from io import BytesIO
                response['body'] = BytesIO(body_data)
            
            return response
            
        except Exception as e:
            print(f"API 호출 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    return wrapper

# 모니터링 패치 적용
bedrock_client.invoke_model = custom_monitor(bedrock_client.invoke_model)

def test_chat_completion():
    """
    채팅 완성 API를 테스트
    """
    try:
        # Claude 3.5 Sonnet 모델 요청 형식에 맞게 조정
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
        
        # Bedrock API 호출 - content_type과 accept 헤더 추가
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        # 응답 메타데이터 출력
        print("\n응답 메타데이터:")
        print(f"상태 코드: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}")
        print(f"요청 ID: {response.get('ResponseMetadata', {}).get('RequestId')}")
        
        # 원시 응답 본문 처리
        raw_response = response.get("body").read()
        
        # 응답이 비어있는지 확인
        if not raw_response:
            print("\n경고: 응답 본문이 비어 있습니다.")
            return None
        
        # 응답 처리 시도
        response_body = json.loads(raw_response.decode("utf-8"))
        print("\n응답 내용 (파싱 성공):")
        if "content" in response_body and len(response_body["content"]) > 0:
            for content_item in response_body["content"]:
                if content_item.get("type") == "text":
                    print(content_item.get("text", ""))
        else:
            print("응답에 content 필드가 없거나 비어 있습니다.")
            print("전체 응답 구조:")
            print(json.dumps(response_body, indent=2))
        
        return response_body
    
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("\n== Bedrock API 연결 테스트 ==")
    
    print("\n채팅 완성 테스트 시작...")
    chat_result = test_chat_completion()
    
    
    print("\n테스트 완료!")

if __name__ == "__main__":
    main()