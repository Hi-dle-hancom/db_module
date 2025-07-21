"""
HAPA DB Module - 통합 인증 시스템
JWT 토큰 기반 인증 + 보안 강화 기능
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import uuid
import logging

import database
from models import TokenData, UserInDB

# 로거 설정
logger = logging.getLogger(__name__)

# 🔐 JWT 보안 설정 (Backend와 동기화)
def get_secure_secret_key() -> str:
    """Backend와 동일한 방식으로 JWT SECRET_KEY 로드"""
    # Backend config.py와 동일한 기본값 사용
    secret_key = os.getenv("JWT_SECRET_KEY", "HAPA_UNIFIED_SECRET_KEY_FOR_DEVELOPMENT_ONLY_CHANGE_IN_PRODUCTION_32CHARS")
    environment = os.getenv("ENVIRONMENT", "development")
    
    # 🔍 디버깅 정보 출력 (Backend와 비교용)
    logger.info(f"🔐 DB Module JWT SECRET_KEY 로드")
    logger.info(f"🔍 환경: {environment}")
    logger.info(f"🔍 JWT_SECRET_KEY 길이: {len(secret_key)}")
    logger.info(f"🔍 JWT_SECRET_KEY prefix: {secret_key[:20]}...")
    logger.info(f"🔍 환경변수에서 로드: {'YES' if os.getenv('JWT_SECRET_KEY') else 'NO (기본값 사용)'}")
    
    if environment == "production":
        if not os.getenv("JWT_SECRET_KEY"):
            raise ValueError("🚨 [PRODUCTION] JWT_SECRET_KEY 환경변수가 설정되지 않았습니다!")
        if len(secret_key) < 32:
            raise ValueError(f"🚨 [PRODUCTION] JWT_SECRET_KEY는 최소 32자 이상이어야 합니다! 현재 길이: {len(secret_key)}")
    
    if secret_key == "HAPA_UNIFIED_SECRET_KEY_FOR_DEVELOPMENT_ONLY_CHANGE_IN_PRODUCTION_32CHARS":
        if environment == "production":
            raise ValueError("🚨 [PRODUCTION] 기본 개발용 JWT_SECRET_KEY를 사용할 수 없습니다!")
        else:
            logger.warning("⚠️ [DEVELOPMENT] 기본 개발용 JWT_SECRET_KEY 사용 중")
    
    logger.info("✅ DB Module JWT 키 로드 완료")
    return secret_key

try:
    SECRET_KEY = get_secure_secret_key()
    logger.info(f"🔐 JWT 설정 로드됨 - 키 길이: {len(SECRET_KEY)}, 환경: {os.getenv('ENVIRONMENT', 'development')}")
except Exception as e:
    logger.error(f"🚨 JWT 시크릿 키 로드 실패: {e}")
    raise
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# 보안 검증
if ACCESS_TOKEN_EXPIRE_MINUTES > 120:
    raise ValueError(f"🚨 액세스 토큰 만료 기간이 너무 깁니다: {ACCESS_TOKEN_EXPIRE_MINUTES}분 (최대 120분)")

if REFRESH_TOKEN_EXPIRE_DAYS > 30:
    raise ValueError(f"🚨 리프레시 토큰 만료 기간이 너무 깁니다: {REFRESH_TOKEN_EXPIRE_DAYS}일 (최대 30일)")

# 보안 객체
security = HTTPBearer()

# 토큰 관리 클래스
class TokenService:
    """통합 토큰 관리 서비스"""
    
    def __init__(self):
        self.token_blacklist = set()
        self.user_sessions = {}
    
    def create_tokens(self, user_data: Dict[str, Any]) -> Dict[str, str]:
        """액세스 토큰과 리프레시 토큰 생성"""
        session_id = str(uuid.uuid4())
        
        # 액세스 토큰
        access_payload = {
            "sub": user_data["email"],
            "user_id": user_data["user_id"],
            "session_id": session_id,
            "token_type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # 리프레시 토큰
        refresh_payload = {
            "sub": user_data["email"],
            "user_id": user_data["user_id"],
            "session_id": session_id,
            "token_type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        }
        refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # 세션 정보 저장
        self.user_sessions[session_id] = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow(),
            "is_active": True
        }
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """토큰 검증 (블랙리스트 및 세션 확인 포함)"""
        # 블랙리스트 확인
        if token in self.token_blacklist:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰이 무효화되었습니다"
            )
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # 토큰 타입 확인
            if payload.get("token_type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="잘못된 토큰 타입입니다"
                )
            
            # 세션 확인
            session_id = payload.get("session_id")
            if session_id and session_id in self.user_sessions:
                session = self.user_sessions[session_id]
                if not session["is_active"]:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="세션이 만료되었습니다"
                    )
                session["last_used"] = datetime.utcnow()
            
            return payload
            
        except JWTError as e:
            logger.error(f"JWT 토큰 검증 실패: {str(e)}")
            logger.error(f"사용된 SECRET_KEY: {SECRET_KEY[:20]}...")
            logger.error(f"토큰 길이: {len(token)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰 검증에 실패했습니다"
            )
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """리프레시 토큰으로 새로운 액세스 토큰 발급"""
        payload = self.verify_token(refresh_token, "refresh")
        
        new_access_payload = {
            "sub": payload["sub"],
            "user_id": payload["user_id"],
            "session_id": payload["session_id"],
            "token_type": "access",
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        
        new_access_token = jwt.encode(new_access_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    def logout(self, token: str):
        """로그아웃 처리"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            self.token_blacklist.add(token)
            
            session_id = payload.get("session_id")
            if session_id in self.user_sessions:
                self.user_sessions[session_id]["is_active"] = False
                
        except JWTError:
            pass

# 전역 토큰 서비스 인스턴스
token_service = TokenService()

# 하위 호환성을 위한 기존 함수들
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """액세스 토큰 생성 (하위 호환성)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """리프레시 토큰 생성 (하위 호환성)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "token_type": "refresh"
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def add_token_to_blacklist(token: str, reason: str = "logout"):
    """토큰을 블랙리스트에 추가 (하위 호환성)"""
    token_service.token_blacklist.add(token)
    logger.info(f"🚫 토큰 블랙리스트 추가: {token[:20]}... (사유: {reason})")

async def get_user(email: str) -> Optional[UserInDB]:
    """이메일로 사용자 조회"""
    try:
        pool = await database.get_db_pool()
        async with pool.acquire() as connection:
            query = "SELECT id, email, username FROM users WHERE email = $1"
            user_record = await connection.fetchrow(query, email)
            
            if user_record:
                return UserInDB(**dict(user_record))
            return None
            
    except Exception as e:
        logger.error(f"사용자 조회 중 오류: {e}")
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInDB:
    """현재 사용자 인증 및 조회"""
    token = credentials.credentials
    
    # 🔍 디버깅: 받은 토큰 정보 로그
    logger.info(f"🔍 JWT 토큰 검증 시작")
    logger.info(f"🔍 토큰 길이: {len(token)}")
    logger.info(f"🔍 토큰 prefix: {token[:50]}...")
    logger.info(f"🔍 사용할 SECRET_KEY 길이: {len(SECRET_KEY)}")
    logger.info(f"🔍 사용할 SECRET_KEY prefix: {SECRET_KEY[:20]}...")
    
    try:
        # 토큰 검증
        payload = token_service.verify_token(token, "access")
        logger.info(f"✅ JWT 토큰 검증 성공")
        logger.info(f"🔍 토큰 payload: {payload}")
        
        # 사용자 조회
        email = payload.get("sub")
        if not email:
            logger.error("❌ 토큰에서 이메일(sub) 클레임을 찾을 수 없음")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다"
            )
        
        logger.info(f"🔍 토큰에서 추출한 이메일: {email}")
        user = await get_user(email)
        if not user:
            logger.error(f"❌ 데이터베이스에서 사용자를 찾을 수 없음: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="사용자를 찾을 수 없습니다"
            )
        
        logger.info(f"✅ 사용자 인증 성공: {email}")
        return user
        
    except HTTPException as e:
        logger.error(f"❌ JWT 인증 실패 (HTTPException): {e.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ JWT 인증 중 예외 발생: {str(e)}")
        logger.error(f"❌ 예외 타입: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

# 초기화 완료 로그
logger.info(f"✅ 통합 인증 시스템 초기화 완료 (환경: {os.getenv('ENVIRONMENT', 'development')})")