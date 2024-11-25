from pathlib import Path
from ...graph_definition import GraphState

def start_node(state: GraphState) -> GraphState:
    """시작 노드"""
    file_name = state['file_name']
    file_type = Path(file_name).suffix[1:].lower()
    
    return GraphState(
        file_type=file_type
    )