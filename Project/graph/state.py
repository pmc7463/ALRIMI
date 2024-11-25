from typing import TypedDict, Annotated, List, Optional

class GraphState(TypedDict):
    # 파일 관련
    file_name: Annotated[str, "입력 파일 경로"]
    file_type: Annotated[str, "파일 타입(pdf)"]
    
    # 회사 정보
    company_name: Annotated[str, "회사명"]
    company_address: Annotated[str, "회사 주소"]
    business_fields: Annotated[List[str], "사업분야"]
    
    # 처리 중간 데이터
    question: Annotated[str, "추출된 전체 텍스트"]
    question_split_page: Annotated[list, "페이지별 텍스트"]
    context: Annotated[list, "검색된 문서 컨텍스트"]
    
    # 결과
    proposal_context: Annotated[str, "생성된 제안서 내용"]
    announcement_id: Annotated[int, "공고 ID"]
    announcement_title: Annotated[str, "공고 제목"]