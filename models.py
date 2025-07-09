from pydantic import BaseModel
from typing import List, Optional

# --- 사용자 관련 모델 ---

class UserBase(BaseModel):
    """사용자 데이터의 기본 형태"""
    email: str
    username: Optional[str] = None

class UserInDB(UserBase):
    """데이터베이스에서 조회한 사용자 정보를 나타내는 모델"""
    id: int

    class Config:
        # Pydantic V2 호환성을 위해 'orm_mode'를 'from_attributes'로 변경
        # 이 설정을 통해 데이터베이스 객체를 Pydantic 모델로 변환할 수 있습니다.
        from_attributes = True

# --- 인증 관련 모델 ---

class Token(BaseModel):
    """보안 강화된 JWT 토큰 모델 (액세스 + 리프레시 토큰)"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str
    expires_in: Optional[int] = None  # 초 단위

class TokenData(BaseModel):
    """JWT 토큰을 디코딩했을 때 얻게 되는 데이터 모델"""
    email: Optional[str] = None

# --- 설정 관련 모델 ---

class SettingOption(BaseModel):
    """선택 가능한 개별 설정 옵션을 나타내는 모델"""
    id: int
    setting_type: str
    option_value: str

    class Config:
        # 데이터베이스 객체 변환을 위해 설정
        from_attributes = True

class UserSettingsUpdate(BaseModel):
    """사용자가 자신의 설정을 업데이트할 때 보내는 요청 모델"""
    option_ids: List[int]

