"""
HAPA DB Module - 설정 관련 라우터
"""

from fastapi import APIRouter, Depends, status
from typing import List

import auth
import database
from models import UserInDB, SettingOption, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/options", response_model=List[SettingOption])
async def read_setting_options(current_user: UserInDB = Depends(auth.get_current_user)):
    """(로그인 필요) 선택 가능한 모든 설정 옵션 목록 조회"""
    pool = await database.get_db_pool()
    async with pool.acquire() as connection:
        records = await connection.fetch(
            "SELECT id, setting_type, option_value FROM setting_options ORDER BY setting_type, id"
        )
        return [dict(record) for record in records]

@router.get("/me", response_model=List[SettingOption])
async def get_my_settings(current_user: UserInDB = Depends(auth.get_current_user)):
    """(로그인 필요) 현재 로그인한 사용자의 설정 조회"""
    pool = await database.get_db_pool()
    async with pool.acquire() as connection:
        query = """
            SELECT so.id, so.setting_type, so.option_value
            FROM user_selected_options uso
            JOIN setting_options so ON uso.option_id = so.id
            WHERE uso.user_id = $1
        """
        records = await connection.fetch(query, current_user.id)
        return [dict(record) for record in records]

@router.post("/me", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_settings(
    settings: UserSettingsUpdate, 
    current_user: UserInDB = Depends(auth.get_current_user)
):
    """(로그인 필요) 사용자 설정 저장/수정"""
    pool = await database.get_db_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            # 기존 설정 삭제
            await connection.execute(
                "DELETE FROM user_selected_options WHERE user_id = $1", 
                current_user.id
            )
            # 새로운 설정 추가
            for option_id in settings.option_ids:
                await connection.execute(
                    "INSERT INTO user_selected_options (user_id, option_id) VALUES ($1, $2)",
                    current_user.id,
                    option_id
                )
    return 