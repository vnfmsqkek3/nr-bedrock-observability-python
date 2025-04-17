"""
AWS Bedrock 모니터링 데모 애플리케이션

이 스크립트는 AWS Bedrock API를 호출하고 New Relic에 모니터링 데이터를 전송하는 예제입니다.
실행하기 전에 환경 변수를 설정하거나 코드를 직접 수정해야 합니다.
"""

import os
import json
import sys
import boto3
from dotenv import load_dotenv

# 프로젝트 루트 디렉토리 추가 (로컬 테스트용)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 환경 변수 로드
load_dotenv()

# 라이브러리 임포트
from src import monitor_bedrock

# AWS 자격 증명은 환경 변수나 AWS 설정 파일에서 가져옵니다
NEW_RELIC_API_KEY = os.getenv('NEW_RELIC_API_KEY')

# Bedrock 클라이언트 생성
bedrock_client = boto3.client('bedrock-runtime')

# 모니터링 설정
monitor_bedrock(bedrock_client, {
    'application_name': 'Bedrock Demo',
    'new_relic_api_key': NEW_RELIC_API_KEY
})

def invoke_model_example():
    """
    Amazon Titan 모델을 사용한 텍스트 생성 예제
    """
    try:
        response = bedrock_client.invoke_model(
            modelId='amazon.titan-text-express-v1',
            body=json.dumps({
                'inputText': 'What is observability?',
                'textGenerationConfig': {
                    'maxTokenCount': 512,
                    'temperature': 0.7,
                    'topP': 0.9
                }
            })
        )
        
        # 응답 본문 읽기
        response_body = json.loads(response['body'].read())
        output_text = response_body['results'][0]['outputText']
        
        print("\n=== invoke_model 결과 ===")
        print(f"응답: {output_text}")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")

def converse_example():
    """
    Bedrock converse API를 사용한 대화 예제
    """
    try:
        response = bedrock_client.converse(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            messages=[
                {
                    'role': 'user',
                    'content': [{'text': 'What is the difference between monitoring and observability?'}]
                }
            ],
            inferenceConfig={
                'maxTokens': 500,
                'temperature': 0.7,
                'topP': 0.9
            }
        )
        
        # 응답 추출
        output_message = response['output']['message']
        output_text = output_message['content'][0]['text']
        
        print("\n=== converse 결과 ===")
        print(f"응답: {output_text}")
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")

if __name__ == "__main__":
    print("AWS Bedrock 모니터링 데모 시작...\n")
    
    # invoke_model 예제 실행
    invoke_model_example()
    
    # converse 예제 실행 (Claude 모델 필요)
    converse_example()
    
    print("\n데모 완료!") 