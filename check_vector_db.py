import os
import pickle
import faiss
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_vector_db():
    vector_db_path = '/home/pmc/work_space/ALRIMI/vector_db'
    
    # 파일 존재 확인
    index_path = os.path.join(vector_db_path, 'announcement_vectors.idx')
    data_path = os.path.join(vector_db_path, 'announcements.pkl')
    checkpoint_path = os.path.join(vector_db_path, 'last_update.json')
    
    logger.info("벡터 DB 파일 확인:")
    logger.info(f"- 인덱스 파일 존재: {os.path.exists(index_path)}")
    logger.info(f"- 데이터 파일 존재: {os.path.exists(data_path)}")
    logger.info(f"- 체크포인트 존재: {os.path.exists(checkpoint_path)}")
    
    try:
        # 벡터 인덱스 확인
        if os.path.exists(index_path):
            index = faiss.read_index(index_path)
            logger.info(f"\n벡터 인덱스 정보:")
            logger.info(f"- 저장된 벡터 수: {index.ntotal}")
            logger.info(f"- 벡터 차원: {index.d}")
        
        # 공고 데이터 확인
        if os.path.exists(data_path):
            with open(data_path, 'rb') as f:
                announcements = pickle.load(f)
            logger.info(f"\n공고 데이터 정보:")
            logger.info(f"- 저장된 공고 수: {len(announcements)}")
            if announcements:
                logger.info("\n첫 번째 공고 예시:")
                first_ann = announcements[0]
                for key, value in first_ann.items():
                    logger.info(f"- {key}: {value[:100] if isinstance(value, str) else value}")
        
    except Exception as e:
        logger.error(f"벡터 DB 확인 중 오류 발생: {e}")

if __name__ == "__main__":
    check_vector_db()
