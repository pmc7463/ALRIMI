import logging

# 로깅 설정을 가장 먼저 실행
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


from fastapi import FastAPI
from Project.api.endpoints import announcement, proposal, recommendation

# FastAPI 앱 시작 로그
logger.debug("FastAPI 애플리케이션 시작")

app = FastAPI(
    title="ALRIMI API",
    description="사업공고 및 제안서 생성 API",
    version="1.0.0"
)

###
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 정적 파일 제공 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 테스트 페이지 라우트
@app.get("/test")
async def get_test_form():
    return FileResponse("static/test_form.html")

@app.get("/test/recommendation")
async def get_recommendation_test():
    return FileResponse("static/recommendation_test.html")
###

app.include_router(
    announcement.router, 
    prefix="/api/v1", 
    tags=["announcements"]
)

app.include_router(
    proposal.router,
    prefix="/api/v1",
    tags=["proposals"]
)

app.include_router(             
    recommendation.router,
    prefix="/api/v1",
    tags=["recommendations"]
)

if __name__ == "__main__":
    import uvicorn
    logger.info("서버 시작 중...")
    uvicorn.run(app, host="0.0.0.0", port=8001)