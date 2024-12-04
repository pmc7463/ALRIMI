from apscheduler.schedulers.blocking import BlockingScheduler
import importlib
import logging
from datetime import datetime
from typing import List, Dict
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import os
import json
import mysql.connector
from mysql.connector import Error

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self):
        self.model = SentenceTransformer('jhgan/ko-sbert-nli')
        self.dimension = 768
        self.index = None
        self.announcements = []
        self.last_update = None
        self.db_path = os.path.join(os.path.dirname(__file__), 'vector_db')
        self.ensure_directory()
    
    def ensure_directory(self):
        """벡터 DB 디렉토리 생성"""
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
    
    def load_checkpoint(self):
        """마지막 업데이트 시점 로드"""
        checkpoint_file = os.path.join(self.db_path, 'last_update.json')
        if os.path.exists(checkpoint_file):
            with open(checkpoint_file, 'r') as f:
                self.last_update = json.load(f)
                logger.info(f"마지막 업데이트: {self.last_update['last_update']}")
    
    def save_checkpoint(self):
        """현재 업데이트 시점 저장"""
        checkpoint_file = os.path.join(self.db_path, 'last_update.json')
        checkpoint_data = {
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_announcements': len(self.announcements)
        }
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f)
        logger.info(f"체크포인트 저장: {checkpoint_data}")
    
    def update_from_db(self):
        """DB에서 새로운 공고 가져와서 벡터 DB 업데이트"""
        try:
            # DB 연결
            connection = mysql.connector.connect(
                host='10.100.54.176',
                database='ALRIMI',
                user='root',
                password='ibdp',
                charset='utf8mb4'
            )
            cursor = connection.cursor(dictionary=True)
            
            # 기존 벡터 DB 로드
            self.load()
            
            # 이미 처리된 ID 목록
            processed_ids = {ann['ID'] for ann in self.announcements}
            
            # 새로운 공고 조회
            cursor.execute("""
                SELECT ID, TITLE, CONTENT, LOCATION, CATEGORY, 
                       START, END, AGENCY, LINK, FILE
                FROM Crawler
                WHERE END >= CURRENT_DATE 
                   OR END IN ('예산 소진시', '예산 소진시까지', '상시')
            """)
            
            new_announcements = cursor.fetchall()
            logger.info(f"전체 공고 수: {len(new_announcements)}")
            
            # 새로운 공고만 추가
            added_count = 0
            for ann in new_announcements:
                if ann['ID'] not in processed_ids:
                    text = f"{ann['TITLE']} {ann['CONTENT']}"
                    vector = self.model.encode([text])[0]
                    
                    if self.index is None:
                        self.index = faiss.IndexFlatL2(self.dimension)
                    
                    self.index.add(vector.reshape(1, -1).astype('float32'))
                    self.announcements.append(ann)
                    added_count += 1
            
            logger.info(f"새로 추가된 공고 수: {added_count}")
            
            # 저장
            if added_count > 0:
                self.save()
                self.save_checkpoint()
            
        except Exception as e:
            logger.error(f"벡터 DB 업데이트 중 오류: {e}")
            raise
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
    
    def save(self):
        """벡터 DB 저장"""
        index_path = os.path.join(self.db_path, 'announcement_vectors.idx')
        data_path = os.path.join(self.db_path, 'announcements.pkl')
        
        faiss.write_index(self.index, index_path)
        with open(data_path, 'wb') as f:
            pickle.dump(self.announcements, f)
        
        logger.info(f"벡터 DB 저장 완료: {len(self.announcements)}개 공고")
    
    def load(self):
        """기존 벡터 DB 로드"""
        try:
            index_path = os.path.join(self.db_path, 'announcement_vectors.idx')
            data_path = os.path.join(self.db_path, 'announcements.pkl')
            
            if os.path.exists(index_path) and os.path.exists(data_path):
                self.index = faiss.read_index(index_path)
                with open(data_path, 'rb') as f:
                    self.announcements = pickle.load(f)
                logger.info(f"기존 벡터 DB 로드 완료: {len(self.announcements)}개 공고")
            else:
                logger.info("기존 벡터 DB가 없습니다. 새로 생성합니다.")
        except Exception as e:
            logger.error(f"벡터 DB 로드 중 오류: {e}")
            self.index = None
            self.announcements = []

# 벡터 DB 인스턴스 생성
vector_db = VectorDB()

def run_crawler_and_update_vectordb(site_name):
    """크롤러 실행 후 벡터 DB 업데이트"""
    try:
        logger.info(f"{site_name} 크롤러 시작")
        crawler = importlib.import_module(f'Crawlers.{site_name}')
        crawler.run()
        logger.info(f"{site_name} 크롤러 완료")
        
        # 마지막 크롤러 실행 후 벡터 DB 업데이트
        if site_name == 'kstartup':
            logger.info("모든 크롤링 완료, 벡터 DB 업데이트 시작")
            vector_db.update_from_db()
            
    except Exception as e:
        logger.error(f"{site_name} 처리 중 오류 발생: {e}")

def main():
    scheduler = BlockingScheduler()
    #sites = ['중소벤처기업부', '소셜벤쳐스퀘어', '창조경제혁신센터', 'iris', '기업마당', 'kstartup']
    sites = ['창조경제혁신센터', 'iris', '기업마당', 'kstartup']
    for site in sites:
        scheduler.add_job(
            run_crawler_and_update_vectordb,
            'cron', 
            hour=23,
            minute=24,
            args=[site],
            id=f'{site}_crawler',
            name=f'{site} Crawler'
        )
        logger.info(f"{site} 크롤러 스케줄 등록 완료")
    
    try:
        logger.info("스케줄러 시작")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 종료")

if __name__ == "__main__":
    main()
