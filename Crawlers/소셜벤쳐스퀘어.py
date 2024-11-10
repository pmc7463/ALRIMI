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

def run():
#def main():

    """크롤러 메인 함수"""
    # 실행 전 체크포인트 확인
    print_checkpoint('socialventure')
    
    print("소셜벤처스퀘어 크롤링 시작...")
    base_url = "https://sv.kibo.or.kr/BoardExecute.do?pageid=BOARD00004"
    
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
    print_checkpoint('socialventure')
    
    print("크롤링 완료")

# 웹드라이버 설정
def setup_driver():
    chrome_options = Options()
    
    # 리눅스 환경에서의 추가 설정
    chrome_options.add_argument('--headless')  # 헤드리스 모드 실행
    chrome_options.add_argument('--no-sandbox')  # 샌드박스 비활성화
    chrome_options.add_argument('--disable-dev-shm-usage')  # 공유 메모리 사용 비활성화
    chrome_options.add_argument('--disable-gpu')  # GPU 하드웨어 가속 비활성화
    
    # 기존 설정들
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # 크롬 드라이버 생성 시 에러 처리
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        return driver
    except Exception as e:
        print(f"드라이버 설정 중 오류 발생: {e}")
        
        # 대체 방법 시도
        try:
            print("대체 방법으로 드라이버 설정 시도...")
            chrome_options.add_argument('--remote-debugging-port=9222')
            driver = webdriver.Chrome(
                options=chrome_options
            )
            return driver
        except Exception as sub_e:
            print(f"대체 방법도 실패: {sub_e}")
            raise

# 공고 상세 페이지 크롤링 함수
def get_announcement_detail(url, headers):
    """상세 페이지에서 공고 정보 추출"""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        board_view = soup.find('div', class_='board_view')
        
        if not board_view:
            return None
            
        data = {
            'POSTDATE': None,
            'ANNOUNCEMENT_NUMBER': None,
            'TITLE': None,
            'CATEGORY': None,
            'LOCATION': "전국",  # 기본값
            'CONTENT': None,
            'START': None,
            'END': None,
            'AGENCY': None,
            'LINK': url,
            'FILE': None,
            'KEYWORD': None
        }
        
        # 구분(카테고리) 추출
        category_dl = board_view.find('dl')
        if category_dl:
            data['CATEGORY'] = category_dl.find('dd').text.strip()
        
        # 제목과 접수기간 추출
        title_dl = board_view.find('dl', class_='board_Tit')
        if title_dl:
            # 제목
            title_dd = title_dl.find_all('dd')[0]
            data['TITLE'] = title_dd.text.strip()
            
            # 접수기간
            period_dd = title_dl.find_all('dd')[1]
            period_text = period_dd.text.strip()
            if '~' in period_text:
                start_date, end_date = period_text.split('~')
                data['START'] = start_date.strip()
                data['END'] = end_date.strip()
        
        # 담당부서(에이전시) 추출
        agency_dl = title_dl.find_next_sibling('dl')
        if agency_dl:
            agency_dd = agency_dl.find_all('dd')[1]  # 두 번째 dd가 담당부서
            data['AGENCY'] = agency_dd.text.strip()
        
        # 내용 추출
        content_dl = board_view.find('dl', class_='board_content')
        if content_dl:
            content = content_dl.find('dd').text
            # HTML 태그 및 불필요한 공백 제거
            content = re.sub(r'<[^>]+>', '', content)
            content = re.sub(r'\s+', ' ', content)
            data['CONTENT'] = content.strip()
        
        # 첨부파일 추출 (있을 경우)
        files = []
        file_area = board_view.find('div', class_='file_area')
        if file_area:
            for file_link in file_area.find_all('a'):
                if file_link.get('href'):
                    file_name = file_link.text.strip()
                    files.append(file_name)
        
        if files:
            data['FILE'] = ', '.join(files)
            
        # 지역 정보 추출
        location_text = f"{data['TITLE']} {data['CONTENT']} {data['AGENCY']}"
        locations = ['서울', '경기', '인천', '강원', '충북', '충남', '대전', '세종', 
                    '전북', '전남', '광주', '경북', '경남', '대구', '울산', '부산', '제주']
        
        found_locations = {}
        for loc in locations:
            count = location_text.count(loc)
            if count > 0:
                found_locations[loc] = count
        
        if found_locations:
            # 가장 많이 언급된 지역
            data['LOCATION'] = max(found_locations.items(), key=lambda x: x[1])[0]
        
        return data
        
    except Exception as e:
        print(f"상세 페이지 크롤링 중 오류 발생: {e}")
        return None
    
# 공고 메인 페이지 크롤링 함수
def get_announcement_list(base_url, start_page=1, end_page=None):
    # 체크포인트 초기화
    checkpoint = CrawlerCheckpoint('socialventure')
    announcements = []
    stop_crawling = False
    
    try:
        page = start_page
        while end_page is None or page <= end_page:
            if stop_crawling:
                break
                
            print(f"\n{'='*50}")
            print(f"현재 {page}페이지 크롤링 시작")
            
            url = f"{base_url}&pageIndex={page}"
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 공고 목록 테이블 찾기
            table = soup.find('table', class_='boardList')
            if table and table.find('tbody'):
                rows = table.find('tbody').find_all('tr')
                
                for row in rows:
                    try:
                        # 공지사항 제외
                        if row.find('span', class_='noticeMark'):
                            continue
                            
                        # 기본 정보 추출
                        cells = row.find_all('td')
                        title_link = cells[1].find('a')
                        title = title_link.text.strip()
                        agency = cells[2].text.strip()
                        status = cells[3].text.strip()  # 모집상태
                        reg_date = cells[4].text.strip()  # 게시일
                        
                        # 이전 수집 데이터와 비교
                        if checkpoint.last_crawled:
                            if (reg_date == checkpoint.last_crawled['last_post_date'] and 
                                title == checkpoint.last_crawled['last_title']):
                                print(f"\n이전 수집 지점 도달. 크롤링 중단")
                                stop_crawling = True
                                break
                        
                        # 상세 페이지 URL 추출 및 데이터 수집
                        onclick = title_link.get('href', '')
                        post_id = re.search(r"'(\d+)'", onclick)
                        if post_id:
                            post_id = post_id.group(1)
                            detail_url = f"https://sv.kibo.or.kr/BoardExecute.do?pageid=BOARD00004&command=View&idx={post_id}"
                            
                            announcement_data = get_announcement_detail(detail_url, headers)
                            if announcement_data:
                                announcement_data.update({
                                    'POSTDATE': reg_date.replace('.', '-'),
                                    'AGENCY': agency,
                                    'LINK': detail_url
                                })
                                announcements.append(announcement_data)
                                
                                # 첫 번째 게시물 수집 후 체크포인트 저장
                                if len(announcements) == 1:
                                    print(f"첫 번째 게시물 수집 완료: {reg_date}, {title}")
                                    checkpoint.save_checkpoint(reg_date, title)
                                
                    except Exception as e:
                        print(f"게시물 처리 중 오류: {e}")
                        continue
                        
                    time.sleep(1)
            
            print(f"{page}페이지 완료 - {len(announcements)}건 수집")
            time.sleep(2)
            page += 1
            
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    
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
def print_checkpoint(site_name='socialventure'):
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
            values = (
                announcement.get('POSTDATE'),
                announcement.get('ANNOUNCEMENT_NUMBER'),
                announcement.get('TITLE'),
                announcement.get('CATEGORY'),
                announcement.get('LOCATION'),
                announcement.get('CONTENT'),
                announcement.get('START'),
                announcement.get('END'),
                announcement.get('AGENCY'),
                announcement.get('LINK'),
                announcement.get('FILE'),
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