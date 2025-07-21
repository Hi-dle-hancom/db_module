"""
HAPA DB Module - 관리자 관련 라우터
"""

from fastapi import APIRouter, HTTPException

import database

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/init-db")
async def initialize_database():
    """데이터베이스 설정 옵션 초기화"""
    try:
        pool = await database.get_db_pool()
        async with pool.acquire() as connection:
            # 테이블 생성
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS setting_options (
                    id SERIAL PRIMARY KEY,
                    setting_type VARCHAR(100) NOT NULL,
                    option_value VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS user_selected_options (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    option_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (option_id) REFERENCES setting_options(id) ON DELETE CASCADE
                )
            """)
            
            # 히스토리 세션 테이블 생성
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(50) UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    session_title VARCHAR(200),
                    status VARCHAR(20) DEFAULT 'active',
                    primary_language VARCHAR(50) DEFAULT 'python',
                    tags TEXT[],
                    project_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_entries INTEGER DEFAULT 0,
                    question_count INTEGER DEFAULT 0,
                    answer_count INTEGER DEFAULT 0
                )
            """)
            
            # 히스토리 엔트리 테이블 생성
            await connection.execute("""
                CREATE TABLE IF NOT EXISTS conversation_entries (
                    id SERIAL PRIMARY KEY,
                    entry_id VARCHAR(50) UNIQUE NOT NULL,
                    session_id VARCHAR(50) NOT NULL,
                    user_id INTEGER NOT NULL,
                    conversation_type VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    language VARCHAR(50),
                    code_snippet TEXT,
                    file_name VARCHAR(255),
                    line_number INTEGER,
                    response_time FLOAT,
                    confidence_score FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions(session_id) ON DELETE CASCADE
                )
            """)
            
            # 인덱스 생성 (성능 최적화)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id 
                ON conversation_sessions(user_id)
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_sessions_session_id 
                ON conversation_sessions(session_id)
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_entries_user_id 
                ON conversation_entries(user_id)
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_entries_session_id 
                ON conversation_entries(session_id)
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_entries_created_at 
                ON conversation_entries(created_at)
            """)
            await connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversation_entries_conversation_type 
                ON conversation_entries(conversation_type)
            """)
            
            # 기존 설정 옵션이 있는지 확인
            existing_count = await connection.fetchval("SELECT COUNT(*) FROM setting_options")
            
            if existing_count == 0:
                # 새로운 설정 옵션 데이터 삽입 (9개 핵심 옵션)
                setting_options = [
                    # 🐍 Python 스킬 레벨 (2가지)
                    (1, 'python_skill_level', 'beginner', '기본 문법 학습 중'),
                    (2, 'python_skill_level', 'intermediate', '일반적 프로그래밍 가능'),
                    
                    # 📝 코드 출력 구조 (3가지)
                    (3, 'code_output_structure', 'minimal', '핵심 로직만 간결하게'),
                    (4, 'code_output_structure', 'standard', '기본 주석 포함'),
                    (5, 'code_output_structure', 'detailed', '예외처리 + 타입힌트'),
                    
                    # 💬 설명 스타일 (4가지)
                    (6, 'explanation_style', 'brief', '핵심 내용만'),
                    (7, 'explanation_style', 'standard', '코드 + 간단 설명'),
                    (8, 'explanation_style', 'detailed', '개념 + 이유 + 활용법'),
                    (9, 'explanation_style', 'educational', '단계별 + 예시'),
                ]
                
                for option in setting_options:
                    await connection.execute(
                        "INSERT INTO setting_options (id, setting_type, option_value, description) VALUES ($1, $2, $3, $4)",
                        *option
                    )
                
                # ID 시퀀스 재설정
                await connection.execute("SELECT setval('setting_options_id_seq', 9, true)")
                
                return {
                    "status": "success",
                    "message": "데이터베이스가 성공적으로 초기화되었습니다.",
                    "options_created": len(setting_options),
                    "categories": {
                        "python_skill_level": 2,
                        "code_output_structure": 3,
                        "explanation_style": 4
                    }
                }
            else:
                return {
                    "status": "already_initialized",
                    "message": f"데이터베이스가 이미 초기화되어 있습니다. ({existing_count}개 옵션 존재)",
                    "existing_options": existing_count
                }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"데이터베이스 초기화 실패: {str(e)}"
        ) 