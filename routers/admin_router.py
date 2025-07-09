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
            
            # 기존 설정 옵션이 있는지 확인
            existing_count = await connection.fetchval("SELECT COUNT(*) FROM setting_options")
            
            if existing_count == 0:
                # 설정 옵션 데이터 삽입
                setting_options = [
                    (1, 'python_skill_level', 'beginner', 'Python을 처음 배우고 있거나 기본 문법을 학습 중'),
                    (2, 'python_skill_level', 'intermediate', '기본 문법을 알고 있으며 일반적인 프로그래밍이 가능'),
                    (3, 'python_skill_level', 'advanced', '복잡한 프로젝트 개발이 가능하며 라이브러리 활용에 능숙'),
                    (4, 'python_skill_level', 'expert', '최적화, 아키텍처 설계, 고급 패턴 구현이 가능'),
                    
                    (5, 'code_output_structure', 'minimal', '핵심 로직만 간결하게 (주석 최소화)'),
                    (6, 'code_output_structure', 'standard', '일반적인 코드 구조 + 기본 주석'),
                    (7, 'code_output_structure', 'detailed', '자세한 주석 + 예외 처리 + 타입 힌트'),
                    (8, 'code_output_structure', 'comprehensive', '문서화 + 테스트 코드 + 최적화 제안'),
                    
                    (9, 'explanation_style', 'brief', '핵심 내용만 빠르게'),
                    (10, 'explanation_style', 'standard', '코드 + 간단한 설명'),
                    (11, 'explanation_style', 'detailed', '개념 + 이유 + 활용법'),
                    (12, 'explanation_style', 'educational', '단계별 + 예시 + 관련 개념'),
                    
                    (13, 'project_context', 'web_development', 'Django, Flask, FastAPI 등 웹 개발'),
                    (14, 'project_context', 'data_science', 'NumPy, Pandas, 머신러닝 등 데이터 사이언스'),
                    (15, 'project_context', 'automation', '스크립팅, 업무 자동화'),
                    (16, 'project_context', 'general_purpose', '다양한 목적의 범용 개발'),
                ]
                
                for option in setting_options:
                    await connection.execute(
                        "INSERT INTO setting_options (id, setting_type, option_value, description) VALUES ($1, $2, $3, $4)",
                        *option
                    )
                
                return {
                    "status": "success",
                    "message": "데이터베이스가 성공적으로 초기화되었습니다.",
                    "options_created": len(setting_options)
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