from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class ProposalRequest(BaseModel):
    공고일련번호: int
    기업명: str
    주소: str
    사업분야: List[str]
    회사소개서: Optional[str] = None

class ProposalResponse(BaseModel):
    공고일련번호: int
    공고제목: str
    제안서내용: str
    생성일자: date