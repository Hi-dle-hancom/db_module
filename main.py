from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from dotenv import load_dotenv

# 환경변수 파일 로드 (가장 먼저 실행)
load_dotenv()

import auth
import database
from models import UserBase, UserInDB, SettingOption, UserSettingsUpdate, Token

app = FastAPI(
    title="HAPA DB Module API",
    description="사용자 관리 및 개인화 설정 마이크로서비스",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 애플리케이션 시작 시 데이터베이스 연결
@app.on_event("startup")
async def startup_event():
    await database.connect_to_db()

# 애플리케이션 종료 시 데이터베이스 연결 해제
@app.on_event("shutdown") 
async def shutdown_event():
    await database.close_db_connection()

@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "message": "HAPA DB Module API is running!",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        pool = await database.get_db_pool()
        # 간단한 DB 연결 테스트
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )

@app.post("/login", response_model=Token)
async def login_or_register(user_data: UserBase):
    """
    이메일만으로 로그인 또는 자동 회원가입을 처리하고, 식별용 JWT 토큰을 발급합니다.
    """
    print(f"🔍 [DEBUG] 로그인 요청: {user_data.email}")
    
    user = await auth.get_user(user_data.email)
    print(f"🔍 [DEBUG] 기존 사용자 조회 결과: {user}")

    if user is None:
        print(f"🔍 [DEBUG] 신규 사용자 생성 시작: {user_data.email}")
        
        pool = await database.get_db_pool()
        async with pool.acquire() as connection:
            print(f"🔍 [DEBUG] DB 연결 획득 완료")
            
            query = "INSERT INTO users (email, username) VALUES ($1, $2) RETURNING id, email, username"
            print(f"🔍 [DEBUG] INSERT 쿼리 실행: {query}")
            print(f"🔍 [DEBUG] 매개변수: email={user_data.email}, username={user_data.username}")
            
            try:
                created_user_record = await connection.fetchrow(query, user_data.email, user_data.username)
                print(f"🔍 [DEBUG] INSERT 결과: {created_user_record}")
                
                # --- 여기를 수정합니다 ---
                # 기존: user = UserInDB.from_orm(created_user_record)
                # 수정: asyncpg.Record 객체를 dict로 변환 후 Pydantic 모델 생성
                user = UserInDB(**dict(created_user_record))
                print(f"🔍 [DEBUG] UserInDB 객체 생성: {user}")
                # ---------------------
            except Exception as e:
                print(f"🚨 [ERROR] INSERT 실행 중 오류: {e}")
                raise HTTPException(status_code=500, detail=f"사용자 생성 실패: {str(e)}")
    else:
        print(f"🔍 [DEBUG] 기존 사용자 로그인: {user.email}")
    
    print(f"🔍 [DEBUG] JWT 토큰 생성 시작")
    access_token = auth.create_access_token(
        data={"sub": user.email}
    )
    print(f"🔍 [DEBUG] JWT 토큰 생성 완료: {access_token[:50]}...")
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/settings/options", response_model=List[SettingOption])
async def read_setting_options(current_user: UserInDB = Depends(auth.get_current_user)):
    """(로그인 필요) 선택 가능한 모든 설정 옵션 목록 조회"""
    pool = await database.get_db_pool()
    async with pool.acquire() as connection:
        records = await connection.fetch("SELECT id, setting_type, option_value FROM setting_options ORDER BY setting_type, id")
        return [dict(record) for record in records]

@app.get("/users/me/settings", response_model=List[SettingOption])
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

@app.post("/users/me/settings", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_settings(settings: UserSettingsUpdate, current_user: UserInDB = Depends(auth.get_current_user)):
    """(로그인 필요) 사용자 설정 저장/수정"""
    pool = await database.get_db_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            await connection.execute("DELETE FROM user_selected_options WHERE user_id = $1", current_user.id)
            for option_id in settings.option_ids:
                await connection.execute(
                    "INSERT INTO user_selected_options (user_id, option_id) VALUES ($1, $2)",
                    current_user.id,
                    option_id
                )
    return

@app.get("/users/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(auth.get_current_user)):
    """(로그인 필요) 내 정보 확인"""
    return current_user

@app.post("/init-db")
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
                    
                    (17, 'comment_trigger_mode', 'immediate_insert', '생성된 코드를 커서 위치에 바로 삽입'),
                    (18, 'comment_trigger_mode', 'sidebar', '사이드바에 결과를 표시하고 검토 후 삽입'),
                    (19, 'comment_trigger_mode', 'confirm_insert', '코드를 미리보고 확인 대화상자에서 삽입 여부 선택'),
                    (20, 'comment_trigger_mode', 'inline_preview', '에디터에서 코드를 미리보고 키보드로 선택'),
                    
                    (21, 'preferred_language_feature', 'type_hints', '타입 힌트로 코드의 가독성과 안정성 향상'),
                    (22, 'preferred_language_feature', 'dataclasses', '데이터클래스로 간편한 클래스 정의'),
                    (23, 'preferred_language_feature', 'async_await', '비동기 프로그래밍으로 효율적인 I/O 처리'),
                    (24, 'preferred_language_feature', 'f_strings', 'f-strings로 깔끔한 문자열 포맷팅'),
                    
                    (25, 'error_handling_preference', 'basic', '기본적인 try-except 구조'),
                    (26, 'error_handling_preference', 'detailed', '구체적인 예외 처리와 로깅'),
                    (27, 'error_handling_preference', 'robust', '완전한 에러 복구 메커니즘과 fallback')
                ]
                
                for option in setting_options:
                    await connection.execute(
                        "INSERT INTO setting_options (id, setting_type, option_value, description) VALUES ($1, $2, $3, $4)",
                        *option
                    )
                
                # ID 시퀀스 재설정
                await connection.execute("SELECT setval('setting_options_id_seq', 27, true)")
                
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