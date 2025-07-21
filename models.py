from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

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

# --- 히스토리 관련 모델 ---

class ConversationType(str, Enum):
    """대화 유형 정의"""
    QUESTION = "question"
    ANSWER = "answer"
    FEEDBACK = "feedback"
    ERROR = "error"
    SYSTEM = "system"

class ConversationStatus(str, Enum):
    """세션 상태 정의"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class SessionCreateRequest(BaseModel):
    """새 세션 생성 요청"""
    session_title: Optional[str] = None
    primary_language: Optional[str] = "python"
    tags: Optional[List[str]] = []
    project_name: Optional[str] = None

class HistoryCreateRequest(BaseModel):
    """히스토리 엔트리 생성 요청"""
    session_id: str
    conversation_type: ConversationType
    content: str
    language: Optional[str] = "python"
    code_snippet: Optional[str] = None
    file_name: Optional[str] = None
    line_number: Optional[int] = None
    response_time: Optional[float] = None
    confidence_score: Optional[float] = None

class HistorySearchRequest(BaseModel):
    """히스토리 검색 요청"""
    query: str
    session_ids: Optional[List[str]] = []
    language: Optional[str] = None
    conversation_type: Optional[ConversationType] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: Optional[int] = 20

class ConversationEntry(BaseModel):
    """대화 엔트리 모델"""
    entry_id: str
    session_id: str
    user_id: int
    conversation_type: ConversationType
    content: str
    language: Optional[str] = None
    code_snippet: Optional[str] = None
    file_name: Optional[str] = None
    line_number: Optional[int] = None
    response_time: Optional[float] = None
    confidence_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationSession(BaseModel):
    """대화 세션 모델"""
    session_id: str
    user_id: int
    session_title: str
    status: ConversationStatus
    primary_language: str
    tags: List[str]
    project_name: Optional[str] = None
    total_entries: int = 0
    question_count: int = 0
    answer_count: int = 0
    created_at: datetime
    updated_at: datetime
    last_activity: datetime

    class Config:
        from_attributes = True

class HistoryResponse(BaseModel):
    """히스토리 작업 응답"""
    success: bool
    entry_id: Optional[str] = None
    session_id: Optional[str] = None
    message: str
    timestamp: datetime

class HistoryStats(BaseModel):
    """히스토리 통계"""
    total_sessions: int = 0
    active_sessions: int = 0
    total_entries: int = 0
    total_questions: int = 0
    total_answers: int = 0
    language_distribution: dict = {}
    sessions_today: int = 0
    sessions_this_week: int = 0
    average_session_length: float = 0.0

