"""
HAPA DB Module - 인증 관련 라우터
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from jose import jwt, JWTError
import logging

import auth
import database
from models import UserBase, UserInDB, Token

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

@router.post("/login", response_model=Token)
async def login_user(user_data: UserBase):
    """사용자 로그인 API"""
    try:
        # 기존 사용자 조회
        user = await auth.get_user(user_data.email)
        
        if not user:
            # 신규 사용자 생성
            logger.info(f"신규 사용자 생성 시작: {user_data.email}")
            
            pool = await database.get_db_pool()
            async with pool.acquire() as connection:
                query = "INSERT INTO users (email, username) VALUES ($1, $2) RETURNING id, email, username"
                created_user_record = await connection.fetchrow(query, user_data.email, user_data.username)
                user = UserInDB(**dict(created_user_record))
                logger.info(f"신규 사용자 생성 완료: {user.email}")
        else:
            logger.info(f"기존 사용자 로그인: {user.email}")
        
        # JWT 토큰 생성
        logger.info("인증 토큰 생성 중...")
        
        access_token = auth.create_access_token(
            data={"sub": user.email, "user_id": user.id, "token_type": "access"}
        )
        refresh_token = auth.create_refresh_token(
            data={"sub": user.email, "user_id": user.id}
        )
        logger.info(f"로그인 성공: 사용자 {user.email}에 대한 토큰 발급 완료")
        
        return {
            "access_token": access_token, 
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    except Exception as e:
        logger.error(f"로그인 처리 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="로그인 처리 중 오류가 발생했습니다.")

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    current_user: UserInDB = Depends(auth.get_current_user)
):
    """보안 강화된 로그아웃 - 토큰 블랙리스트 추가"""
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        auth.add_token_to_blacklist(token, reason="logout")
        logger.info(f"✅ 사용자 {current_user.email} 로그아웃 완료")
    else:
        logger.info(f"⚠️ 토큰을 찾을 수 없음 - 사용자: {current_user.email}")
    
    return

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_data: dict):
    """리프레시 토큰으로 새로운 액세스 토큰 발급"""
    refresh_token = refresh_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="리프레시 토큰이 필요합니다"
        )
    
    try:
        # 리프레시 토큰 검증
        payload = jwt.decode(refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email = payload.get("sub")
        user_id = payload.get("user_id")
        token_type = payload.get("token_type")
        
        if not email or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 리프레시 토큰입니다"
            )
        
        # 새로운 액세스 토큰 생성
        new_access_token = auth.create_access_token(
            data={"sub": email, "user_id": user_id, "token_type": "access"}
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="리프레시 토큰 검증에 실패했습니다"
        ) 