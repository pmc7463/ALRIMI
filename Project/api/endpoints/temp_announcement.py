from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ...models.announcement import AnnouncementList, AnnouncementBase
from ...database.database import Database
from mysql.connector import Error

router = APIRouter()
db = Database()

@router.get("/announcements/", response_model=AnnouncementList)
async def get_announcements(
    page: int = Query(1, ge=1, description="현재 페이지"),
    공고문출력수: int = Query(10, ge=1, le=100, description="페이지당 출력할 공고 수"),
    지역: Optional[str] = None,
    카테고리: Optional[str] = None
):
    """
    사업공고 리스트를 조회합니다.
    """
    try:
        connection = await db.connect()
        if not connection:
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")

        cursor = connection.cursor(dictionary=True)
        
        # 기본 쿼리 구성
        query = "SELECT COUNT(*) as total FROM Crawler WHERE 1=1"
        where_conditions = []
        params = []

        # 필터 조건 추가
        if 지역:
            where_conditions.append("LOCATION = %s")
            params.append(지역)
        if 카테고리:
            where_conditions.append("CATEGORY = %s")
            params.append(카테고리)

        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)

        # 전체 개수 조회
        cursor.execute(query, params)
        total_count = cursor.fetchone()['total']

        # 페이지네이션 적용된 데이터 조회
        query = """
            SELECT 
                ANNOUNCEMENT_NUMBER, TITLE, LOCATION, AGENCY, 
                CONTENT, START, END, FILE, LINK, CATEGORY, POSTDATE
            FROM Crawler 
            WHERE 1=1
        """
        if where_conditions:
            query += " AND " + " AND ".join(where_conditions)
        
        query += " ORDER BY POSTDATE DESC LIMIT %s OFFSET %s"
        params.extend([공고문출력수, (page - 1) * 공고문출력수])

        cursor.execute(query, params)
        announcements = cursor.fetchall()

        return AnnouncementList(
            items=[AnnouncementBase(**announcement) for announcement in announcements],
            total=total_count,
            page=page,
            size=공고문출력수
        )

    except Error as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
    
    finally:
        if 'cursor' in locals():
            cursor.close()

@router.get("/announcements/{announcement_number}", response_model=AnnouncementBase)
async def get_announcement_detail(announcement_number: str):
    """
    특정 공고의 상세 정보를 조회합니다.
    """
    try:
        connection = await db.connect()
        if not connection:
            raise HTTPException(status_code=500, detail="데이터베이스 연결 실패")

        cursor = connection.cursor(dictionary=True)
        
        query = """
            SELECT 
                ANNOUNCEMENT_NUMBER, TITLE, LOCATION, AGENCY, 
                CONTENT, START, END, FILE, LINK, CATEGORY, POSTDATE
            FROM Crawler 
            WHERE ANNOUNCEMENT_NUMBER = %s
        """
        
        cursor.execute(query, (announcement_number,))
        announcement = cursor.fetchone()

        if not announcement:
            raise HTTPException(status_code=404, detail="공고를 찾을 수 없습니다")

        return AnnouncementBase(**announcement)

    except Error as e:
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
    
    finally:
        if 'cursor' in locals():
            cursor.close()