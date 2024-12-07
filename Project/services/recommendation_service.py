from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from datetime import datetime
import os
import pickle
from typing import List, Dict
import logging
from ..api.nodes.loader_node import pyMuPDF_loader_node

logger = logging.getLogger(__name__)

class RecommendationService:
    def __init__(self):
        try:
            logger.info("RecommendationService 초기화 시작")
            self.model = SentenceTransformer('jhgan/ko-sbert-nli')
            self.vector_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vector_db')
            self.index = None
            self.announcements = None
            self.load_vector_db()
            logger.info("RecommendationService 초기화 완료")
        except Exception as e:
            logger.error(f"초기화 중 오류: {e}")
            raise

    def load_vector_db(self):
        """벡터 DB 로드"""
        try:
            index_path = os.path.join(self.vector_db_path, 'announcement_vectors.idx')
            data_path = os.path.join(self.vector_db_path, 'announcements.pkl')
            
            if os.path.exists(index_path) and os.path.exists(data_path):
                self.index = faiss.read_index(index_path)
                with open(data_path, 'rb') as f:
                    self.announcements = pickle.load(f)
                logger.info(f"벡터 DB 로드 완료: {len(self.announcements)}개 공고")
            else:
                raise FileNotFoundError("벡터 DB 파일이 존재하지 않습니다")
        except Exception as e:
            logger.error(f"벡터 DB 로드 실패: {e}")
            raise

    def process_company_info(self, company_name: str, company_address: str, business_fields: List[str]) -> str:
        """회사 정보 처리"""
        pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                               'Inputs', f"{company_name}.pdf")
        
        company_info = f"""
        회사명: {company_name}
        주소: {company_address}
        사업분야: {', '.join(business_fields)}
        """
        
        if os.path.exists(pdf_path):
            try:
                result = pyMuPDF_loader_node({"file_name": pdf_path})
                pdf_text = result.get('question', '')
                company_info += f"\n회사소개서 내용:\n{pdf_text}"
                logger.info("회사소개서 텍스트 추출 완료")
            except Exception as e:
                logger.error(f"PDF 처리 중 오류: {e}")
        else:
            logger.warning(f"회사소개서 PDF 없음: {pdf_path}")

        return company_info

    def calculate_similarity_score(self, query_vector: np.ndarray, k: int = 100) -> List[Dict]:
        """유사도 기반 공고 검색"""
        if self.index is None:
            raise Exception("벡터 DB가 로드되지 않았습니다")
        
        distances, indices = self.index.search(query_vector.reshape(1, -1), k)
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.announcements):
                announcement = self.announcements[idx]
                similarity_score = 1 / (1 + distance)
                results.append({
                    'announcement': announcement,
                    'similarity_score': similarity_score
                })
        
        return results

    def get_recommendations(
        self,
        company_name: str,
        company_address: str,
        business_fields: List[str],
        top_k: int = 20
    ) -> List[Dict]:
        """추천 공고 검색"""
        try:
            logger.info(f"추천 시작 - 기업명: {company_name}")
            
            # 회사 정보 통합 처리
            company_info = self.process_company_info(company_name, company_address, business_fields)
            
            # 벡터화
            query_vector = self.model.encode([company_info])[0]
            similar_announcements = self.calculate_similarity_score(query_vector)
            
            recommendations = []
            for item in similar_announcements:
                announcement = item['announcement']
                content_similarity = item['similarity_score']
                
                # 1. 기간 점수
                time_score = 1.0
                if announcement.get('END') and announcement['END'] not in ['예산 소진시', '예산 소진시까지', '상시']:
                    try:
                        end_date = datetime.strptime(announcement['END'], '%Y-%m-%d').date()
                        days_left = (end_date - datetime.now().date()).days
                        time_score = min(max(days_left / 30, 0), 1)
                    except:
                        time_score = 0.5

                # 2. 지역 점수
                company_region = company_address.split()[0]
                announcement_region = announcement['LOCATION'].split()[0] if announcement.get('LOCATION') else ""
                location_score = 1.0 if company_region in announcement_region or announcement_region in company_region else 0.0
                
                # 3. 분야 점수
                announcement_fields = set(announcement['CATEGORY'].split(',')) if announcement.get('CATEGORY') else set()
                company_field_set = set(business_fields)
                field_score = 0.0
                if announcement_fields and company_field_set:
                    intersection = len(announcement_fields.intersection(company_field_set))
                    union = len(announcement_fields.union(company_field_set))
                    field_score = intersection / union if union > 0 else 0.0

                # 4. 최종 점수
                final_score = (
                    field_score * 0.7 +          # 분야 매칭
                    location_score * 0.1 +       # 지역 매칭
                    content_similarity * 0.1 +    # 내용 유사도
                    time_score * 0.1              # 남은 기간
                )
                
                # 5. 추천 사유
                """
                if field_score > 0 and location_score > 0:
                    reason = f"분야와 지역이 일치 (유사도: {content_similarity:.2f})"
                    category = 1
                elif field_score > 0:
                    reason = f"분야 일치 (유사도: {content_similarity:.2f})"
                    category = 2
                elif location_score > 0:
                    reason = f"지역 일치 (유사도: {content_similarity:.2f})"
                    category = 3
                else:
                    continue
                """
                if field_score >= 0.01 and location_score > 0:
                    reason = f"분야와 지역이 일치"
                    category = 1
                elif field_score >= 0.01:
                    reason = f"분야 일치"
                    category = 2
                elif location_score > 0:
                    reason = f"지역 일치"
                    category = 3
                else:
                    reason = "내용 기반 추천" 
                    category = 4  

                recommendations.append({
                    'score': final_score,
                    'category': category,
                    'announcement_id': announcement['ID'],
                    'title': announcement['TITLE'],
                    'url': announcement['LINK'],
                    'reason': reason,
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
            
            # 카테고리 우선, 점수 차순으로 정렬
            recommendations.sort(key=lambda x: (x['category'], -x['score']))
            return recommendations[:top_k]
                
        except Exception as e:
            logger.error(f"추천 처리 중 오류: {e}")
            raise