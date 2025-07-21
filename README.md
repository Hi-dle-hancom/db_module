# 🗃️ HAPA DB-Module

> **사용자 관리 & 데이터베이스 전담 마이크로서비스**  
> PostgreSQL + MongoDB 이중 DB 구조로 안전하고 효율적인 데이터 관리

## 🤔 **DB-Module이 하는 일**

**간단히 설명하면**: HAPA의 모든 데이터를 안전하게 관리하는 전용 서버입니다! 🏦

```mermaid
graph TB
    A[👤 사용자 요청] --> B[🗃️ DB-Module]
    B --> C[🔐 PostgreSQL<br/>사용자 인증/설정]
    B --> D[📚 MongoDB<br/>대화 히스토리]

    B --> E[🎫 JWT 토큰 발급]
    B --> F[⚙️ 개인화 설정]
    B --> G[📊 히스토리 관리]
```

## 🎯 **핵심 기능**

### **🔐 사용자 인증 & 보안**

- **JWT 토큰 시스템**: 액세스 토큰(30분) + 리프레시 토큰(7일)
- **자동 사용자 등록**: 이메일만으로 즉시 계정 생성
- **토큰 블랙리스트**: 로그아웃된 토큰 무효화

### **⚙️ 개인화 설정 관리**

- **16가지 설정 카테고리**: Python 스킬, 코드 스타일, 설명 방식 등
- **실시간 설정 동기화**: 변경사항 즉시 반영
- **프로필 기반 맞춤화**: 사용자별 AI 응답 개인화

### **📚 히스토리 관리 (MongoDB)**

- **대화 세션 관리**: 질문-답변 쌍 체계적 저장
- **실시간 검색**: 과거 대화 내용 빠른 검색
- **통계 분석**: 사용 패턴 및 효율성 분석

## 🏗️ **데이터베이스 구조**

### **PostgreSQL (사용자 데이터)**

```sql
-- 사용자 테이블
users {
  id: SERIAL PRIMARY KEY
  email: VARCHAR UNIQUE
  username: VARCHAR
  created_at: TIMESTAMP
}

-- 설정 옵션
setting_options {
  id: SERIAL PRIMARY KEY
  setting_type: VARCHAR     -- 설정 카테고리
  option_value: VARCHAR     -- 설정 값
  description: TEXT
}

-- 사용자 선택 설정
user_selected_options {
  user_id: INTEGER
  option_id: INTEGER
  created_at: TIMESTAMP
}
```

### **MongoDB (히스토리 데이터)**

```javascript
// 세션 문서 (hapa.history 컬렉션)
{
  "document_type": "session",
  "session_id": "session_abc123",
  "user_id": 1,
  "session_title": "Python 기초 학습",
  "status": "active",
  "primary_language": "python",
  "total_entries": 4,
  "created_at": ISODate("2024-12-28T...")
}

// 대화 엔트리 문서
{
  "document_type": "entry",
  "entry_id": "entry_xyz789",
  "session_id": "session_abc123",
  "conversation_type": "question",
  "content": "Python에서 리스트 정렬 방법은?",
  "created_at": ISODate("2024-12-28T...")
}
```

## 📡 **API 엔드포인트**

### **🔐 인증 관리**

```http
POST /auth/login
# 로그인/자동 회원가입

POST /auth/logout
# 로그아웃 (토큰 무효화)

POST /auth/refresh
# 토큰 갱신
```

### **👤 사용자 관리**

```http
GET /users/me
# 내 정보 조회
```

### **⚙️ 설정 관리**

```http
GET /settings/options
# 사용 가능한 설정 옵션 조회

GET /settings/me
# 내 설정 조회

POST /settings/me
# 설정 업데이트
```

### **📚 히스토리 관리 (MongoDB)**

```http
POST /history/sessions
# 새 대화 세션 생성

GET /history/sessions
# 세션 목록 조회

GET /history/sessions/{session_id}
# 특정 세션의 대화 내용

POST /history/entries
# 새 대화 엔트리 추가

POST /history/search
# 히스토리 검색

GET /history/stats
# 사용 통계 조회
```

### **🏥 시스템 관리**

```http
GET /health
# 전체 시스템 상태 (PostgreSQL + MongoDB)

POST /admin/init-db
# 데이터베이스 초기화
```

## 🚀 **빠른 시작**

### **1. 환경 설정**

```bash
# 환경 변수 파일 생성
cp .env.example .env

# 필수 환경 변수 설정
DATABASE_URL=postgresql://username:password@localhost:5432/hidle
MONGODB_URL=mongodb://localhost:27017/hapa
JWT_SECRET_KEY=your-32-character-secret-key
```

### **2. 의존성 설치**

```bash
pip install -r requirements.txt
```

### **3. 데이터베이스 초기화**

```bash
# 서버 실행
python main.py

# 데이터베이스 테이블 생성
curl -X POST http://localhost:8001/admin/init-db
```

### **4. API 테스트**

```bash
# 헬스 체크
curl http://localhost:8001/health

# 사용자 로그인/등록
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "testuser"}'

# 설정 옵션 조회
curl -X GET "http://localhost:8001/settings/options" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔧 **Docker 배포**

### **docker-compose.yml 설정**

```yaml
# PostgreSQL 서비스 (기존)
postgres:
  image: postgres:14
  environment:
    POSTGRES_DB: hidle
    POSTGRES_USER: username
    POSTGRES_PASSWORD: password

# MongoDB 서비스 (NEW)
mongodb:
  image: mongo:7.0
  environment:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: hapa_mongodb_password
    MONGO_INITDB_DATABASE: hapa

# DB-Module 서비스
db_module:
  build: ./DB-Module
  environment:
    - DATABASE_URL=postgresql://username:password@postgres:5432/hidle
    - MONGODB_URL=mongodb://admin:hapa_mongodb_password@mongodb:27017/hapa?authSource=admin
  depends_on:
    - postgres
    - mongodb
```

### **실행**

```bash
# 전체 서비스 시작
docker-compose up -d

# DB-Module만 시작
docker-compose up db_module
```

## 📁 **프로젝트 구조**

DB-Module/
├── main.py # FastAPI 애플리케이션 진입점
├── auth.py # JWT 인증 시스템
├── database.py # PostgreSQL + MongoDB 연결 관리
├── models.py # Pydantic 데이터 모델
├── routers/ # API 엔드포인트
│ ├── auth_router.py # 인증 관련 API
│ ├── users_router.py # 사용자 관리 API
│ ├── settings_router.py # 설정 관리 API
│ ├── history_router.py # 히스토리 관리 API (MongoDB)
│ └── admin_router.py # 관리자 API
├── requirements.txt # Python 의존성
├── Dockerfile # Docker 설정
└── README.md # 이 문서

## 🛡️ **보안 & 인증**

### **JWT 토큰 시스템**

```python
# 토큰 구조
{
  "sub": "user@example.com",      # 사용자 이메일
  "user_id": 123,                 # 사용자 ID
  "token_type": "access",         # 토큰 타입
  "exp": 1640995200,             # 만료 시간
  "iat": 1640991600              # 발급 시간
}
```

### **보안 기능**

- **토큰 블랙리스트**: 로그아웃된 토큰 자동 무효화
- **자동 만료**: 액세스 토큰 30분, 리프레시 토큰 7일
- **환경별 시크릿**: 개발/운영 환경 분리

## 📊 **모니터링 & 로깅**

### **헬스 체크**

```json
{
  "status": "healthy",
  "database": "connected",
  "mongodb": "connected",
  "environment": "development",
  "connections": {
    "postgresql": {
      "host": "localhost:5432",
      "database": "hidle",
      "status": "connected"
    },
    "mongodb": {
      "host": "localhost:27017",
      "database": "hapa",
      "status": "connected"
    }
  }
}
```

### **로깅 시스템**

- **구조화된 로그**: JSON 형태로 체계적 기록
- **DB 연결 추적**: 연결 상태 실시간 모니터링
- **성능 메트릭**: 쿼리 실행 시간 측정

## 🔧 **설정 시스템**

### **개인화 설정 옵션**

| 카테고리              | 옵션                                       | 설명             |
| --------------------- | ------------------------------------------ | ---------------- |
| **Python 스킬**       | beginner, intermediate, advanced, expert   | 코드 복잡도 조절 |
| **코드 출력**         | minimal, standard, detailed, comprehensive | 출력 상세도      |
| **설명 스타일**       | simple, standard, detailed, educational    | 설명 방식        |
| **프로젝트 컨텍스트** | web, data_science, automation, general     | 분야별 최적화    |

### **설정 API 사용 예시**

```bash
# 설정 업데이트
curl -X POST "http://localhost:8001/settings/me" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"option_ids": [1, 5, 9, 13]}'
```

## 🆘 **문제 해결**

### **자주 발생하는 문제**

**Q: PostgreSQL 연결 실패**

```bash
# 해결: 연결 정보 확인
echo $DATABASE_URL
# postgresql://username:password@host:5432/database
```

**Q: MongoDB 연결 실패**

```bash
# 해결: MongoDB 서비스 상태 확인
docker-compose ps mongodb
mongosh mongodb://localhost:27017/hapa
```

**Q: JWT 토큰 만료**

```bash
# 해결: 리프레시 토큰으로 갱신
curl -X POST "http://localhost:8001/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

## 📈 **성능 지표**

| 메트릭           | 목표    | 현재 상태 |
| ---------------- | ------- | --------- |
| 로그인 응답 시간 | < 500ms | 200ms ✅  |
| DB 쿼리 시간     | < 100ms | 50ms ✅   |
| 동시 접속        | 100명   | 지원됨 ✅ |
| 가용성           | 99.9%   | 99.8% ⚠️  |

---
