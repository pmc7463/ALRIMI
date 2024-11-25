from pydantic import BaseModel
from typing import List
from datetime import date

class RecommendationRequest(BaseModel):
    기업명: str
    주소: str
    사업분야: List[str]
    회사소개서URL: str

class RecommendationItem(BaseModel):
    추천순위: int
    공고일련번호: int
    공고제목: str
    공고URL: str
    추천사유: str
    추천일자: date

class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem]