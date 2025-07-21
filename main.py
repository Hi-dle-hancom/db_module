"""
HAPA DB Module - 메인 애플리케이션
사용자 관리 및 개인화 설정 마이크로서비스
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import logging

# 환경변수 로드
load_dotenv(".env")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 모듈 import
import database
from routers import auth_router, settings_router, users_router, admin_router, history_router

# FastAPI 앱 생성
app = FastAPI(
    title="HAPA DB Module API",
    description="사용자 관리 및 개인화 설정 마이크로서비스",
    version="1.0.0"
)

# CORS 설정
cors_origins = [
    "http://3.13.240.111:3000",  # React Landing Page
    "http://3.13.240.111:8000",  # Backend API
    "vscode://*",                # VSCode Extension
    "vscode-webview://*"         # VSCode WebView
]

if os.getenv("ENVIRONMENT") == "development":
    cors_origins.extend([
        "http://localhost:3000", 
        "http://localhost:8000", 
        "http://localhost:8001"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(settings_router)
app.include_router(users_router)
app.include_router(admin_router)
app.include_router(history_router)

# 애플리케이션 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 시 실행"""
    await database.connect_to_db()
    logger.info("🚀 HAPA DB Module 서버가 시작되었습니다.")

@app.on_event("shutdown") 
async def shutdown_event():
    """애플리케이션 종료 시 실행"""
    await database.close_db_connection()
    logger.info("👋 HAPA DB Module 서버가 종료되었습니다.")

# 기본 엔드포인트
@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "message": "HAPA DB Module API is running!",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    health_status = {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "databases": {}
    }
    
    # PostgreSQL 상태 확인
    try:
        pool = await database.get_db_pool()
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
        health_status["databases"]["postgresql"] = "connected"
    except Exception as e:
        health_status["databases"]["postgresql"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # MongoDB 상태 확인 (선택적)
    try:
        mongo_client = await database.get_mongo_client()
        await mongo_client.admin.command('ping')
        health_status["databases"]["mongodb"] = "connected"
    except Exception as e:
        health_status["databases"]["mongodb"] = f"error: {str(e)}"
        # MongoDB는 선택적이므로 전체 상태에 영향 없음
    
    # 전체 상태가 healthy가 아닌 경우 503 반환
    if health_status["status"] != "healthy":
        raise HTTPException(
            status_code=503,
            detail=health_status
        )
    
    return health_status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8001")),
        reload=os.getenv("ENVIRONMENT") == "development"
    )

