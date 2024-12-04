import os, glob, sys
from ...graph_definition import GraphState
from typing import List, AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

sys.path.append('/home/pmc/work_space')
from key_manager import set_openai_api_key, get_openai_api_key

class CompanyInfo(BaseModel):
    company_name: str = Field(..., description="회사이름")
    company_address: str = Field(..., description="회사주소")
    research_necessity: str = Field(..., description="연구개발과제의 필요성 (지원 분야 기반)")
    research_objectives: str = Field(..., description="연구개발과제의 목표 및 내용 (지원 분야 기반)")
    technical_outcome: str = Field(..., description="기술적 활용방안 및 기대성과")
    industrial_outcome: str = Field(..., description="산업적 활용방안 및 기대성과")
    social_outcome: str = Field(..., description="사회적 활용방안 및 기대성과")
    company_history: List[str] = Field(default_factory=list, description="회사 이력")
    company_introduction: str = Field(..., description="회사 소개")
    main_business: List[str] = Field(..., description="회사 주요 업무")
    company_vision: str = Field(..., description="회사 비전")

# API 키 설정 (한 번만 호출)
set_openai_api_key()
# 환경 변수에서 OpenAI API 키 읽기
openai_api_key = get_openai_api_key()

prompt = PromptTemplate.from_template("""
당신은 유능한 연구개발 제안서 초안 작성 AI 어시스턴트 입니다.
주어진 사업공고 내용과 회사 정보를 바탕으로 적절한 제안서를 작성해주세요.
분량은 A4 2장정도로 작성합니다.

[공고 정보]
제목: {announcement_title}
내용: {announcement_content}

[Company Main Field]
{company_filed}

[Company Information]
{company_context}        

위 정보를 바탕으로 다음 구조에 맞게 제안서를 작성해주세요:

1. 연구개발과제의 필요성
   - 공고 내용과 연계하여 회사의 강점 부각
   - 해당 과제가 필요한 배경과 중요성

2. 연구개발과제의 목표 및 내용
   - 공고의 요구사항과 연계된 구체적 목표
   - 세부 연구 내용 및 방법

3. 기대성과
   - 기술적 활용방안 및 기대성과
   - 산업적 활용방안 및 기대성과
   - 사회적 활용방안 및 기대성과

4. 수행 역량
   - 회사의 관련 기술 및 경험
   - 인프라 및 전문인력 현황    
""")

# 모델 초기화에 API 키 추가
structured_llm = ChatOpenAI(
    model='gpt-4o-mini',
    api_key=openai_api_key
).with_structured_output(CompanyInfo)

base_llm = ChatOpenAI(
    model='gpt-4o-mini',
    api_key=openai_api_key
)

# 스트리밍용 모델
streaming_llm = ChatOpenAI(
    model='gpt-4o-mini',
    api_key=openai_api_key,
    streaming=True,
    temperature=0.7
)

# 스트리밍 체인
streaming_chain = prompt | streaming_llm | StrOutputParser()

# 일반 체인 (기존 기능 유지)
chain = prompt | base_llm | StrOutputParser()

async def proposal_maker_node_stream(state: GraphState) -> AsyncGenerator[str, None]:
    """스트리밍 방식의 제안서 생성"""
    try:
        company_info = ""
        for info in state.get('question_split_page', []):
            company_info += str(info)
            
        company_field = state.get('main_filed', [])
        announcement_title = state.get('announcement_title', '')
        announcement_content = state.get('announcement_content', '')

        # 스트리밍 방식으로 제안서 생성
        async for chunk in streaming_chain.astream({
            "company_filed": company_field,
            "company_context": company_info,
            "announcement_title": announcement_title,
            "announcement_content": announcement_content
        }):
            yield chunk

    except Exception as e:
        logger.error(f"Streaming proposal generation error: {str(e)}")
        raise

def proposal_maker_node(state: GraphState) -> GraphState:
    """기존 방식의 제안서 생성 (호환성 유지)"""
    try:
        company_info = ""
        for info in state.get('question_split_page', []):
            company_info += str(info)
            
        company_field = state.get('main_filed', [])
        announcement_title = state.get('announcement_title', '')
        announcement_content = state.get('announcement_content', '')

        proposal_context = chain.invoke({
            "company_filed": company_field,
            "company_context": company_info,
            "announcement_title": announcement_title,
            "announcement_content": announcement_content
        })

        return GraphState(
            retriever=state.get('retriever'),
            question=state.get('question', ''),
            question_split_page=state.get('question_split_page', []),
            context=state.get('context', []),
            answer=state.get('answer', ''),
            proposal_context=proposal_context,
            main_filed=company_field,
            file_name=state.get('file_name', ''),
            file_type=state.get('file_type', 'pdf'),
            announcement_title=announcement_title,
            announcement_content=announcement_content
        )

    except Exception as e:
        logger.error(f"Proposal generation error: {str(e)}")
        raise