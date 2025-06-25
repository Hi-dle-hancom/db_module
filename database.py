import asyncpg
import os
from typing import Optional
from dotenv import load_dotenv

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
    if not DATABASE_URL:
        return {"error": "DATABASE_URL not set"}
    
    try:
        # postgresql://user:pass@host:port/db 파싱
        url_parts = DATABASE_URL.replace("postgresql://", "").split("@")
        user_part = url_parts[0].split(":")[0]  # 사용자명만
        host_db_part = url_parts[1]
        host_port = host_db_part.split("/")[0]
        database = host_db_part.split("/")[1]
        
        return {
            "host": host_port,
            "database": database,
            "user": user_part,
            "connection_status": "configured" if pool else "not_connected"
        }
    except Exception as e:
        return {"error": f"Failed to parse DATABASE_URL: {e}"}

# 환경변수에서 데이터베이스 URL 로드 (보안 강화)
DATABASE_URL = os.getenv("DATABASE_URL")

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

print(f"🔗 데이터베이스 연결 정보 로드 완료: {_extract_host_from_url(DATABASE_URL)}")

pool: Optional[asyncpg.Pool] = None

async def get_db_pool() -> asyncpg.Pool:
    """데이터베이스 커넥션 풀을 반환합니다."""
    if pool is None:
        raise RuntimeError("데이터베이스 커넥션 풀이 초기화되지 않았습니다. connect_to_db()를 먼저 호출하세요.")
    return pool

async def connect_to_db():
    """애플리케이션 시작 시 데이터베이스 커넥션 풀을 생성합니다."""
    global pool
    try:
        print(f"🔗 데이터베이스 연결 풀 생성 중... (Host: {_extract_host_from_url(DATABASE_URL)})")
        
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
            
        print(f"✅ 데이터베이스 연결 풀 생성 완료!")
        print(f"   📊 데이터베이스: {db_name}")
        print(f"   👤 사용자: {user_name}")
        print(f"   🔧 연결 풀 크기: 2-10")
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {type(e).__name__}: {e}")
        print(f"   🔍 연결 정보: {_extract_host_from_url(DATABASE_URL)}")
        raise

async def close_db_connection():
    """애플리케이션 종료 시 데이터베이스 커넥션 풀을 닫습니다."""
    global pool
    if pool:
        await pool.close()
        print("✅ 데이터베이스 커넥션 풀이 정상 종료되었습니다.")
    else:
        print("⚠️ 데이터베이스 커넥션 풀이 이미 종료되었거나 초기화되지 않았습니다.")
