from fastapi import APIRouter, HTTPException
from typing import List
import logging
from datetime import datetime
from ...models.recommendation import RecommendationRequest, RecommendationResponse, RecommendationItem
from ...services.recommendation_service import RecommendationService
import os

logger = logging.getLogger(__name__)
router = APIRouter()
recommendation_service = RecommendationService()

@router.post("/recommendations/", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """공고 추천 API"""
    try:
        logger.info(f"추천 요청 - 기업: {request.기업명}")
        
        # 회사소개서URL은 사용하지 않음 (자동으로 PDF 파일 찾기)
        recommendations = recommendation_service.get_recommendations(
            company_name=request.기업명,
            company_address=request.주소,
            business_fields=request.사업분야
        )
        
        return RecommendationResponse(
            recommendations=[
                RecommendationItem(
                    추천순위=idx + 1,
                    공고일련번호=rec['announcement_id'],
                    공고제목=rec['title'],
                    공고URL=rec['url'],
                    추천사유=rec['reason'],
                    추천일자=datetime.now().date()
                )
                for idx, rec in enumerate(recommendations)
            ]
        )

    except Exception as e:
        logger.error(f"추천 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))