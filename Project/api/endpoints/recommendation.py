from fastapi import APIRouter, HTTPException
from typing import List
import logging
from datetime import datetime
from ...models.recommendation import RecommendationRequest, RecommendationResponse, RecommendationItem
from ...services.recommendation_engine import RecommendationEngine
from ...database.database import Database

router = APIRouter()
recommendation_engine = RecommendationEngine()
db = Database()

@router.post("/recommendations/", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """공고 추천 API"""
    try:
        # DB 연결
        connection = await db.connect()
        if not connection:
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")

        cursor = connection.cursor(dictionary=True)
        
        # 활성 공고 조회
        cursor.execute("""
            SELECT ID, TITLE, LOCATION, CATEGORY, CONTENT, START, END, LINK
            FROM Crawler
            WHERE END >= CURRENT_DATE OR END IN ('예산 소진시', '예산 소진시까지', '상시')
        """)
        
        announcements = cursor.fetchall()
        
        # 추천 실행
        recommendations = recommendation_engine.recommend(
            company_info={
                '주소': request.주소,
                '사업분야': request.사업분야,
                '회사소개서': request.회사소개서URL
            },
            announcements=announcements
        )
        
        # 응답 생성
        return RecommendationResponse(
            recommendations=[
                RecommendationItem(
                    추천순위=idx + 1,
                    공고일련번호=rec['announcement']['ID'],
                    공고제목=rec['announcement']['TITLE'],
                    공고URL=rec['announcement']['LINK'],
                    추천사유=rec['reason'],
                    추천일자=datetime.now().date()
                )
                for idx, rec in enumerate(recommendations)
            ]
        )

    except Exception as e:
        logging.error(f"추천 처리 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if 'cursor' in locals():
            cursor.close()