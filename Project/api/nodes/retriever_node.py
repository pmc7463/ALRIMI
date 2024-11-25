import os, sys
import numpy as np
from ...graph_definition import GraphState
from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

def get_model():
    """한국어 SBERT 모델 로드"""
    return SentenceTransformer('jhgan/ko-sbert-nli')

def perform_embedding(texts: list) -> list:
    """텍스트 임베딩 수행"""
    try:
        model = get_model()
        embeddings = model.encode(texts)
        return list(zip(texts, embeddings))
    except Exception as e:
        logger.error(f"임베딩 오류: {str(e)}")
        raise

def vector_direct_retriever_node(state: GraphState) -> GraphState:
    """벡터 검색 노드"""
    try:
        # 현재 상태에서 필요한 데이터 가져오기
        split_question = state.get('question_split_page', [])
        logger.info(f"Processing {len(split_question)} text segments")

        # 임베딩 수행
        page_embedding = perform_embedding(split_question)
        vectors = [emb[1] for emb in page_embedding]
        average_embedding = np.mean(vectors, axis=0) if vectors else None

        # 모든 상태 값 유지하면서 context 업데이트
        return GraphState(
            retriever=state.get('retriever'),
            question=state.get('question', ''),
            question_split_page=split_question,
            context=page_embedding,  # 임베딩 결과 저장
            answer=state.get('answer', ''),
            proposal_context=state.get('proposal_context', ''),
            main_filed=state.get('main_filed', []),
            file_name=state.get('file_name', ''),
            file_type=state.get('file_type', 'pdf')
        )

    except Exception as e:
        logger.error(f"Retriever error: {str(e)}")
        raise

def bm25_retriever_node(state: GraphState) -> GraphState:
    """BM25 검색 노드"""
    # 모든 상태 값 유지
    return GraphState(
        retriever=state.get('retriever'),
        question=state.get('question', ''),
        question_split_page=state.get('question_split_page', []),
        context=state.get('context', []),
        answer=state.get('answer', ''),
        proposal_context=state.get('proposal_context', ''),
        main_filed=state.get('main_filed', []),
        file_name=state.get('file_name', ''),
        file_type=state.get('file_type', 'pdf')
    )

def hybrid_retriever_node(state: GraphState) -> GraphState:
    """하이브리드 검색 노드"""
    # 모든 상태 값 유지
    return GraphState(
        retriever=state.get('retriever'),
        question=state.get('question', ''),
        question_split_page=state.get('question_split_page', []),
        context=state.get('context', []),
        answer=state.get('answer', ''),
        proposal_context=state.get('proposal_context', ''),
        main_filed=state.get('main_filed', []),
        file_name=state.get('file_name', ''),
        file_type=state.get('file_type', 'pdf')
    )

def vector_retriever_node(state: GraphState) -> GraphState:
    """벡터 검색 노드"""
    # 모든 상태 값 유지
    return GraphState(
        retriever=state.get('retriever'),
        question=state.get('question', ''),
        question_split_page=state.get('question_split_page', []),
        context=state.get('context', []),
        answer=state.get('answer', ''),
        proposal_context=state.get('proposal_context', ''),
        main_filed=state.get('main_filed', []),
        file_name=state.get('file_name', ''),
        file_type=state.get('file_type', 'pdf')
    )