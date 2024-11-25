import os
from typing import Dict
from ...graph_definition import GraphState
from langchain_community.document_loaders import PyMuPDFLoader
import logging

logger = logging.getLogger(__name__)

def pdf_markdown_loader_node(state: GraphState) -> GraphState:
    """PDF 텍스트 마크다운 로더"""
    import pymupdf4llm
    
    pdf_file_name = state['file_name']
    pdf_markdown = pymupdf4llm.to_markdown(pdf_file_name)

    return GraphState(
        retriever=state.get('retriever'),
        question=pdf_markdown,
        question_split_page=state.get('question_split_page', []),
        context=state.get('context', []),
        answer=state.get('answer', ''),
        proposal_context=state.get('proposal_context', ''),
        main_filed=state.get('main_filed', []),
        file_name=pdf_file_name,
        file_type=state.get('file_type', 'pdf')
    )

def pyMuPDF_loader_node(state: GraphState) -> GraphState:
    """PyMuPDF 로더"""
    current_file = state['file_name']
    logger.info(f"Loading PDF: {current_file}")

    try:
        loader = PyMuPDFLoader(current_file)
        docs = loader.load()

        texts = ""
        page_splited_text = []

        for doc in docs:
            add_contents = doc.page_content
            if add_contents == '':
                add_contents = "None"

            texts += add_contents
            page_splited_text.append(add_contents)

        logger.info(f"Successfully loaded {len(page_splited_text)} pages")
        
        # 모든 필드를 포함한 새로운 상태 반환
        return GraphState(
            retriever=state.get('retriever'),
            question=texts,
            question_split_page=page_splited_text,
            context=state.get('context', []),
            answer=state.get('answer', ''),
            proposal_context=state.get('proposal_context', ''),
            main_filed=state.get('main_filed', []),
            file_name=current_file,
            file_type=state.get('file_type', 'pdf')
        )

    except Exception as e:
        logger.error(f"Error loading PDF: {str(e)}")
        raise