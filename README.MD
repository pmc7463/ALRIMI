# 알리미 개발 노트
## 주제
1. 사업 공고문 추천
2. 제안서 작성 어시스트

---
## 사업 공고문 DB 구축
### 공통 
1. 각 사이트마다 크롤링 프로그램 작성
2. 수집할 때 "타이틀", "내용", "에이전시" 등에서 지역을 추출 후 카운팅하여 위치 데이터로 활용
    - 제목 - "서울"+1, 내용 - "서울"+1
    - 매칭 안 될 경우 전국 또는 기타(논의 내용)
3. 수집된 데이터는 한 DB에 저장
4. 여러 사이트에서 수집된 사업 공고문은 중복이 존재하기 때문에 중복 제거 단계가 필요
    - 중복 제거 알고리즘 고려
    - 자카드 유사도, TF-IDF, KoBERT
5. 사업 공고문은 매일 올라오기 때문에 매일 정해진 시간을 지정해서 자동 수집이 필요
6. 매일 각 수집기 프로그램이 실행되기 때문에 새롭게 올라온 공고문도 있지만 어제 수집해서 DB에 저장된 데이터도 있기 때문에 중복을 막고자 각 사이트 마다 게시일을 수집해서 막기
    - DB에 저장하기 전에 검토 단계가 필요
7. DB Colum 순서
    1) ID (Primary key) (수집안해도됨 DB에서 자동 증감)
    2) POSTDATE (등록일 or 게시일)
    3) TITLE
    4) CATEGORY (없으면 NULL)
    5) LOCATION (기본 "전국")
    6) CONTENT
    7) START (예산소진시 or 선착순 접수 등의 값이 들어올 때는 NULL)
    8) END (예산소진시 or 선착순 접수가 들어올 수 있음)
    9) AGENCY
    10) LINK
    11) FILE (없으면 NULL)
8. 공고번호 크롤링 어려움(중소벤처기업부 가능, 기업마당 없음, K-startup 유동적)

### 1. 중소벤처기업부