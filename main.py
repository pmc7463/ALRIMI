import logging

# 로깅 설정을 가장 먼저 실행
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


from fastapi import FastAPI
from Project.api.endpoints import announcement  # Project 추가

# FastAPI 앱 시작 로그
logger.debug("FastAPI 애플리케이션 시작")

app = FastAPI(
    title="ALRIMI API",
    description="사업공고 및 제안서 생성 API",
    version="1.0.0"
)

app.include_router(
    announcement.router, 
    prefix="/api/v1", 
    tags=["announcements"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)