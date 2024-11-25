import os, glob, sys
from ...graph_definition import GraphState
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import requests
import logging

logger = logging.getLogger(__name__)

def get_upstage_document_ocr(image_path):
    api_key = "up_slmPU1Ldu169KdRPWgde2FsCW4V3p"
    url = "https://api.upstage.ai/v1/document-ai/ocr"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    with open(image_path, "rb") as f:
        files = {"document": f}
        response = requests.post(url, headers=headers, files=files)
    
    return response.json()['text']

def python_tessorect_ocr(image_path):
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang='kor+eng')
    return text

def pdf_to_images(pdf_path, dpi=200, fmt='jpg'):
    output_dir = "image_temp"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
        image_paths = []
        
        for i, image in enumerate(images):
            file_name = f'page_{str(i+1).zfill(3)}.{fmt}'
            file_path = os.path.join(output_dir, file_name)
            
            save_fmt = 'JPEG' if fmt.lower() in ['jpg', 'jpeg'] else fmt.upper()
            image.save(file_path, save_fmt)
            image_paths.append(file_path)
            
        logger.info(f"{pdf_path} 이미지 저장 완료")
        return image_paths
    
    except Exception as e:
        logger.error(f'에러 발생: {str(e)}')
        return []

def cleanup_temp_images():
    temp_dir = "image_temp"
    if os.path.exists(temp_dir):
        try:
            for file_path in glob.glob(os.path.join(temp_dir, "*")):
                os.remove(file_path)
            logger.info(f"Successfully cleaned up {temp_dir} directory")
        except Exception as e:
            logger.error(f"Error cleaning up temporary files: {str(e)}")

def python_tessorect_ocr_node(state: GraphState) -> GraphState:
    # 현재 상태 값들 가져오기
    loader_question = state.get('question_split_page', [])
    current_file = state['file_name']
    
    # OCR 처리
    image_paths = pdf_to_images(current_file)
    
    try:
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(python_tessorect_ocr, image_paths))
            loader_question.extend(results)
            
    finally:
        cleanup_temp_images()
    
    # 모든 필드를 포함한 새로운 상태 반환
    return GraphState(
        retriever=state.get('retriever'),
        question=state.get('question', ''),
        question_split_page=loader_question,
        context=state.get('context', []),
        answer=state.get('answer', ''),
        proposal_context=state.get('proposal_context', ''),
        main_filed=state.get('main_filed', []),
        file_name=current_file,
        file_type=state.get('file_type', 'pdf')
    )

def upstage_ocr_node(state: GraphState) -> GraphState:
    # 현재 상태 값들 가져오기
    loader_question = state.get('question_split_page', [])
    current_file = state['file_name']
    
    # OCR 처리
    image_paths = pdf_to_images(current_file)
    
    try:
        for image_path in image_paths:
            result = get_upstage_document_ocr(image_path)
            loader_question.append(result)
    
    finally:
        cleanup_temp_images()
    
    # 모든 필드를 포함한 새로운 상태 반환
    return GraphState(
        retriever=state.get('retriever'),
        question=state.get('question', ''),
        question_split_page=loader_question,
        context=state.get('context', []),
        answer=state.get('answer', ''),
        proposal_context=state.get('proposal_context', ''),
        main_filed=state.get('main_filed', []),
        file_name=current_file,
        file_type=state.get('file_type', 'pdf')
    )