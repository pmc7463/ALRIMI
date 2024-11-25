from langchain.graph import StateGraph
from ..graph.state import GraphState
from ..nodes import (
    start_node,
    pyMuPDF_loader_node,
    python_tessorect_ocr_node,
    vector_direct_retriever_node,
    proposal_maker_node
)

def create_proposal_pipeline() -> StateGraph:
    """제안서 생성 파이프라인 생성"""
    graph = StateGraph(GraphState)
    
    # 노드 추가
    graph.add_node("start", start_node)
    graph.add_node("loader", pyMuPDF_loader_node)
    graph.add_node("ocr", python_tessorect_ocr_node)
    graph.add_node("retriever", vector_direct_retriever_node)
    graph.add_node("proposal", proposal_maker_node)
    
    # 엣지 추가
    graph.add_edge("start", "loader")
    graph.add_edge("loader", "ocr")
    graph.add_edge("ocr", "retriever")
    graph.add_edge("retriever", "proposal")
    
    # 시작 노드 설정
    graph.set_entry_point("start")
    
    return graph.compile()