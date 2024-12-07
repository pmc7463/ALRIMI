from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import StreamingResponse
import logging
from ...models.proposal import ProposalResponse
from ...database.database import Database
from datetime import datetime
import os
import json
from typing import AsyncGenerator
from ..nodes.loader_node import pyMuPDF_loader_node
from ..nodes.ocr_node import python_tessorect_ocr_node
from ..nodes.retriever_node import vector_direct_retriever_node
#from ..nodes.llm_answer_node import proposal_maker_node
from ...graph_definition import GraphState
from ..nodes.llm_answer_node import proposal_maker_node_stream
from ...graph_definition import GraphState


logger = logging.getLogger(__name__)
router = APIRouter()
db = Database()

INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "Inputs")

async def generate_proposal_stream(
    pdf_path: str,
    company_name: str,
    business_fields: list[str],
    announcement_title: str,
    announcement_content: str,
    announcement_url: str,  # URL 추가
    공고일련번호: int
) -> AsyncGenerator[str, None]:
    try:
        # 초기 메타데이터 전송 (제목 포함)
        metadata = {
            "type": "metadata",
            "company_name": company_name,
            "announcement_title": announcement_title,
            "url": announcement_url  # URL 추가
        }
        yield f"data: {json.dumps(metadata, ensure_ascii=False)}\n\n"

        # 파이프라인 준비단계
        initial_state = GraphState({
            "retriever": None,
            "question": "",
            "question_split_page": [],
            "context": [],
            "answer": "",
            "proposal_context": "",
            "main_filed": business_fields,
            "file_name": pdf_path,
            "file_type": "pdf",
            "announcement_title": announcement_title,
            "announcement_content": announcement_content
        })

        # PDF 처리 및 분석 단계
        loader_state = pyMuPDF_loader_node(initial_state)
        ocr_state = python_tessorect_ocr_node(loader_state)
        retriever_state = vector_direct_retriever_node(ocr_state)

        # 제안서 생성 (스트리밍)
        async for chunk in proposal_maker_node_stream(retriever_state):
            yield f"data: {json.dumps({'type': 'content', 'chunk': chunk}, ensure_ascii=False)}\n\n"

        # 완료 메시지
        yield "data: [DONE]\n\n"

    except Exception as e:
        error_msg = {
            "type": "error",
            "message": str(e)
        }
        yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"

@router.post("/proposals/")
async def create_proposal(
    공고일련번호: int = Form(...),
    기업명: str = Form(...),
    주소: str = Form(...),
    사업분야: str = Form(...)
):
    """제안서 생성 API - 스트리밍 응답"""
    try:
        logger.info(f"제안서 생성 요청 - 기업명: {기업명}, 공고번호: {공고일련번호}")
        
        # PDF 파일 경로 확인
        pdf_file = os.path.join(INPUT_DIR, f"{기업명}.pdf")
        if not os.path.exists(pdf_file):
            raise HTTPException(status_code=404, detail=f"회사소개서 파일을 찾을 수 없습니다: {기업명}.pdf")

        # DB 연결 및 공고 정보 조회
        connection = await db.connect()
        if not connection:
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")

        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT TITLE, CONTENT, LINK FROM Crawler WHERE ID = %s
        """, (공고일련번호,))
        
        announcement = cursor.fetchone()
        if not announcement:
            raise HTTPException(status_code=404, detail="해당 공고를 찾을 수 없습니다")

        # 스트리밍 응답 반환
        return StreamingResponse(
            generate_proposal_stream(
                pdf_path=pdf_file,
                company_name=기업명,
                business_fields=사업분야.split(','),
                announcement_title=announcement["TITLE"],
                announcement_content=announcement["CONTENT"],
                announcement_url=announcement["LINK"],
                공고일련번호=공고일련번호
            ),
            media_type="text/event-stream"
        )

    except Exception as e:
        logger.error(f"제안서 생성 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if 'cursor' in locals():
            cursor.close()