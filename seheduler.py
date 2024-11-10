from apscheduler.schedulers.blocking import BlockingScheduler
import importlib
import logging
from datetime import datetime

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

def run_crawler(site_name):
   """각 사이트별 크롤러 실행"""
   try:
       logger.info(f"{site_name} 크롤러 시작")
       
       # 동적으로 크롤러 모듈 import
       crawler = importlib.import_module(f'Crawlers.{site_name}')
       crawler.run()
       
       logger.info(f"{site_name} 크롤러 완료")
       
   except Exception as e:
       logger.error(f"{site_name} 크롤링 중 오류 발생: {e}")

def main():
   scheduler = BlockingScheduler()
   
   # 크롤러 목록
   sites = ['중소벤처기업부', '소셜벤쳐스퀘어', '창조경제혁신센터', 'iris', '기업마당', 'kstartup']  # 크롤러 파일명 (확장자 제외)
   
   for site in sites:
       # 매일 오전 9시에 실행
       scheduler.add_job(
           run_crawler, 
           'cron', 
           hour=17,
           minute=58,
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