#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
사용자 응답 평가 예제

이 샘플은 AWS Bedrock API 호출 결과에 대한 사용자 평가를 수집하는 방법을 보여줍니다.
"""

import os
import json
import uuid
import boto3
import logging

from nr_bedrock_observability import (
    monitor_bedrock,
    create_response_evaluation_collector
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 메인 함수
def main():
    # 환경 변수에서 API 키 가져오기
    nr_api_key = os.environ.get('NEW_RELIC_API_KEY')
    if not nr_api_key:
        logger.warning("NEW_RELIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        nr_api_key = 'test-api-key'  # 테스트용 키
    
    # 애플리케이션 이름 설정
    application_name = "Bedrock-Response-Evaluation-Demo"
    
    # Bedrock 클라이언트 생성
    try:
        bedrock_client = boto3.client('bedrock-runtime')
    except Exception as e:
        logger.error(f"Bedrock 클라이언트 생성 중 오류: {str(e)}")
        return
    
    # 트레이스 ID 생성 (메시지 그룹 추적용)
    trace_id = str(uuid.uuid4())
    logger.info(f"트레이스 ID: {trace_id}")
    
    # Bedrock 클라이언트 모니터링 래핑
    monitored_client = monitor_bedrock(bedrock_client, {
        'application_name': application_name,
        'new_relic_api_key': nr_api_key,
        'trace_id': trace_id
    })
    
    # Bedrock API 호출
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"  # 사용할 모델 ID
    prompt = "인공지능의 역사에 대해 간략하게 설명해주세요."
    
    try:
        # API 호출 (Claude 3 Sonnet 모델 사용)
        response = monitored_client.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            })
        )
        
        # 응답 처리
        response_body = json.loads(response['body'].read().decode('utf-8'))
        result = response_body['content'][0]['text']
        
        logger.info("\n=== Bedrock 응답 ===\n")
        print(result)
        logger.info("\n===================\n")
        
        # 응답 평가 수집기 생성
        eval_collector = create_response_evaluation_collector(
            application_name=application_name,
            trace_id=trace_id
        )
        
        # 사용자로부터 평가 입력 받기
        print("\n응답에 대한 평가를 제공해주세요:")
        
        # 응답 평가 입력 받기
        while True:
            try:
                response_rating = int(input("응답 평가 (1-5): "))
                if 1 <= response_rating <= 5:
                    break
                print("1에서 5 사이의 값을 입력해주세요.")
            except ValueError:
                print("숫자를 입력해주세요.")
        
        # 만족도 카테고리 매핑
        satisfaction_map = {
            1: "very_dissatisfied",
            2: "dissatisfied",
            3: "neutral",
            4: "satisfied",
            5: "very_satisfied"
        }
        satisfaction_category = satisfaction_map[response_rating]
        
        # 추가 평가 입력 받기 (선택 사항)
        usefulness_rating = None
        accuracy_rating = None
        relevance_rating = None
        
        if input("추가 평가를 입력하시겠습니까? (y/n): ").lower() == 'y':
            try:
                usefulness_rating = int(input("유용성 평가 (1-5): "))
                accuracy_rating = int(input("정확성 평가 (1-5): "))
                relevance_rating = int(input("적절성 평가 (1-5): "))
            except ValueError:
                print("유효하지 않은 입력입니다. 기본 평가로 계속합니다.")
        
        # 피드백 메시지 입력 받기
        feedback_message = input("추가 의견 (선택사항): ")
        
        # 문제 해결 여부
        problem_solved_input = input("응답이 문제를 해결했나요? (y/n/p-부분적으로): ").lower()
        problem_solved = None
        if problem_solved_input == 'y':
            problem_solved = True
        elif problem_solved_input == 'n':
            problem_solved = False
        
        # 후속 조치 필요 여부
        needs_followup = input("추가 조치가 필요한가요? (y/n): ").lower() == 'y'
        
        # 평가 기록
        eval_collector.record_evaluation(
            response_rating=response_rating,
            satisfaction_category=satisfaction_category,
            usefulness_rating=usefulness_rating,
            accuracy_rating=accuracy_rating,
            relevance_rating=relevance_rating,
            feedback_message=feedback_message,
            problem_solved=problem_solved,
            needs_followup=needs_followup,
            source="cli_demo"
        )
        
        logger.info("사용자 응답 평가가 성공적으로 기록되었습니다.")
        
    except Exception as e:
        logger.error(f"API 호출 또는 평가 기록 중 오류: {str(e)}")

if __name__ == "__main__":
    main() 