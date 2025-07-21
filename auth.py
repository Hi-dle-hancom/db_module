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

# 보안 강화된 JWT 관리자 import
from secure_jwt_manager import jwt_manager

# JWT 보안 설정
try:
    SECRET_KEY = jwt_manager.get_jwt_secret_key()
    
    # JWT 설정 검증
    validation_result = jwt_manager.validate_jwt_setup()
    
    if validation_result['status'] == 'critical':
        raise ValueError(f"🚨 JWT 설정 치명적 오류: {validation_result['issues']}")
    elif validation_result['status'] == 'warning':
        for issue in validation_result['issues']:
            logger.warning(f"⚠️ JWT 설정 경고: {issue}")
    
    # 키 정보 로그 (보안 정보 제외)
    key_info = jwt_manager.get_key_info()
    logger.info(f"🔐 JWT 설정 로드됨 - ID: {key_info['key_id']}, 길이: {key_info['key_length']}, 환경: {key_info['environment']}")
    
    if key_info['is_temporary']:
        logger.warning("🔶 임시 JWT 키 사용 중. 운영 환경에서는 고정 키를 사용하세요!")
    
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
    
    # 토큰 검증
    payload = token_service.verify_token(token, "access")
    
    # 사용자 조회
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다"
        )
    
    user = await get_user(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다"
        )
    
    return user

# 초기화 완료 로그
logger.info(f"✅ 통합 인증 시스템 초기화 완료 (환경: {os.getenv('ENVIRONMENT', 'development')})")