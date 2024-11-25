from fastapi import APIRouter, HTTPException, Form
import logging
from ...models.proposal import ProposalResponse
from ...database.database import Database
from datetime import datetime
import os
from ..nodes.loader_node import pyMuPDF_loader_node
from ..nodes.ocr_node import python_tessorect_ocr_node
from ..nodes.retriever_node import vector_direct_retriever_node
from ..nodes.llm_answer_node import proposal_maker_node
from ...graph_definition import GraphState

logger = logging.getLogger(__name__)
router = APIRouter()
db = Database()

# Inputs 디렉토리 경로
INPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "Inputs")

async def process_proposal_pipeline(
    pdf_path: str,
    company_name: str,
    business_fields: list[str],
    announcement_title: str,
    announcement_content: str
) -> str:
    """제안서 생성 파이프라인 실행"""
    try:
        logger.info(f"Starting pipeline with file: {pdf_path}")
        
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
        
        logger.info("PDF 로드 시작")
        loader_state = pyMuPDF_loader_node(initial_state)
        
        logger.info("OCR 처리 시작")
        ocr_state = python_tessorect_ocr_node(loader_state)
        
        logger.info("벡터 검색 시작")
        retriever_state = vector_direct_retriever_node(ocr_state)
        
        logger.info("제안서 생성 시작")
        final_state = proposal_maker_node(retriever_state)
        
        return final_state["proposal_context"]

    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}")
        raise

@router.post("/proposals/", response_model=ProposalResponse)
async def create_proposal(
    공고일련번호: int = Form(...),
    기업명: str = Form(...),
    주소: str = Form(...),
    사업분야: str = Form(...)
):
    """제안서 생성 API"""
    try:
        logger.info(f"제안서 생성 요청 - 기업명: {기업명}, 공고번호: {공고일련번호}")
        
        # PDF 파일 경로 확인
        pdf_file = os.path.join(INPUT_DIR, f"{기업명}.pdf")
        if not os.path.exists(pdf_file):
            logger.error(f"회사소개서 파일을 찾을 수 없음: {pdf_file}")
            raise HTTPException(status_code=404, detail=f"회사소개서 파일을 찾을 수 없습니다: {기업명}.pdf")

        # DB에서 공고 정보 조회
        connection = await db.connect()
        if not connection:
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")

        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT TITLE, CONTENT FROM Crawler WHERE ID = %s
        """, (공고일련번호,))
        
        announcement = cursor.fetchone()
        if not announcement:
            raise HTTPException(status_code=404, detail="해당 공고를 찾을 수 없습니다")

        # 파이프라인 실행
        try:
            proposal_content = await process_proposal_pipeline(
                pdf_path=pdf_file,
                company_name=기업명,
                business_fields=사업분야.split(','),
                announcement_title=announcement["TITLE"],
                announcement_content=announcement["CONTENT"]
            )
        except Exception as e:
            logger.error(f"제안서 생성 파이프라인 오류: {str(e)}")
            raise HTTPException(status_code=500, detail="제안서 생성 중 오류가 발생했습니다")

        return ProposalResponse(
            공고일련번호=공고일련번호,
            공고제목=announcement["TITLE"],
            제안서내용=proposal_content,
            생성일자=datetime.now().date()
        )

    except Exception as e:
        logger.error(f"제안서 생성 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if 'cursor' in locals():
            cursor.close()