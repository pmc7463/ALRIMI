from typing import TypedDict, Annotated

class GraphState(TypedDict):
    # 초기 정의값
    retriever: Annotated[object, "리트리버 객체 - input으로 들어옴"]
    question: Annotated[str, "사용자의 질문 - 회사의 브로셔!"]  
    question_split_page: Annotated[list, "페이지별 벡터 분할 테스트."]
    context: Annotated[str, "검색 문서의 중간 결과. - 리트리버 청크값."]
    answer: Annotated[str, "공고에 대한 정제된 답변?"]
    proposal_context: Annotated[str, "회사에 대한 제안서 초안"]
    main_filed: Annotated[list[str], "회사의 분야 (입력값)"]
    file_name: Annotated[str, "입력으로 들어오는 파일의 전체 경로 및 이름"]
    file_type: Annotated[str, "파일의 확장자 타입. (pdf, hwp, ...)"]
    announcement_title: Annotated[str, "선택한 공고 제목"]
    announcement_content: Annotated[str, "선택한 공고 내용"]