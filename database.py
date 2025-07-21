"""
HAPA DB Module - 데이터베이스 연결 및 관리
PostgreSQL 및 MongoDB 연결 풀 관리와 쿼리 실행을 담당합니다.
"""

import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

import asyncpg
from fastapi import FastAPI
from dotenv import load_dotenv

# 🔧 선택적 MongoDB 지원 (의존성 실패 시에도 기본 기능은 동작)
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
    MOTOR_AVAILABLE = True
    print("✅ Motor(MongoDB) 의존성 로드됨")
except ImportError as e:
    print(f"⚠️ Motor(MongoDB) 없음: {e} - PostgreSQL만 사용")
    MOTOR_AVAILABLE = False
    # 더미 클래스 (import 에러 방지)
    class AsyncIOMotorClient:
        pass
    class AsyncIOMotorDatabase:
        pass
    class ServerSelectionTimeoutError(Exception):
        pass
    class ConfigurationError(Exception):
        pass

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 환경변수 파일 명시적 로드
load_dotenv()

def _extract_host_from_url(url: str) -> str:
    """URL에서 호스트명만 추출 (로깅용, 보안을 위해 비밀번호 제외)"""
    try:
        # postgresql://user:pass@host:port/db -> host:port 추출
        parts = url.split("@")[1].split("/")[0]
        return parts
    except (IndexError, AttributeError):
        return "unknown"

def get_database_info() -> dict:
    """데이터베이스 연결 정보 반환 (디버깅용, 비밀번호는 마스킹)"""
    result = {}
    
    # PostgreSQL 정보
    if DATABASE_URL:
        try:
            # postgresql://user:pass@host:port/db 파싱
            url_parts = DATABASE_URL.replace("postgresql://", "").split("@")
            user_part = url_parts[0].split(":")[0]  # 사용자명만
            host_db_part = url_parts[1]
            host_port = host_db_part.split("/")[0]
            database = host_db_part.split("/")[1]
            
            result["postgresql"] = {
                "host": host_port,
                "database": database,
                "user": user_part,
                "connection_status": "connected" if pool else "not_connected"
            }
        except Exception as e:
            result["postgresql"] = {"error": f"Failed to parse DATABASE_URL: {e}"}
    else:
        result["postgresql"] = {"error": "DATABASE_URL not set"}
    
    # MongoDB 정보
    if MONGODB_URL:
        try:
            # mongodb://user:pass@host:port/db 파싱
            if "@" in MONGODB_URL:
                url_parts = MONGODB_URL.split("@")
                user_part = url_parts[0].split("://")[1].split(":")[0]  # 사용자명만
                host_db_part = url_parts[1]
            else:
                user_part = "none"
                host_db_part = MONGODB_URL.split("://")[1]
            
            host_port = host_db_part.split("/")[0]
            database = "hapa"  # 기본값
            if "/" in host_db_part and host_db_part.split("/")[1]:
                database = host_db_part.split("/")[1].split("?")[0]
            
            result["mongodb"] = {
                "host": host_port,
                "database": database,
                "user": user_part,
                "connection_status": "connected" if mongo_client else "not_connected"
            }
        except Exception as e:
            result["mongodb"] = {"error": f"Failed to parse MONGODB_URL: {e}"}
    else:
        result["mongodb"] = {"status": "not_configured"}
    
    return result

# 환경변수에서 데이터베이스 URL 로드 (보안 강화)
DATABASE_URL = os.getenv("DATABASE_URL")
MONGODB_URL = os.getenv("MONGODB_URL")

# 데이터베이스 타입 결정
DATABASE_TYPE = os.getenv("DATABASE_TYPE", "postgresql")  # 기본값: postgresql

# 환경변수 검증 (필수)
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL 환경변수가 설정되지 않았습니다. "
        "다음 형식으로 설정해주세요: postgresql://username:password@host:port/database"
    )

# 연결 정보 검증
if not DATABASE_URL.startswith("postgresql://"):
    raise ValueError(
        "DATABASE_URL은 postgresql:// 형식이어야 합니다. "
        f"현재 값: {DATABASE_URL[:20]}..."
    )

# MongoDB 설정 검증 (MongoDB 사용 시)
if MONGODB_URL:
    if not MONGODB_URL.startswith("mongodb://"):
        raise ValueError(
            "MONGODB_URL은 mongodb:// 형식이어야 합니다. "
            f"현재 값: {MONGODB_URL[:20]}..."
        )
    logger.info(f"🔗 MongoDB 연결 정보 로드 완료: {_extract_host_from_url(MONGODB_URL)}")

logger.info(f"🔗 PostgreSQL 연결 정보 로드 완료: {_extract_host_from_url(DATABASE_URL)}")

# 연결 풀 변수들
pool: Optional[asyncpg.Pool] = None
mongo_client: Optional[AsyncIOMotorClient] = None
mongo_db: Optional[AsyncIOMotorDatabase] = None

async def get_db_pool() -> asyncpg.Pool:
    """PostgreSQL 데이터베이스 커넥션 풀을 반환합니다."""
    if pool is None:
        raise RuntimeError("PostgreSQL 커넥션 풀이 초기화되지 않았습니다. connect_to_db()를 먼저 호출하세요.")
    return pool

async def get_mongo_db() -> AsyncIOMotorDatabase:
    """MongoDB 데이터베이스 인스턴스를 반환합니다."""
    if not MOTOR_AVAILABLE:
        return None  # MongoDB 없는 경우 None 반환
    if mongo_db is None:
        raise RuntimeError("MongoDB 연결이 초기화되지 않았습니다. connect_to_db()를 먼저 호출하세요.")
    return mongo_db

async def get_mongo_client() -> AsyncIOMotorClient:
    """MongoDB 클라이언트 인스턴스를 반환합니다."""
    if not MOTOR_AVAILABLE:
        return None  # MongoDB 없는 경우 None 반환
    if mongo_client is None:
        raise RuntimeError("MongoDB 클라이언트가 초기화되지 않았습니다. connect_to_db()를 먼저 호출하세요.")
    return mongo_client

async def connect_to_db():
    """애플리케이션 시작 시 데이터베이스 커넥션 풀을 생성합니다."""
    global pool, mongo_client, mongo_db
    
    # PostgreSQL 연결
    try:
        logger.info(f"🔗 PostgreSQL 연결 풀 생성 중... (Host: {_extract_host_from_url(DATABASE_URL)})")
        
        # 연결 풀 설정 최적화
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,           # 최소 연결 수
            max_size=10,          # 최대 연결 수
            timeout=30,           # 연결 타임아웃
            command_timeout=60    # 명령 타임아웃
        )
        
        # 연결 테스트
        async with pool.acquire() as connection:
            db_name = await connection.fetchval("SELECT current_database()")
            user_name = await connection.fetchval("SELECT current_user")
            
        logger.info(f"✅ PostgreSQL 연결 풀 생성 완료!")
        logger.info(f"   📊 데이터베이스: {db_name}")
        logger.info(f"   👤 사용자: {user_name}")
        logger.info(f"   🔧 연결 풀 크기: 2-10")
        
    except Exception as e:
        logger.error(f"❌ PostgreSQL 연결 실패: {type(e).__name__}: {e}")
        logger.error(f"   🔍 연결 정보: {_extract_host_from_url(DATABASE_URL)}")
        raise
    
    # MongoDB 연결 (선택적)
    if MONGODB_URL:
        try:
            logger.info(f"🔗 MongoDB 연결 생성 중... (Host: {_extract_host_from_url(MONGODB_URL)})")
            
            # MongoDB 클라이언트 생성
            mongo_client = AsyncIOMotorClient(
                MONGODB_URL,
                serverSelectionTimeoutMS=10000,  # 10초 타임아웃
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                minPoolSize=2
            )
            
            # 데이터베이스 선택 (URL에서 추출 또는 기본값)
            db_name = "hapa"  # 기본 데이터베이스 이름
            if "/" in MONGODB_URL:
                url_parts = MONGODB_URL.split("/")
                if len(url_parts) > 3 and url_parts[-1]:
                    # URL에 데이터베이스 이름이 있는 경우
                    db_name = url_parts[-1].split("?")[0]  # 쿼리 파라미터 제거
            
            mongo_db = mongo_client[db_name]
            
            # 연결 테스트
            await mongo_client.admin.command('ping')
            server_info = await mongo_client.server_info()
            
            logger.info(f"✅ MongoDB 연결 생성 완료!")
            logger.info(f"   📊 데이터베이스: {db_name}")
            logger.info(f"   🔧 MongoDB 버전: {server_info.get('version', 'unknown')}")
            logger.info(f"   🔧 연결 풀 크기: 2-10")
            
        except (ServerSelectionTimeoutError, ConfigurationError) as e:
            logger.error(f"❌ MongoDB 연결 실패: {type(e).__name__}: {e}")
            logger.error(f"   🔍 연결 정보: {_extract_host_from_url(MONGODB_URL)}")
            # MongoDB 연결 실패는 치명적이지 않음 (선택적 기능)
            logger.warning("⚠️ MongoDB 연결에 실패했지만 애플리케이션을 계속 실행합니다.")
        except Exception as e:
            logger.error(f"❌ MongoDB 연결 중 예상치 못한 오류: {type(e).__name__}: {e}")
            logger.warning("⚠️ MongoDB 연결에 실패했지만 애플리케이션을 계속 실행합니다.")
    else:
        logger.info("ℹ️ MONGODB_URL이 설정되지 않아 MongoDB 연결을 건너뜁니다.")

async def close_db_connection():
    """애플리케이션 종료 시 데이터베이스 커넥션 풀을 닫습니다."""
    global pool, mongo_client, mongo_db
    
    # PostgreSQL 연결 종료
    if pool:
        await pool.close()
        logger.info("✅ PostgreSQL 커넥션 풀이 정상 종료되었습니다.")
    else:
        logger.warning("⚠️ PostgreSQL 커넥션 풀이 이미 종료되었거나 초기화되지 않았습니다.")
    
    # MongoDB 연결 종료
    if mongo_client:
        mongo_client.close()
        mongo_db = None
        logger.info("✅ MongoDB 클라이언트가 정상 종료되었습니다.")
    else:
        logger.info("ℹ️ MongoDB 클라이언트가 이미 종료되었거나 초기화되지 않았습니다.")
