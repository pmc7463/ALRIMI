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
from typing import List, Dict, Optional

def run():
    """크롤러 메인 함수"""
    # 실행 전 체크포인트 확인
    print_checkpoint('kstartup')
    
    print("K-Startup 크롤링 시작...")
    base_url = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
    
    # 데이터 수집
    announcements = get_announcement_list(base_url, start_page=1, end_page=None)
    
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
def get_announcement_detail_selenium(driver):
    """Selenium을 사용한 상세 페이지 데이터 추출"""
    try:
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
            'LINK': driver.current_url,
            'FILE': None
        }

        # 제목 추출
        try:
            title_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".title h3"))
            )
            if title_elem:
                data['TITLE'] = title_elem.text.strip()
        except:
            pass

        # 카테고리(지원분야) 추출
        try:
            category_elems = driver.find_elements(By.CSS_SELECTOR, ".dot_list")
            for elem in category_elems:
                label = elem.find_element(By.CSS_SELECTOR, ".tit").text.strip()
                if "지원분야" in label:
                    value = elem.find_element(By.CSS_SELECTOR, ".txt").text.strip()
                    data['CATEGORY'] = value
                    break
        except:
            pass
        
        # CONTENT 추출
        data['CONTENT'] = extract_clean_content(driver)

        # 지역 추출
        info_items = driver.find_elements(By.CSS_SELECTOR, '.dot_list')
        for item in info_items:
            try:
                label = item.find_element(By.CSS_SELECTOR, '.tit').text.strip()
                value = item.find_element(By.CSS_SELECTOR, '.txt').text.strip()
                
                if '지원분야' in label:
                    data['CATEGORY'] = value
                elif '기관명' in label:
                    data['AGENCY'] = value
                elif '지역' in label:
                    data['LOCATION'] = simplify_location(value)
            except:
                continue

        # 담당부서(AGENCY) 추출
        try:
            agency_elems = driver.find_elements(By.CSS_SELECTOR, ".dot_list")
            for elem in agency_elems:
                label = elem.find_element(By.CSS_SELECTOR, ".tit").text.strip()
                if "담당부서" in label:
                    value = elem.find_element(By.CSS_SELECTOR, ".txt").text.strip()
                    data['AGENCY'] = value
                    break
        except:
            pass

        # 신청기간 추출
        try:
            period_elems = driver.find_elements(By.CSS_SELECTOR, ".dot_list")
            for elem in period_elems:
                label = elem.find_element(By.CSS_SELECTOR, ".tit").text.strip()
                if "접수기간" in label:
                    value = elem.find_element(By.CSS_SELECTOR, ".txt").text.strip()
                    if '~' in value:
                        start_date, end_date = value.split('~')
                        data['START'] = start_date.split()[0].strip()  # 시간 제거
                        data['END'] = end_date.split()[0].strip()  # 시간 제거
                    break
        except:
            pass

        # 사업개요(CONTENT) 추출
        try:
            content_elems = driver.find_elements(By.CSS_SELECTOR, ".information_list")
            for elem in content_elems:
                title = elem.find_element(By.CSS_SELECTOR, ".title").text.strip()
                if "사업개요" in title:
                    content = elem.find_element(By.CSS_SELECTOR, ".txt").text.strip()
                    data['CONTENT'] = content
                    break
        except:
            pass

        # 첨부파일 추출
        try:
            files = []
            file_elems = driver.find_elements(By.CSS_SELECTOR, ".board_file .file_bg")
            for elem in file_elems:
                file_name = elem.get_attribute("title")
                if file_name and file_name.startswith('[첨부파일] '):
                    files.append(file_name.replace('[첨부파일] ', ''))
            if files:
                data['FILE'] = ', '.join(files)
        except:
            pass

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
            
            url = f"{base_url}?schM=&page={page}&schStr=&pbancEndYn=N"
            driver.get(url)
            
            try:
                # 데이터 없음 확인
                no_data = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.notice, .no_data"))
                )
                
                # "등록된 데이터가 없습니다" 텍스트 확인
                if "등록된 데이터가 없습니다" in driver.page_source:
                    print("마지막 페이지 도달. 크롤링 종료.")
                    break
                
            except Exception as e:
                print(f"페이지 로딩 시간 초과: {e}")
                break

            # 한 번에 모든 공고 정보 수집
            items = driver.find_elements(By.CSS_SELECTOR, "li.notice")
            
            if not items:
                print("더 이상 공고가 없습니다.")
                break

            print(f"찾은 공고 개수: {len(items)}")
            
            # 각 항목의 기본 정보 수집
            announcements_data = []
            for item in items:
                try:
                    # 제목 추출
                    title = item.find_element(By.CSS_SELECTOR, ".middle .tit").text.strip()
                    
                    # 등록일자 추출
                    post_date = None
                    info_lists = item.find_elements(By.CSS_SELECTOR, ".bottom .list")
                    for info in info_lists:
                        if "등록일자" in info.text:
                            post_date = info.text.replace("등록일자", "").strip()
                            break
                    
                    if not post_date:
                        continue
                    
                    # 공고 ID 추출
                    pbancSn = None
                    
                    # 1. href에서 추출 시도
                    try:
                        link = item.find_element(By.CSS_SELECTOR, "a[href*='javascript:go_view']")
                        onclick = link.get_attribute('href')
                        if onclick:
                            match = re.search(r'go_view\((\d+)\)', onclick)
                            if match:
                                pbancSn = match.group(1)
                    except:
                        pass
                    
                    # 2. go_view_blank에서 추출 시도
                    if not pbancSn:
                        try:
                            button = item.find_element(By.CSS_SELECTOR, "button[onclick*='go_view_blank']")
                            onclick = button.get_attribute('onclick')
                            if onclick:
                                match = re.search(r'go_view_blank\((\d+)\)', onclick)
                                if match:
                                    pbancSn = match.group(1)
                        except:
                            pass
                    
                    if not pbancSn:
                        continue
                        
                    # 카테고리 추출
                    try:
                        category = item.find_element(By.CSS_SELECTOR, ".top .flag").text.strip()
                    except:
                        category = None
                    
                    announcements_data.append({
                        'title': title,
                        'post_date': post_date,
                        'pbancSn': pbancSn,
                        'category': category
                    })
                    
                except Exception as e:
                    print(f"항목 처리 중 오류: {e}")
                    continue
            
            # 체크포인트 확인 및 데이터 수집
            for data in announcements_data:
                try:
                    print(f"현재 처리 중: {data['post_date']}, {data['title']}")
                    
                    # 체크포인트 비교
                    if checkpoint.last_crawled:
                        if (data['post_date'] == checkpoint.last_crawled['last_post_date'] and 
                            data['title'] == checkpoint.last_crawled['last_title']):
                            print(f"\n이전 수집 지점 도달. 크롤링 중단")
                            stop_crawling = True
                            break
                    
                    detail_url = f"https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do?schM=view&pbancSn={data['pbancSn']}&page={page}&schStr=&pbancEndYn=N"
                    print(f"\n수집 시도: {data['title']}")
                    print(f"URL: {detail_url}")
                    
                    driver.get(detail_url)
                    
                    try:
                        # 상세 페이지 로딩 대기
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".title h3"))
                        )
                    except:
                        print("상세 페이지 로딩 실패")
                        continue
                    
                    announcement_data = get_announcement_detail_selenium(driver)
                    
                    if announcement_data:
                        if page == start_page and len(announcements) == 0:
                            checkpoint.save_checkpoint(data['post_date'], data['title'])
                        
                        announcement_data.update({
                            'POSTDATE': data['post_date'],
                            'CATEGORY': data['category'],
                            'LINK': detail_url
                        })
                        
                        announcements.append(announcement_data)
                        print(f"수집 완료: {data['title']}")
                    
                except Exception as e:
                    print(f"상세 정보 수집 중 오류: {e}")
                    continue
            
            if not stop_crawling:
                print(f"{page}페이지 완료 - {len(announcements)}건 수집")
                page += 1
            
    except Exception as e:
        print(f"크롤링 중 오류 발생: {e}")
    
    finally:
        if driver:
            driver.quit()
    
    return announcements

def extract_clean_content(driver):
    """상세 내용을 추출하고 정제하는 함수"""
    try:
        content_parts = []
        
        # information_list-wrap 내의 모든 섹션 찾기
        sections = driver.find_elements(By.CSS_SELECTOR, ".information_list")
        
        for section in sections:
            try:
                # 섹션 제목 추출
                title = section.find_element(By.CSS_SELECTOR, ".title").text.strip()
                content_parts.append(f"[{title}]")
                
                # 각 항목 추출
                items = section.find_elements(By.CSS_SELECTOR, ".dot_list")
                for item in items:
                    try:
                        # 항목 제목과 내용 추출
                        label_elem = item.find_element(By.CSS_SELECTOR, ".tit")
                        if label_elem:
                            label = label_elem.text.strip()
                            
                            # 내용이 있는 경우에만 추가
                            if not label.startswith('자세한 내용은') and not label.startswith('제출하신 서류는') and not label.startswith('신청 시 요청하는'):
                                content_text = ""
                                
                                # txt 클래스에서 텍스트 추출
                                try:
                                    txt_elem = item.find_element(By.CSS_SELECTOR, ".txt")
                                    content_text = txt_elem.text.strip()
                                except:
                                    pass
                                
                                # list 클래스에서 텍스트 추출
                                try:
                                    list_elem = item.find_element(By.CSS_SELECTOR, ".list")
                                    if not content_text:
                                        content_text = list_elem.text.strip()
                                    else:
                                        content_text += "\n" + list_elem.text.strip()
                                except:
                                    pass
                                
                                if content_text:
                                    # 온라인 접수 링크 제거
                                    content_text = re.sub(r'온라인 접수 : 접수 바로가기', '', content_text)
                                    content_text = content_text.strip()
                                    
                                    if content_text and content_text != "없음":
                                        content_parts.append(f"● {label}: {content_text}")
                    except:
                        continue
                
                content_parts.append("")  # 섹션 사이 빈 줄 추가
                
            except:
                continue
        
        # 최종 내용 정리
        content = "\n".join(content_parts)
        
        # 정제 작업
        content = content.replace("\t", " ")  # 탭 제거
        content = re.sub(r'\n\s*\n', '\n\n', content)  # 연속된 빈 줄 정리
        content = re.sub(r' +', ' ', content)  # 연속된 공백 정리
        content = content.strip()  # 앞뒤 공백 제거
        
        return content
        
    except Exception as e:
        print(f"내용 추출 중 오류 발생: {e}")
        return None


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