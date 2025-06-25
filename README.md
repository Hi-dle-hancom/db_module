# 🗄️ HAPA DB Module

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![JWT](https://img.shields.io/badge/JWT-Authentication-orange.svg)](https://jwt.io/)

> **HAPA 사용자 관리 및 인증 마이크로서비스**  
> PostgreSQL 기반 사용자 데이터 관리, JWT 인증, 온보딩 설정 서비스

## 🎯 **서비스 개요**

HAPA DB Module은 사용자 인증, 개인화 설정, 온보딩 플로우를 담당하는 **독립적인 마이크로서비스**입니다. Backend API와 분리되어 확장성과 보안성을 향상시켰습니다.

### ✨ **주요 기능**

- 👤 **사용자 인증**: JWT 토큰 기반 안전한 인증 시스템
- ⚙️ **개인화 설정**: 27개 온보딩 옵션으로 맞춤형 AI 경험
- 🚀 **온보딩 플로우**: 신규 사용자 설정 가이드
- 🔒 **보안 관리**: 패스워드 해싱, 토큰 관리
- 📊 **사용자 프로필**: 스킬 레벨, 선호도 관리
- 🔄 **실시간 동기화**: Backend API와 실시간 데이터 연동

## 🏗️ **아키텍처**

```
DB-Module/
├── 📄 main.py              # FastAPI 애플리케이션 진입점
├── 📄 database.py          # PostgreSQL 커넥션 풀 관리
├── 📄 auth.py              # JWT 인증 로직
├── 📄 models.py            # Pydantic 데이터 모델
├── 📄 requirements.txt     # Python 의존성
├── 📄 Dockerfile           # Docker 컨테이너 설정
└── 📄 .env                 # 환경 변수 설정
```

### 🗃️ **데이터베이스 스키마**

```sql
-- 사용자 테이블
users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 설정 옵션 마스터 테이블 (27개 옵션)
setting_options (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,     -- 'skill_level', 'output_structure' 등
    option_key VARCHAR(100) NOT NULL,  -- 'beginner', 'standard' 등
    option_value VARCHAR(255) NOT NULL, -- 표시명
    description TEXT,
    is_active BOOLEAN DEFAULT true
);

-- 사용자별 선택된 설정
user_selected_options (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    setting_option_id INTEGER REFERENCES setting_options(id),
    selected_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, setting_option_id)
);
```

## 🚀 **빠른 시작**

### 전제 조건

- **Python 3.12+**
- **PostgreSQL 15+**
- **Git**

### 로컬 개발 환경

```bash
# 1. 저장소 클론 (프로젝트 루트에서)
cd DB-Module

# 2. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. PostgreSQL 데이터베이스 설정
createdb hapa_development

# 5. 환경 변수 설정
cp .env.example .env
# .env 파일에서 DATABASE_URL 등 수정

# 6. 개발 서버 시작
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### Docker 실행

```bash
# 1. Docker 이미지 빌드
docker build -t hapa-db-module .

# 2. 컨테이너 실행
docker run -p 8001:8001 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/hapa" \
  -e JWT_SECRET_KEY="your-jwt-secret" \
  hapa-db-module
```

### 서비스 확인

```bash
# 헬스 체크
curl http://localhost:8001/health

# API 문서 확인
open http://localhost:8001/docs
```

## 🔧 **환경 설정**

### 필수 환경 변수

```bash
# 기본 설정
ENVIRONMENT=development          # development/production
HOST=0.0.0.0                    # 서버 호스트
PORT=8001                       # 서버 포트

# 데이터베이스 설정
DATABASE_URL=postgresql://username:password@localhost:5432/hapa_development

# JWT 인증 설정
JWT_SECRET_KEY=your-super-secure-jwt-secret-key-32-characters-minimum
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_DAYS=365    # 토큰 만료 기간

# CORS 설정 (개발환경)
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# 로깅 설정
LOG_LEVEL=INFO
```

### 운영 환경 설정

```bash
# 운영 환경 전용
ENVIRONMENT=production
DEBUG=false

# 강화된 보안 설정
ACCESS_TOKEN_EXPIRE_DAYS=7      # 짧은 토큰 만료 기간
CORS_ORIGINS=["https://your-domain.com"]

# 데이터베이스 풀링
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

## 📡 **API 엔드포인트**

### 🔐 **인증 API**

#### **사용자 등록**

```http
POST /register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "secure_password123"
}
```

**응답:**

```json
{
  "message": "사용자가 성공적으로 등록되었습니다.",
  "user_id": 1,
  "username": "john_doe"
}
```

#### **로그인**

```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=john_doe&password=secure_password123
```

**응답:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 31536000
}
```

### ⚙️ **설정 관리 API**

#### **온보딩 옵션 조회**

```http
GET /setting-options
```

**응답:**

```json
{
  "skill_level": [
    {
      "id": 1,
      "option_key": "beginner",
      "option_value": "초급자 (Python 기초 학습 중)",
      "description": "Python 문법을 배우고 있는 단계"
    },
    {
      "id": 2,
      "option_key": "intermediate",
      "option_value": "중급자 (기본 문법 숙지)",
      "description": "기본적인 Python 개발 가능"
    }
  ],
  "output_structure": [
    {
      "id": 5,
      "option_key": "minimal",
      "option_value": "간결한 코드",
      "description": "핵심 로직만 포함된 간단한 코드"
    }
  ]
}
```

#### **사용자 설정 업데이트**

```http
PUT /users/me/settings
Authorization: Bearer your-jwt-token
Content-Type: application/json

{
  "selected_options": [1, 5, 8, 12, 15]
}
```

### 👤 **사용자 프로필 API**

#### **현재 사용자 정보 조회**

```http
GET /users/me
Authorization: Bearer your-jwt-token
```

**응답:**

```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "selected_settings": {
    "skill_level": "intermediate",
    "output_structure": "standard",
    "explanation_style": "detailed",
    "project_context": "web_development",
    "preferred_features": ["type_hints", "f_strings"]
  }
}
```

## 📊 **온보딩 설정 옵션**

### 🎯 **27개 개인화 옵션 카테고리**

1. **Python 스킬 레벨** (4개)

   - 초급자, 중급자, 고급자, 전문가

2. **코드 출력 구조** (4개)

   - 간결, 표준, 상세, 포괄적

3. **설명 스타일** (4개)

   - 간단, 표준, 상세, 교육적

4. **프로젝트 컨텍스트** (6개)

   - 웹개발, 데이터사이언스, 자동화, 범용, 학술, 기업

5. **주석 트리거 모드** (4개)

   - 즉시삽입, 사이드바, 확인삽입, 인라인미리보기

6. **선호 언어 기능** (8개)

   - 타입힌트, 데이터클래스, 비동기, 컴프리헨션, 제너레이터, 데코레이터, 컨텍스트매니저, f-strings

7. **에러 처리 선호도** (4개)
   - 기본, 상세, 견고함, 프로덕션 준비

## 🔒 **보안 고려사항**

### 패스워드 보안

```python
# bcrypt 해싱 사용
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 패스워드 해싱
hashed = pwd_context.hash(plain_password)

# 패스워드 검증
is_valid = pwd_context.verify(plain_password, hashed)
```

### JWT 토큰 보안

- **HS256 알고리즘** 사용
- **32자 이상 시크릿 키** 필수
- **토큰 만료시간** 설정
- **리프레시 토큰** 미지원 (간단한 아키텍처)

## 🚨 **에러 처리**

### 표준 에러 응답

```json
{
  "detail": "사용자를 찾을 수 없습니다.",
  "error_code": "USER_NOT_FOUND",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 주요 에러 코드

- `USER_NOT_FOUND` (404): 사용자를 찾을 수 없음
- `INVALID_CREDENTIALS` (401): 잘못된 인증 정보
- `USER_ALREADY_EXISTS` (409): 사용자 이미 존재
- `INVALID_TOKEN` (401): 유효하지 않은 JWT 토큰
- `DATABASE_ERROR` (500): 데이터베이스 연결 오류

## 📈 **모니터링**

### 헬스 체크

```bash
# 기본 헬스 체크
curl http://localhost:8001/health

# 데이터베이스 연결 상태 포함
curl http://localhost:8001/health/detailed
```

### 로그 모니터링

```bash
# 애플리케이션 로그
tail -f logs/db-module.log

# 데이터베이스 연결 로그
grep "database" logs/db-module.log
```

## 🔄 **Backend API와의 연동**

### 사용자 설정 조회 플로우

```mermaid
sequenceDiagram
    participant VSCode as VSCode Extension
    participant Backend as Backend API
    participant DBModule as DB Module

    VSCode->>Backend: 코드 생성 요청 (with JWT)
    Backend->>DBModule: 사용자 설정 조회
    DBModule-->>Backend: 개인화 설정 반환
    Backend->>Backend: 설정 기반 AI 모델 조정
    Backend-->>VSCode: 맞춤형 코드 응답
```

## 🧪 **테스트**

### 단위 테스트 실행

```bash
# 전체 테스트 실행
pytest

# 특정 모듈 테스트
pytest test_auth.py

# 커버리지 포함
pytest --cov=. --cov-report=html
```

### API 테스트

```bash
# 사용자 등록 테스트
curl -X POST http://localhost:8001/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"test123"}'

# 로그인 테스트
curl -X POST http://localhost:8001/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test123"
```

## 🚀 **배포 가이드**

### Docker Compose (권장)

```yaml
# docker-compose.yml에서 확인
services:
  db-module:
    build: ./DB-Module
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/hapa
      - JWT_SECRET_KEY=production-secret-key
    depends_on:
      - postgres
```

### 단독 배포

```bash
# 1. 운영 환경 변수 설정
export ENVIRONMENT=production
export DATABASE_URL="postgresql://..."
export JWT_SECRET_KEY="production-secret-key"

# 2. 애플리케이션 시작
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4
```

## 📚 **추가 문서**

- **API 문서**: http://localhost:8001/docs (FastAPI 자동 생성)
- **데이터베이스 스키마**: `docs/database-schema.md`
- **보안 가이드**: `docs/security-guide.md`
- **배포 가이드**: `docs/deployment-guide.md`

## 🤝 **기여 가이드**

1. **Fork** 프로젝트
2. **Feature 브랜치** 생성: `git checkout -b feature/amazing-feature`
3. **변경사항 커밋**: `git commit -m 'Add amazing feature'`
4. **브랜치 푸시**: `git push origin feature/amazing-feature`
5. **Pull Request** 생성

## 📄 **라이선스**

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

---

**개발팀**: 하이들 (Hi-dle) Team  
**문의**: support@hapa.dev
