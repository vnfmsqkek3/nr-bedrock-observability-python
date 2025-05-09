#!/usr/bin/env python3
"""
일반 프레임워크에서 모델 평가를 수집하는 데모 스크립트

이 스크립트는 프레임워크에 관계없이 모델 평가를 수집하고 NewRelic에 전송하는 방법을 보여줍니다.
"""

import os
import uuid
import logging
from typing import Dict, Any, Optional

# NewRelic 라이브러리 import
from nr_bedrock_observability import (
    ResponseEvaluationCollector,
    create_response_evaluation_collector,
    EventType
)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EvaluationExample:
    """
    모델 응답 평가를 수집하는 예제 클래스
    이 클래스는 어떤 프레임워크에서도 사용할 수 있는 방식으로 평가를 수집합니다.
    """
    def __init__(self, application_name: str, api_key: Optional[str] = None):
        """
        평가 수집기 초기화
        
        :param application_name: 애플리케이션 이름
        :param api_key: NewRelic API 키 (없으면 환경 변수에서 가져옴)
        """
        # API 키 설정
        if api_key:
            os.environ['NEW_RELIC_LICENSE_KEY'] = api_key
        
        # 트레이스/세션 ID 생성
        self.trace_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        
        # 평가 수집기 생성
        self.eval_collector = create_response_evaluation_collector(
            application_name=application_name,
            trace_id=self.trace_id,
            session_id=self.session_id
        )
        
        logger.info(f"모델 평가 수집기 초기화 완료: trace_id={self.trace_id}, session_id={self.session_id}")
    
    def collect_evaluation(self, model_id: str, evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        모델 평가 데이터 수집 및 NewRelic에 전송
        
        :param model_id: 평가 대상 모델 ID
        :param evaluation_data: 평가 데이터 (점수 등)
        :return: 전송된 평가 데이터
        """
        # 기본 점수 설정 (없는 경우)
        overall_score = evaluation_data.get('overall_score', 5)
        
        # 선택적 평가 항목
        optional_params = {
            'relevance_score': evaluation_data.get('relevance_score'),
            'accuracy_score': evaluation_data.get('accuracy_score'),
            'completeness_score': evaluation_data.get('completeness_score'),
            'coherence_score': evaluation_data.get('coherence_score'),
            'helpfulness_score': evaluation_data.get('helpfulness_score'),
            'response_time_score': evaluation_data.get('response_time_score'),
            'feedback_comment': evaluation_data.get('feedback_comment'),
            'query_type': evaluation_data.get('query_type'),
            'domain': evaluation_data.get('domain'),
            'evaluator_type': evaluation_data.get('evaluator_type', 'end-user'),
            'evaluation_source': evaluation_data.get('evaluation_source', 'api')
        }
        
        # 토큰 사용량 정보 (있는 경우)
        if 'total_tokens' in evaluation_data:
            optional_params['total_tokens'] = evaluation_data['total_tokens']
        if 'prompt_tokens' in evaluation_data:
            optional_params['prompt_tokens'] = evaluation_data['prompt_tokens']
        if 'completion_tokens' in evaluation_data:
            optional_params['completion_tokens'] = evaluation_data['completion_tokens']
        
        # KB 정보 (있는 경우)
        if 'kb_id' in evaluation_data:
            optional_params['kb_id'] = evaluation_data['kb_id']
        if 'kb_name' in evaluation_data:
            optional_params['kb_name'] = evaluation_data['kb_name']
        if 'kb_used_in_query' in evaluation_data:
            optional_params['kb_used_in_query'] = evaluation_data['kb_used_in_query']
        
        # 응답 시간 (있는 경우)
        if 'response_time_ms' in evaluation_data:
            optional_params['response_time_ms'] = evaluation_data['response_time_ms']
        
        try:
            # 평가 기록 및 NewRelic에 전송
            result = self.eval_collector.record_evaluation(
                model_id=model_id,
                overall_score=overall_score,
                **optional_params
            )
            
            logger.info(f"모델 평가가 성공적으로 전송되었습니다: {result.get('id')}")
            return result
        
        except Exception as e:
            logger.error(f"평가 전송 중 오류: {e}")
            raise

def main():
    """메인 함수 - 예제 실행"""
    # 환경 변수에서 API 키 가져오기
    nr_api_key = os.environ.get('NEW_RELIC_API_KEY')
    
    if not nr_api_key:
        logger.warning("NEW_RELIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        nr_api_key = input("NewRelic API 키를 입력하세요: ")
    
    # 애플리케이션 이름 설정
    app_name = "Bedrock-Evaluation-Demo"
    
    # 평가 예제 클래스 초기화
    example = EvaluationExample(application_name=app_name, api_key=nr_api_key)
    
    try:
        # 대화 시나리오 시뮬레이션
        print("\n=== 모델 응답 평가 데모 ===")
        
        # 모델 ID 설정
        model_id = input("평가할 모델 ID (예: anthropic.claude-3-sonnet-20240229-v1:0): ")
        model_id = model_id.strip() or "anthropic.claude-3-sonnet-20240229-v1:0"
        
        # 응답 평가 수집
        print("\n모델 응답에 대한 평가를 입력해주세요 (1-10 척도)")
        
        try:
            overall_score = int(input("전체 만족도 (1-10): "))
            if not 1 <= overall_score <= 10:
                overall_score = 5
                print("유효하지 않은 점수입니다. 기본값 5로 설정합니다.")
        except ValueError:
            overall_score = 5
            print("유효하지 않은 입력입니다. 기본값 5로 설정합니다.")
        
        # 추가 평가 입력
        additional_ratings = {}
        if input("\n추가 평가를 입력하시겠습니까? (y/n): ").lower() == 'y':
            try:
                additional_ratings['relevance_score'] = int(input("관련성 평가 (1-10): "))
                additional_ratings['accuracy_score'] = int(input("정확성 평가 (1-10): "))
                additional_ratings['completeness_score'] = int(input("완성도 평가 (1-10): "))
                additional_ratings['helpfulness_score'] = int(input("유용성 평가 (1-10): "))
            except ValueError:
                print("유효하지 않은 입력입니다. 추가 평가를 건너뜁니다.")
        
        # 피드백 메시지
        feedback_message = input("\n추가 의견 (선택사항): ")
        if feedback_message:
            additional_ratings['feedback_comment'] = feedback_message
        
        # 도메인 및 질문 유형
        query_types = ["일반 지식", "창의적 생성", "코딩/기술", "분석/추론", "기타"]
        print("\n질문 유형을 선택하세요:")
        for i, qt in enumerate(query_types):
            print(f"{i+1}. {qt}")
        
        try:
            qt_choice = int(input("번호 선택: "))
            if 1 <= qt_choice <= len(query_types):
                additional_ratings['query_type'] = query_types[qt_choice-1]
        except ValueError:
            print("유효하지 않은 선택입니다. 기본값으로 계속합니다.")
        
        domains = ["일반", "기술", "과학", "비즈니스", "예술", "기타"]
        print("\n도메인 분야를 선택하세요:")
        for i, domain in enumerate(domains):
            print(f"{i+1}. {domain}")
        
        try:
            domain_choice = int(input("번호 선택: "))
            if 1 <= domain_choice <= len(domains):
                additional_ratings['domain'] = domains[domain_choice-1]
        except ValueError:
            print("유효하지 않은 선택입니다. 기본값으로 계속합니다.")
        
        # 평가 데이터 종합
        evaluation_data = {
            'overall_score': overall_score,
            'evaluation_source': 'cli_demo',
            **additional_ratings
        }
        
        # 임의의 추가 정보 (실제 앱에서는 실제 데이터 사용)
        evaluation_data['total_tokens'] = 2500
        evaluation_data['prompt_tokens'] = 1500
        evaluation_data['completion_tokens'] = 1000
        evaluation_data['response_time_ms'] = 3500
        
        # 평가 전송
        print("\n평가 데이터 전송 중...")
        result = example.collect_evaluation(model_id, evaluation_data)
        
        print(f"\n평가가 성공적으로 전송되었습니다!")
        print(f"평가 ID: {result.get('id')}")
        print(f"평가 시간: {result.get('timestamp')}")
        
        # NewRelic NRQL 쿼리 안내
        print("\nNewRelic NRQL 쿼리로 데이터 확인하기:")
        print(f"""
FROM {EventType.LLM_USER_RESPONSE_EVALUATION} SELECT * 
WHERE trace_id = '{example.trace_id}'
SINCE 1 HOUR AGO
        """)
        
    except Exception as e:
        logger.error(f"데모 실행 중 오류: {e}")
        print(f"\n오류가 발생했습니다: {e}")
        
    print("\n데모가 완료되었습니다.")

if __name__ == "__main__":
    main() 