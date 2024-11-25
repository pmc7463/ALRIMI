from datetime import datetime, date
from typing import List, Dict, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

class RecommendationEngine:
    def __init__(self):
        self.model = SentenceTransformer('jhgan/ko-sbert-nli')
        self.weights = {
            'time': 0.3,
            'location': 0.3,
            'field': 0.4
        }

    def calculate_time_score(self, end_date: str) -> float:
        """남은 기간 점수 계산"""
        if end_date.lower() in ['예산 소진시', '예산 소진시까지', '상시']: 
            return 1.0
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            today = date.today()
            days_left = (end - today).days
            return min(max(days_left / 30, 0), 1)  # 30일을 기준으로 정규화
        except:
            return 0.5

    def calculate_location_match(self, company_location: str, announcement_location: str) -> float:
        """지역 일치도 계산"""
        # 광역시/도 단위로 매칭
        company_region = company_location.split()[0]
        announcement_region = announcement_location.split()[0]
        return 1.0 if company_region == announcement_region else 0.0

    def calculate_field_match(self, company_fields: List[str], announcement_fields: List[str]) -> float:
        """사업분야 일치도 계산"""
        company_fields = set(f.strip().lower() for f in company_fields)
        announcement_fields = set(f.strip().lower() for f in announcement_fields)
        
        if not company_fields or not announcement_fields:
            return 0.0
            
        intersection = company_fields.intersection(announcement_fields)
        return len(intersection) / max(len(company_fields), len(announcement_fields))

    def get_recommendation_reason(self, location_score: float, field_score: float) -> str:
        """추천 사유 결정"""
        if location_score > 0 and field_score > 0:
            return "분야와 지역이 일치하여 추천"
        elif field_score > 0:
            return "분야가 일치하여 추천"
        elif location_score > 0:
            return "지역이 일치하여 추천"
        return "기타 조건이 일치하여 추천"

    def recommend(self, company_info: dict, announcements: List[dict], top_k: int = 10) -> List[dict]:
        """공고 추천"""
        recommendations = []
        
        for ann in announcements:
            # 점수 계산
            time_score = self.calculate_time_score(ann['END'])
            location_score = self.calculate_location_match(company_info['주소'], ann['LOCATION'])
            field_score = self.calculate_field_match(company_info['사업분야'], ann['CATEGORY'].split(','))
            
            # 가중치 적용
            total_score = (
                self.weights['time'] * time_score +
                self.weights['location'] * location_score +
                self.weights['field'] * field_score
            )
            
            if total_score > 0:  # 최소 점수 이상인 경우만 추천
                recommendations.append({
                    'score': total_score,
                    'announcement': ann,
                    'reason': self.get_recommendation_reason(location_score, field_score)
                })
        
        # 점수순 정렬
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations[:top_k]