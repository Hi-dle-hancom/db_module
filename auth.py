from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os

import database
from models import TokenData, UserInDB

# --- JWT 설정 (환경변수 사용) - 보안 강화 ---
def get_secure_secret_key() -> str:
    """JWT SECRET_KEY를 안전하게 가져오는 함수"""
    secret_key = os.getenv("JWT_SECRET_KEY")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # 운영 환경에서는 반드시 환경 변수 설정 필요
    if environment == "production":
        if not secret_key:
            raise ValueError(
                "🚨 [PRODUCTION] JWT_SECRET_KEY 환경변수가 설정되지 않았습니다! "
                "보안을 위해 반드시 설정해야 합니다."
            )
        if len(secret_key) < 32:
            raise ValueError(
                "🚨 [PRODUCTION] JWT_SECRET_KEY는 최소 32자 이상이어야 합니다! "
                f"현재 길이: {len(secret_key)}"
            )
        # 운영 환경에서 기본값 사용 방지
        if secret_key in ["YOUR_VERY_SECRET_KEY_FOR_PASSWORDLESS_AUTH", "test", "dev", "secret"]:
            raise ValueError(
                "🚨 [PRODUCTION] 안전하지 않은 SECRET_KEY가 감지되었습니다! "
                "복잡하고 고유한 키를 사용하세요."
            )
    
    # 개발 환경에서도 기본값 사용 시 경고
    if not secret_key:
        import warnings
        warnings.warn(
            "⚠️ [DEVELOPMENT] JWT_SECRET_KEY가 설정되지 않아 기본값을 사용합니다. "
            "운영 환경에서는 반드시 설정하세요!",
            UserWarning
        )
        return "HAPA_DEV_SECRET_KEY_FOR_DEVELOPMENT_ONLY_CHANGE_IN_PRODUCTION_32CHARS"
    
    return secret_key

SECRET_KEY = get_secure_secret_key()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "365"))

# 추가 보안 검증
if ACCESS_TOKEN_EXPIRE_DAYS > 365:
    raise ValueError(f"🚨 토큰 만료 기간이 너무 깁니다: {ACCESS_TOKEN_EXPIRE_DAYS}일 (최대 365일)")

print(f"✅ JWT 인증 시스템 초기화 완료 (환경: {os.getenv('ENVIRONMENT', 'development')})")

# 헤더에서 'Authorization' 값을 가져오는 새로운 방식
api_key_header = APIKeyHeader(name="Authorization")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # 긴 유효기간을 기본값으로 설정
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_user(email: str) -> Optional[UserInDB]:
    """이메일로 사용자를 조회합니다. (비밀번호 없음)"""
    pool = await database.get_db_pool()
    async with pool.acquire() as connection:
        query = "SELECT id, email, username FROM users WHERE email = $1"
        user_record = await connection.fetchrow(query, email)
        if user_record:
            # --- 여기를 수정합니다 ---
            # 기존: return UserInDB.from_orm(user_record)
            # 수정: asyncpg.Record 객체를 dict로 변환 후 Pydantic 모델 생성
            return UserInDB(**dict(user_record))
            # ---------------------
    return None

async def get_current_user(token: str = Depends(api_key_header)):
    """토큰을 검증하여 현재 사용자를 식별합니다."""
    # 클라이언트가 보낸 "Bearer <token>" 형식에서 "Bearer " 부분을 제거
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = await get_user(token_data.email)
    if user is None:
        raise credentials_exception
    return user