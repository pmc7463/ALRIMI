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
    print_checkpoint('Bizinfo')
    
    print("기업마당 크롤링 시작...")
    base_url = "https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/list.do"
    
    # 데이터 수집
    #announcements = get_announcement_list(base_url, start_page=1, end_page=1)
    announcements = get_announcement_list(base_url, start_page=1, end_page=None)

    print("\n최종 결과:")
    print(f"총 {len(announcements)}개의 공고 수집 완료")
    
    # DB 저장
    connection = connect_to_database()
    if connection:
        insert_into_db(connection, announcements)
        connection.close()
    
    # 크롤링 후 체크포인트 확인
    print_checkpoint('Bizinfo')
    
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

def get_announcement_detail(url, headers):
    """공고 상세 페이지 크롤링"""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
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
            'FILE': None
        }
        
        # 제목 추출
        title_element = soup.select_one('div.view_cont_tit')
        if title_element:
            data['TITLE'] = clean_content(title_element.text.strip())
            
        # 내용 추출 - 사업개요만
        overview_element = soup.find('span', class_='s_title', string='사업개요')
        if overview_element:
            content_div = overview_element.find_next('div', class_='txt')
            if content_div:
                data['CONTENT'] = clean_content(content_div.text.strip())
        
        # 신청기간 추출
        period_element = soup.find('span', class_='s_title', string='신청기간')
        if period_element:
            period_txt = period_element.find_next('div', class_='txt')
            if period_txt:
                period = period_txt.text.strip()
                if '~' in period:
                    start, end = period.split('~')
                    data['START'] = extract_date(start.strip())
                    data['END'] = extract_date(end.strip())
                else:
                    # 상시접수 등의 문자열인 경우
                    data['START'] = period
        
        # 첨부파일 추출
        file_names = []
        for file_div in soup.select('div.file_name'):
            file_name = file_div.text.strip()
            if file_name:
                file_names.append(file_name)
        if file_names:
            data['FILE'] = ', '.join(file_names)

        # 기관 정보 추출
        agency_element = soup.find('span', class_='s_title', string='지원기관')
        if agency_element:
            agency_txt = agency_element.find_next('div', class_='txt')
            if agency_txt:
                data['AGENCY'] = agency_txt.text.strip()

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

def get_announcement_list(base_url, start_page=1, end_page=None):
    """공고 목록 수집"""
    checkpoint = CrawlerCheckpoint('bizinfo')
    announcements = []
    stop_crawling = False
    
    try:
        page = start_page
        while end_page is None or page <= end_page:
            if stop_crawling:
                break
                
            print(f"\n{'='*50}")
            print(f"현재 {page}페이지 크롤링 시작")
            
            try:
                url = f"{base_url}?rows=15&cpage={page}"
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # HTML 구조에 맞게 선택자 수정
                rows = soup.select("tbody tr")  # tbody 내의 모든 tr 선택
                
                if not rows:
                    print("더 이상 공고가 없습니다.")
                    break
                    
                print(f"찾은 공고 개수: {len(rows)}")
                
                for row in rows:
                    try:
                        # 각 컬럼 데이터 추출
                        cols = row.select("td")
                        if len(cols) < 7:
                            continue
                            
                        reg_date = cols[6].text.strip()  # 등록일
                        title_element = cols[2].select_one("a")  # 제목 및 링크
                        if not title_element:
                            continue
                            
                        title = title_element.text.strip()
                        category = cols[1].text.strip()  # 카테고리
                        
                        print(f"현재 처리 중: {reg_date}, {title}")
                        
                        # 체크포인트 비교
                        if checkpoint.last_crawled:
                            last_date = checkpoint.last_crawled['last_post_date']
                            last_title = checkpoint.last_crawled['last_title']
                            
                            if reg_date == last_date and title == last_title:
                                print(f"\n이전 수집 지점 도달. 크롤링 중단")
                                stop_crawling = True
                                break
                        
                        # 첫 번째 게시물 체크포인트 저장
                        if page == start_page and len(announcements) == 0:
                            print(f"체크포인트 저장: {reg_date}, {title}")
                            checkpoint.save_checkpoint(reg_date, title)
                        
                        # href 속성에서 공고 ID 추출
                        href = title_element.get('href', '')
                        if 'pblancId=' not in href:
                            continue
                            
                        pblanc_id = href.split('pblancId=')[1].split('&')[0] if '&' in href else href.split('pblancId=')[1]
                        detail_url = f"https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/view.do?pblancId={pblanc_id}"
                        
                        print(f"\n수집 시도: {title}")
                        print(f"URL: {detail_url}")
                        
                        # 상세 페이지 데이터 수집
                        try:
                            announcement_data = get_announcement_detail(detail_url, headers)
                            if announcement_data:
                                # 기본 정보 업데이트 (location은 제외)
                                announcement_data.update({
                                    'POSTDATE': reg_date,
                                    'CATEGORY': category,
                                    'TITLE': title,
                                    'LINK': detail_url,
                                    'AGENCY': cols[5].text.strip() if len(cols) > 5 else None
                                })
                                announcements.append(announcement_data)
                                print(f"수집 완료: {title}")
                        except Exception as e:
                            print(f"상세 페이지 처리 중 오류: {e}")
                            continue
                            
                        time.sleep(1)
                        
                    except Exception as e:
                        print(f"게시물 처리 중 오류: {e}")
                        continue
                
                if not stop_crawling:
                    # 다음 페이지 존재 여부 확인
                    next_page = soup.select_one(f"div.page_wrap a[title='{page + 1}페이지']")
                    if not next_page:
                        print("마지막 페이지입니다.")
                        break
                        
                    print(f"{page}페이지 완료 - {len(announcements)}건 수집")
                    time.sleep(2)
                    page += 1
                    
            except requests.exceptions.RequestException as e:
                print(f"페이지 요청 중 오류: {e}")
                break
                
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    
    print(f"수집 완료 - 총 {len(announcements)}건")
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
        # 절대 경로로 변경
        self.checkpoint_dir = '/home/pmc/work_space/ALRIMI/Crawlers/checkpoints'
        self.checkpoint_file = os.path.join(self.checkpoint_dir, f'{site_name}_last_crawled.json')
        self.last_crawled = self.load_checkpoint()
        
    def load_checkpoint(self):
        """체크포인트 파일 로드"""
        try:
            if not os.path.exists(self.checkpoint_dir):
                os.makedirs(self.checkpoint_dir)
                print(f"체크포인트 디렉토리 생성: {self.checkpoint_dir}")
            
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"체크포인트 로드 중 오류: {e}")
        return None
        
    def save_checkpoint(self, post_date, title):
        """최신 크롤링 정보 저장"""
        try:
            checkpoint_data = {
                'last_post_date': post_date,
                'last_title': title,
                'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if not os.path.exists(self.checkpoint_dir):
                os.makedirs(self.checkpoint_dir)
                print(f"체크포인트 디렉토리 생성: {self.checkpoint_dir}")
            
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            self.last_crawled = checkpoint_data
            print(f"체크포인트 저장 완료: {self.checkpoint_file}")
            
        except Exception as e:
            print(f"체크포인트 저장 중 오류: {e}")
            print(f"시도한 경로: {self.checkpoint_file}")
            raise

# 체크포인트 확인을 위한 함수 추가
def print_checkpoint(site_name='Bizinfo'):
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
                LINK, FILE
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, 
                %s, %s, %s
            )
        """
        
        for announcement in announcements:
            # 각 필드에 대해 길이 제한 설정
            announcement_number = announcement.get('ANNOUNCEMENT_NUMBER')
            if announcement_number and len(announcement_number) > 50:
                announcement_number = announcement_number[:50]

            title = announcement.get('TITLE')
            if title and len(title) > 300:
                title = title[:300]

            category = announcement.get('CATEGORY')
            if category and len(category) > 20:
                category = category[:20]

            content = announcement.get('CONTENT')
            if content and len(content) > 4000:
                content = content[:4000]

            start = announcement.get('START')
            if start and len(start) > 10:
                start = start[:10]

            agency = announcement.get('AGENCY')
            if agency and len(agency) > 100:
                agency = agency[:100]

            link = announcement.get('LINK')
            if link and len(link) > 300:
                link = link[:300]

            file = announcement.get('FILE')
            if file and len(file) > 200:
                file = file[:200]

            values = (
                announcement.get('POSTDATE'),
                announcement_number,
                title,
                category,
                announcement.get('LOCATION'),
                content,
                start,
                announcement.get('END'),
                agency,
                link,
                file
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