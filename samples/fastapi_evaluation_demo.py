#!/usr/bin/env python3
"""
FastAPI를 사용한 웹 기반 모델 평가 수집 데모

이 스크립트는 FastAPI를 사용하여 모델 평가를 수집하고 NewRelic에 전송하는 방법을 보여줍니다.
"""

import os
import uuid
import time
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

# FastAPI 관련 임포트
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# NewRelic 라이브러리 임포트
from nr_bedrock_observability import (
    ResponseEvaluationCollector,
    create_response_evaluation_collector,
    EventType
)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API 키 설정 (실제 환경에서는 환경 변수나 보안 방식으로 관리)
API_KEY = os.environ.get("NEW_RELIC_LICENSE_KEY")
if not API_KEY:
    logger.warning("NEW_RELIC_LICENSE_KEY 환경 변수가 설정되지 않았습니다.")

# FastAPI 앱 초기화
app = FastAPI(
    title="모델 평가 API",
    description="모델 응답에 대한 사용자 평가를 수집하고 NewRelic에 전송하는 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 환경에서는 특정 도메인으로 제한하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 응답 평가 모델
class EvaluationRequest(BaseModel):
    model_id: str = Field(..., description="평가 대상 모델 ID")
    overall_score: int = Field(..., ge=1, le=10, description="전체 만족도 점수 (1-10)")
    relevance_score: Optional[int] = Field(None, ge=1, le=10, description="질문 관련성 점수 (1-10)")
    accuracy_score: Optional[int] = Field(None, ge=1, le=10, description="정확성 점수 (1-10)")
    completeness_score: Optional[int] = Field(None, ge=1, le=10, description="완성도 점수 (1-10)")
    coherence_score: Optional[int] = Field(None, ge=1, le=10, description="일관성 점수 (1-10)")
    helpfulness_score: Optional[int] = Field(None, ge=1, le=10, description="유용성 점수 (1-10)")
    response_time_score: Optional[int] = Field(None, ge=1, le=10, description="응답 속도 점수 (1-10)")
    feedback_comment: Optional[str] = Field(None, description="자유 형식 피드백 코멘트")
    query_type: Optional[str] = Field(None, description="질문 유형 (일반 지식, 창의적 생성 등)")
    domain: Optional[str] = Field(None, description="도메인 분야 (기술, 과학 등)")
    total_tokens: Optional[int] = Field(None, description="총 토큰 수")
    prompt_tokens: Optional[int] = Field(None, description="프롬프트 토큰 수")
    completion_tokens: Optional[int] = Field(None, description="완성 토큰 수")
    response_time_ms: Optional[int] = Field(None, description="응답 시간 (밀리초)")
    trace_id: Optional[str] = Field(None, description="트레이스 ID (없으면 자동 생성)")
    completion_id: Optional[str] = Field(None, description="완성 ID (없으면 자동 생성)")
    kb_id: Optional[str] = Field(None, description="지식 기반 ID")
    kb_name: Optional[str] = Field(None, description="지식 기반 이름")
    kb_used_in_query: Optional[bool] = Field(None, description="이 쿼리에서 지식 기반이 사용되었는지 여부")

class EvaluationResponse(BaseModel):
    id: str = Field(..., description="평가 ID")
    model_id: str = Field(..., description="평가 대상 모델 ID")
    overall_score: int = Field(..., description="전체 만족도 점수")
    trace_id: str = Field(..., description="트레이스 ID")
    timestamp: int = Field(..., description="타임스탬프 (밀리초)")
    message: str = Field(..., description="응답 메시지")

# 모델 평가 수집기 생성 함수
def get_evaluation_collector(trace_id: Optional[str] = None, completion_id: Optional[str] = None):
    """
    모델 평가 수집기 생성
    
    :param trace_id: 트레이스 ID (없으면 자동 생성)
    :param completion_id: 완성 ID (없으면 자동 생성)
    :return: 평가 수집기 인스턴스
    """
    # 애플리케이션 이름 설정
    app_name = "Bedrock-Evaluation-API"
    
    # 평가 수집기 생성
    return create_response_evaluation_collector(
        application_name=app_name,
        trace_id=trace_id,
        completion_id=completion_id
    )

# 루트 엔드포인트
@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "message": "모델 평가 API에 오신 것을 환영합니다.",
        "docs_url": "/docs",
        "version": "1.0.0"
    }

# 모델 평가 제출 엔드포인트
@app.post("/evaluations", response_model=EvaluationResponse)
async def submit_evaluation(evaluation: EvaluationRequest):
    """
    모델 평가 제출 엔드포인트
    
    이 엔드포인트는 모델 응답에 대한 사용자 평가를 수집하고 NewRelic에 전송합니다.
    필수 항목은 model_id와 overall_score이며, 선택적으로 세부 평가 항목을 추가할 수 있습니다.
    """
    try:
        # API 키 확인
        if not API_KEY:
            raise HTTPException(status_code=500, detail="NewRelic API 키가 설정되지 않았습니다.")
        
        # 트레이스 ID 및 완성 ID 설정
        trace_id = evaluation.trace_id or str(uuid.uuid4())
        completion_id = evaluation.completion_id or trace_id
        
        # 평가 수집기 생성
        collector = get_evaluation_collector(trace_id, completion_id)
        
        # 평가 데이터 추출
        eval_data = evaluation.dict(exclude_unset=True)
        
        # trace_id와 completion_id는 수집기 초기화에 사용되었으므로 제거
        if 'trace_id' in eval_data:
            del eval_data['trace_id']
        if 'completion_id' in eval_data:
            del eval_data['completion_id']
        
        # 평가 기록 및 NewRelic에 전송
        result = collector.record_evaluation(**eval_data)
        
        logger.info(f"모델 평가가 성공적으로 전송되었습니다: {result.get('id')}")
        
        # 응답 생성
        return {
            "id": result.get("id"),
            "model_id": result.get("model_id"),
            "overall_score": result.get("overall_score"),
            "trace_id": result.get("trace_id"),
            "timestamp": result.get("timestamp"),
            "message": "모델 평가가 성공적으로 제출되었습니다."
        }
        
    except Exception as e:
        logger.error(f"평가 제출 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"평가 제출 중 오류가 발생했습니다: {str(e)}")

# 최근 평가 조회 엔드포인트 (가상 데이터 - 실제로는 데이터베이스나 NewRelic API에서 조회)
@app.get("/evaluations/recent", response_model=List[EvaluationResponse])
async def get_recent_evaluations(limit: int = Query(10, ge=1, le=100)):
    """
    최근 평가 조회 엔드포인트 (예제 용도)
    
    실제 구현에서는 데이터베이스나 NewRelic API를 사용하여 최근 평가를 조회합니다.
    이 예제에서는 가상 데이터를 반환합니다.
    """
    # 가상 데이터 생성 (예제 용도)
    evaluations = []
    for i in range(limit):
        evaluations.append({
            "id": str(uuid.uuid4()),
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "overall_score": 8,
            "trace_id": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000) - i * 60000,  # 1분 간격으로 과거 데이터
            "message": "이것은 가상 데이터입니다. 실제 구현에서는 데이터베이스나 NewRelic API를 사용하세요."
        })
    
    return evaluations

# NRQL 쿼리 예제 엔드포인트
@app.get("/evaluations/nrql-examples")
async def get_nrql_examples():
    """
    NewRelic NRQL 쿼리 예제 제공
    """
    return {
        "queries": [
            {
                "description": "모든 평가 조회",
                "query": f"FROM {EventType.LLM_USER_RESPONSE_EVALUATION} SELECT * SINCE 1 DAY AGO LIMIT 100"
            },
            {
                "description": "모델별 평균 점수",
                "query": f"FROM {EventType.LLM_USER_RESPONSE_EVALUATION} SELECT average(overall_score) FACET model_id SINCE 1 WEEK AGO"
            },
            {
                "description": "시간대별 평가 추이",
                "query": f"FROM {EventType.LLM_USER_RESPONSE_EVALUATION} SELECT average(overall_score) TIMESERIES SINCE 1 WEEK AGO"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    # 서버 실행
    print("모델 평가 API 서버 시작...")
    print("API 문서: http://localhost:8000/docs")
    
    # Uvicorn 서버 실행
    uvicorn.run(app, host="0.0.0.0", port=8000) 