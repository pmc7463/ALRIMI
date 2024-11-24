from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class AnnouncementBase(BaseModel):
    ID: int
    POSTDATE: date
    TITLE: str
    CATEGORY: Optional[str] = None
    LOCATION: Optional[str] = None
    CONTENT: Optional[str] = None
    START: Optional[str] = None
    END: Optional[str] = None
    AGENCY: Optional[str] = None
    LINK: Optional[str] = None
    FILE: Optional[str] = None

    class Config:
        from_attributes = True

class PaginationInfo(BaseModel):
    total_items: int
    current_page: int
    total_pages: int
    items_per_page: int

class AnnouncementList(BaseModel):
    items: List[AnnouncementBase]
    pagination: PaginationInfo