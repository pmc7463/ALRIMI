from fastapi import APIRouter, HTTPException, Query  # Query 추가
from typing import Optional
from ...models.announcement import AnnouncementBase, AnnouncementList, PaginationInfo  # PaginationInfo 추가
from ...database.database import Database
from mysql.connector import Error
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
db = Database()

@router.get("/announcements/", response_model=AnnouncementList)
async def get_announcements(
    page: int = Query(1, ge=1, description="페이지 번호"),
    size: int = Query(10, ge=1, le=50, description="페이지당 항목 수")
):
    """
    사업공고 리스트를 페이지별 최신순으로 조회합니다.
    """
    try:
        connection = await db.connect()
        if not connection:
            logger.error("데이터베이스 연결 실패")
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")

        cursor = connection.cursor(dictionary=True)
        
        # 전체 개수 조회
        cursor.execute("SELECT COUNT(*) as total FROM Crawler")
        total_items = cursor.fetchone()['total']

        # 전체 페이지 수 계산
        total_pages = (total_items + size - 1) // size
        
        # 페이지 번호 검증
        if page > total_pages:
            raise HTTPException(status_code=404, detail="존재하지 않는 페이지입니다")
        
        # OFFSET 계산
        offset = (page - 1) * size

       # 페이지네이션이 적용된 데이터 조회
        query = """
            SELECT 
                ID, 
                POSTDATE,
                TITLE,
                CATEGORY,
                LOCATION,
                CONTENT,
                START,
                END,
                AGENCY,
                LINK,
                FILE
            FROM Crawler 
            ORDER BY POSTDATE DESC, ID DESC
            LIMIT %s OFFSET %s
        """
        
        logger.debug(f"Executing query with size: {size}, offset: {offset}")  # 디버그 로그 추가
        cursor.execute(query, (size, offset))  # size를 동적으로 사용
        announcements = cursor.fetchall()
        
        logger.info(f"조회된 공고 수: {len(announcements)}, 요청된 size: {size}")  # 로그 개선
        
        return AnnouncementList(
            items=[AnnouncementBase(**announcement) for announcement in announcements],
            pagination=PaginationInfo(
                total_items=total_items,
                current_page=page,
                total_pages=total_pages,
                items_per_page=size
            )
        )

    except Error as e:
        logger.error(f"데이터베이스 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        if 'cursor' in locals():
            cursor.close()

@router.get("/announcements/{id}", response_model=AnnouncementBase)
async def get_announcement_detail(id: int):
    """
    특정 공고의 상세 정보를 조회합니다.
    """
    try:
        connection = await db.connect()
        if not connection:
            logger.error("데이터베이스 연결 실패")
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")

        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT 
                ID,
                POSTDATE,
                TITLE,
                CATEGORY,
                LOCATION,
                CONTENT,
                START,
                END,
                AGENCY,
                LINK,
                FILE
            FROM Crawler 
            WHERE ID = %s
        """
        
        cursor.execute(query, (id,))
        announcement = cursor.fetchone()

        if not announcement:
            logger.warning(f"공고를 찾을 수 없음 - ID: {id}")
            raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

        return AnnouncementBase(**announcement)

    except Error as e:
        logger.error(f"데이터베이스 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
    
    finally:
        if 'cursor' in locals():
            cursor.close()