import time
from datetime import datetime
import re
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import requests
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import undetected_chromedriver as uc

def run():
#def main():

    """크롤러 메인 함수"""
    # 실행 전 체크포인트 확인
    print_checkpoint('kstartup')
    
    print("k-startup 크롤링 시작...")
    base_url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    
    # 데이터 수집
    announcements = get_announcement_list(base_url, start_page=1, end_page=1)
    #announcements = get_announcement_list(base_url, start_page=1, end_page=None)

    print("\n최종 결과:")
    print(f"총 {len(announcements)}개의 공고 수집 완료")
    
    # DB 저장
    connection = connect_to_database()
    if connection:
        insert_into_db(connection, announcements)
        connection.close()
    
    # 크롤링 후 체크포인트 확인
    print_checkpoint('kstartup')
    
    print("크롤링 완료")

# 웹드라이버 설정
def setup_driver():
    """웹드라이버 설정"""
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    options.add_argument(f'user-agent={user_agent}')
    
    try:
        driver = uc.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"드라이버 설정 중 오류 발생: {e}")
        raise

# 공고 상세 페이지 크롤링 함수
def get_announcement_detail(driver, url):
    """상세 페이지에서 공고 정보 추출"""
    try:
        driver.get(url)
        time.sleep(2)
        
        data = {
            'POSTDATE': None,
            'ANNOUNCEMENT_NUMBER': None,
            'TITLE': None,
            'CATEGORY': None,
            'LOCATION': "전국",
            'CONTENT': None,
            'START': None,
            'END': None,
            'AGENCY': None,
            'LINK': url,
            'FILE': None,
            'KEYWORD': None
        }
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 제목 추출
        title_elem = soup.find('div', class_='title')
        if title_elem:
            data['TITLE'] = title_elem.find('h3').text.strip() if title_elem.find('h3') else None
        
        # 기본 정보 추출
        info_lists = soup.find_all('ul', class_='dot_list-wrap')
        for info_list in info_lists:
            items = info_list.find_all('li')
            for item in items:
                label = item.find('p', class_='tit')
                value = item.find('p', class_='txt')
                if label and value:
                    label_text = label.text.strip()
                    value_text = value.text.strip()
                    
                    if '지원분야' in label_text:
                        data['CATEGORY'] = value_text
                    elif '기관명' in label_text:
                        data['AGENCY'] = value_text
                    elif '접수기간' in label_text:
                        if '~' in value_text:
                            start_date, end_date = value_text.split('~')
                            data['START'] = start_date.strip()
                            data['END'] = end_date.strip()
        
        # 내용 추출
        content_elem = soup.find('div', class_='information_list-wrap')
        if content_elem:
            content_sections = content_elem.find_all('div', class_='information_list')
            content_text = []
            for section in content_sections:
                title = section.find('p', class_='title')
                content = section.find('div', class_='txt')
                if title and content:
                    content_text.append(f"{title.text.strip()}\n{content.text.strip()}")
            data['CONTENT'] = '\n\n'.join(content_text)
        
        # 첨부파일 추출
        files = []
        file_elems = soup.find_all('a', class_='file_bg')
        for elem in file_elems:
            file_name = elem.get('title', '').replace('[첨부파일] ', '')
            if file_name:
                files.append(file_name)
        data['FILE'] = ', '.join(files) if files else None
        
        return data
        
    except Exception as e:
        print(f"상세 페이지 데이터 추출 중 오류: {e}")
        return None

def get_announcement_list(base_url, start_page=1, end_page=None):
    """공고 목록 수집"""
    checkpoint = CrawlerCheckpoint('kstartup')
    announcements = []
    stop_crawling = False
    
    try:
        driver = setup_driver()
        page = start_page
        
        while end_page is None or page <= end_page:
            if stop_crawling:
                break
                
            print(f"\n{'='*50}")
            print(f"현재 {page}페이지 크롤링 시작")
            
            url = f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?page={page}&schStr=regist&pbancEndYn=N"
            driver.get(url)
            time.sleep(2)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            items = soup.find_all('li', class_='notice')
            
            if not items:
                print("더 이상 공고가 없습니다.")
                break
                
            print(f"찾은 공고 개수: {len(items)}")
            
            for item in items:
                try:
                    title_elem = item.find('div', class_='middle').find('div', class_='tit')
                    title = title_elem.text.strip() if title_elem else None
                    
                    # 날짜 및 기관 정보 추출
                    info_spans = item.find_all('span', class_='list')
                    post_date = None
                    agency = None
                    
                    for span in info_spans:
                        text = span.text.strip()
                        if '등록일자' in text:
                            post_date = text.replace('등록일자', '').strip()
                        elif text and not agency:
                            agency = text
                    
                    # 체크포인트 비교
                    if checkpoint.last_crawled:
                        if (post_date == checkpoint.last_crawled['last_post_date'] and 
                            title == checkpoint.last_crawled['last_title']):
                            print(f"\n이전 수집 지점 도달. 크롤링 중단")
                            stop_crawling = True
                            break
                    
                    # 상세 페이지 링크 추출
                    link = item.find('a')
                    onclick = link.get('onclick', '')
                    pbancSn = re.search(r"go_view\((\d+)\)", onclick)
                    
                    if pbancSn:
                        detail_url = f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={pbancSn.group(1)}&page={page}&schStr=regist&pbancEndYn=N"
                        announcement_data = get_announcement_detail(driver, detail_url)
                        
                        if announcement_data:
                            announcement_data.update({
                                'POSTDATE': post_date.replace('.', '-') if post_date else None,
                                'AGENCY': agency,
                                'LINK': detail_url
                            })
                            
                            if len(announcements) == 0:
                                print(f"체크포인트 저장: {post_date}, {title}")
                                checkpoint.save_checkpoint(post_date, title)
                            
                            announcements.append(announcement_data)
                            print(f"수집 완료: {title}")
                    
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"공고 처리 중 오류: {e}")
                    continue
            
            print(f"{page}페이지 완료 - {len(announcements)}건 수집")
            page += 1
            
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    
    finally:
        driver.quit()
    
    return announcements



def extract_date(date_str):
    """날짜 문자열을 YYYY-MM-DD 형식으로 변환"""
    if not date_str:
        return None
    try:
        # 다양한 날짜 형식 처리
        date_str = date_str.replace('.', '-').strip()
        if len(date_str) == 10:  # YYYY-MM-DD
            return date_str
        return None
    except:
        return None
    
def clean_content(text):
   """HTML 태그 및 특수문자 제거"""
   if not text:
       return text
       
   # HTML 태그 제거
   text = re.sub(r'<[^>]+>', '', text)
   
   # HTML 특수문자 변환 및 제거
   html_chars = {
       '&nbsp;': ' ',
       '&#39;': "'",
       '&quot;': '"', 
       '&lt;': '<',
       '&gt;': '>',
       '&amp;': '&',
       '&middot;': '',  # middot 제거
       '&bull;': '',    # 글머리 기호 제거
       '&rarr;': '',    # 화살표 제거
       '&raquo;': '',   # 이중 화살표 제거
       '&laquo;': '',   # 이중 화살표 제거
       '&ndash;': '-',  # 대시
       '&mdash;': '-',  # 대시
   }
   
   for char, replace in html_chars.items():
       text = text.replace(char, replace)
   
   # 나머지 HTML 엔티티 제거 (&로 시작하는 모든 특수문자)
   text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)
   
   # 공고 번호 형식의 텍스트 제거
   text = re.sub(r'중소벤처기업부 공고 제\d{4}-\d+호', '', text)
   
   # 연속된 공백 제거
   text = re.sub(r'\s+', ' ', text)
   
   # 앞뒤 공백 제거
   text = text.strip()
   
   return text

def clean_file_info(files):
   """파일 정보에서 파일명만 추출하고 문자열로 변환"""
   if not files:
       return None
       
   file_names = []
   for file in files:
       if 'name' in file:
           # 파일명과 크기 분리
           name = file['name'].split('  ')[0]  # 파일 크기 정보 제거
           file_names.append(name)
   
   # 리스트를 문자열로 변환 (쉼표로 구분)
   return ', '.join(file_names) if file_names else None

def simplify_location(location):
    """지역명을 간단하게 변환"""
    location_mapping = {
        '서울특별시': '서울', '서울시': '서울',
        '부산광역시': '부산', '부산시': '부산',
        '대구광역시': '대구', '대구시': '대구',
        '인천광역시': '인천', '인천시': '인천',
        '광주광역시': '광주', '광주시': '광주',
        '대전광역시': '대전', '대전시': '대전',
        '울산광역시': '울산', '울산시': '울산',
        '세종특별자치시': '세종', '세종시': '세종',
        '경기도': '경기',
        '강원도': '강원',
        '충청북도': '충북', '충북': '충북',
        '충청남도': '충남', '충남': '충남',
        '전라북도': '전북', '전북': '전북',
        '전라남도': '전남', '전남': '전남',
        '경상북도': '경북', '경북': '경북',
        '경상남도': '경남', '경남': '경남',
        '제주특별자치도': '제주', '제주도': '제주'
    }
    
    # 입력된 지역명에서 매핑된 간단한 이름 찾기
    for full_name, simple_name in location_mapping.items():
        if full_name in location:
            return simple_name
    return location

def extract_location(text):
    """텍스트에서 지역 정보 추출"""
    locations = ['서울', '경기', '인천', '강원', '충북', '충남', '대전', '세종', 
                '전북', '전남', '광주', '경북', '경남', '대구', '울산', '부산', '제주']
    
    location_count = {}
    for loc in locations:
        count = text.count(loc)
        if count > 0:
            location_count[loc] = count
    
    if location_count:
        # 가장 많이 언급된 지역 반환
        return max(location_count.items(), key=lambda x: x[1])[0]
    return "전국"  # 기본값

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

class CrawlerCheckpoint:
    def __init__(self, site_name):
        self.site_name = site_name
        # 현재 스크립트의 상위 디렉토리(ALRIMI)를 기준으로 경로 설정
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.checkpoint_file = os.path.join(base_dir, 'checkpoints', f'{site_name}_last_crawled.json')
        #print(f"체크포인트 파일 경로: {self.checkpoint_file}")  # 디버깅용
        self.last_crawled = self.load_checkpoint()

    def load_checkpoint(self):
        """체크포인트 파일 로드"""
        if not os.path.exists('checkpoints'):
            os.makedirs('checkpoints')
            
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
        
    def save_checkpoint(self, post_date, title):
        """최신 크롤링 정보 저장"""
        try:
            checkpoint_data = {
                'last_post_date': post_date,
                'last_title': title,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 디렉토리 존재 확인 및 생성
            checkpoint_dir = os.path.dirname(self.checkpoint_file)
            if not os.path.exists(checkpoint_dir):
                os.makedirs(checkpoint_dir)
                print(f"체크포인트 디렉토리 생성: {checkpoint_dir}")
                
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            self.last_crawled = checkpoint_data
            print(f"체크포인트 저장 성공: {self.checkpoint_file}")
            #print(f"저장된 데이터: {checkpoint_data}")  # 디버깅용
        except Exception as e:
            print(f"체크포인트 저장 중 오류 발생: {e}")
            #print(f"저장 시도한 경로: {self.checkpoint_file}")  # 디버깅용

# 체크포인트 확인을 위한 함수 추가
def print_checkpoint(site_name='kstartup'):
    checkpoint = CrawlerCheckpoint(site_name)
    if checkpoint.last_crawled:
        print("\n현재 저장된 체크포인트:")
        print(f"마지막 수집 날짜: {checkpoint.last_crawled['last_post_date']}")
        print(f"마지막 수집 제목: {checkpoint.last_crawled['last_title']}")
        print(f"업데이트 시간: {checkpoint.last_crawled['updated_at']}")
    else:
        print("\n저장된 체크포인트가 없습니다.")

def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host='10.100.54.176',          # DB 호스트
            database='ALRIMI',         # DB 이름
            user='root',      # DB 사용자명
            password='ibdp',   # DB 비밀번호
            charset='utf8mb4',
            collation='utf8mb4_general_ci'
        )
        return connection
    except Error as e:
        print(f"DB 연결 오류: {e}")
        return None

def insert_into_db(connection, announcements):
    try:
        cursor = connection.cursor()
        
        insert_query = """
            INSERT INTO Crawler (
                POSTDATE, ANNOUNCEMENT_NUMBER, TITLE, 
                CATEGORY, LOCATION, CONTENT, 
                START, END, AGENCY, 
                LINK, FILE, KEYWORD
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, 
                %s, %s, %s, %s
            )
        """
        
        for announcement in announcements:
            # CONTENT 길이 제한 (5000자)
            content = announcement.get('CONTENT')
            if content and len(content) > 4000:
                content = content[:4000]

            file = announcement.get('FILE')
            if file and len(file) > 200:
                file = file[:200]

            values = (
                announcement.get('POSTDATE'),
                announcement.get('ANNOUNCEMENT_NUMBER'),
                announcement.get('TITLE'),
                announcement.get('CATEGORY'),
                announcement.get('LOCATION'),
                content,
                announcement.get('START'),
                announcement.get('END'),
                announcement.get('AGENCY'),
                announcement.get('LINK'),
                file,
                announcement.get('KEYWORD')
            )
            
            cursor.execute(insert_query, values)
        
        connection.commit()
        print(f"{len(announcements)}개의 공고가 DB에 저장되었습니다.")
        
    except Error as e:
        print(f"데이터 저장 중 오류 발생: {e}")
        connection.rollback()
    
    finally:
        if connection.is_connected():
            cursor.close()

if __name__ == "__main__":
    run()
    #main()