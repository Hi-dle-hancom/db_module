"""
HAPA DB Module - 사용자 관련 라우터
"""

from fastapi import APIRouter, Depends

import auth
from models import UserInDB

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(auth.get_current_user)):
    """(로그인 필요) 내 정보 확인"""
    return current_user 