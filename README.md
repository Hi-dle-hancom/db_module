# 🗃️ HAPA DB Module

<div align="center">

**사용자 관리 및 개인화 설정 마이크로서비스**

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[설치하기](#설치) • [사용법](#사용법) • [API 문서](#api-문서) • [아키텍처](#아키텍처) • [개발](#개발)

</div>

## 📋 목차

- [개요](#개요)
- [주요 기능](#주요-기능)
- [아키텍처](#아키텍처)
- [설치](#설치)
- [사용법](#사용법)
- [API 문서](#api-문서)
- [환경 설정](#환경-설정)
- [개발](#개발)
- [배포](#배포)
- [기여하기](#기여하기)

## 🎯 개요

HAPA DB Module은 **FastAPI 기반**의 경량화된 마이크로서비스로, HAPA 생태계의 사용자 관리 및 개인화 설정을 전담합니다.

### 🚀 핵심 특징

- **🔐 JWT 인증 시스템**: 액세스/리프레시 토큰 기반 보안 인증
- **👤 사용자 관리**: 자동 사용자 생성 및 프로필 관리
- **⚙️ 개인화 설정**: 16가지 카테고리의 사용자 맞춤 설정
- **🏗️ 모듈화 설계**: 라우터별 기능 분리로 확장성 확보
- **🔄 RESTful API**: 표준 HTTP 메서드 및 상태 코드 준수

## 🌟 주요 기능

### 1. 인증 시스템

- JWT 기반 토큰 인증 (액세스 토큰 30분, 리프레시 토큰 7일)
- 토큰 블랙리스트 관리
- 자동 사용자 생성 및 로그인

### 2. 사용자 관리

- 사용자 프로필 조회
- 설정 기반 개인화 서비스

### 3. 개인화 설정

- **Python 스킬 레벨**: 초급, 중급, 고급, 전문가
- **코드 출력 구조**: 간결, 표준, 상세, 종합
- **설명 스타일**: 간단, 표준, 상세, 교육용
- **프로젝트 컨텍스트**: 웹 개발, 데이터 사이언스, 자동화, 범용

### 4. 관리자 기능

- 데이터베이스 초기화
- 설정 옵션 관리

## 🏗️ 아키텍처

### 📁 디렉토리 구조

```
DB-Module/
├── main.py                    # 메인 애플리케이션 (104줄)
├── auth.py                    # 통합 인증 시스템 (244줄)
├── database.py                # 데이터베이스 연결 관리 (120줄)
├── models.py                  # Pydantic 모델 정의 (49줄)
├── routers/                   # API 라우터 모음
│   ├── auth_router.py         # 인증 관련 API
│   ├── settings_router.py     # 설정 관련 API
│   ├── users_router.py        # 사용자 관련 API
│   └── admin_router.py        # 관리자 관련 API
├── .env                       # 환경 설정 (기본)
├── .env.production            # 운영 환경 설정
├── .env.example               # 환경 설정 템플릿
├── requirements.txt           # Python 의존성
├── Dockerfile                 # 도커 설정
└── README.md                  # 이 문서
```

### 🔧 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  HAPA DB Module                         │
├─────────────────────────────────────────────────────────┤
│  📋 Main Application (main.py)                         │
│  └─ FastAPI App + CORS + 라우터 등록                   │
├─────────────────────────────────────────────────────────┤
│  🔐 Authentication Layer (auth.py)                     │
│  └─ JWT 토큰 + 보안 + 토큰 블랙리스트                   │
├─────────────────────────────────────────────────────────┤
│  🛠️ Router Layer (routers/)                           │
│  ├─ auth_router.py → 로그인/로그아웃/토큰 갱신         │
│  ├─ settings_router.py → 개인화 설정 관리             │
│  ├─ users_router.py → 사용자 정보 조회               │
│  └─ admin_router.py → DB 초기화 및 관리               │
├─────────────────────────────────────────────────────────┤
│  🗄️ Data Layer                                        │
│  ├─ database.py → PostgreSQL 연결 관리               │
│  └─ models.py → Pydantic 스키마 정의                 │
└─────────────────────────────────────────────────────────┘
```

## 📦 설치

### 1. 요구사항

- Python 3.9 이상
- PostgreSQL 14 이상
- pip 또는 poetry

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 설정

```bash
cp .env.example .env
# .env 파일을 수정하여 데이터베이스 연결 정보 설정
```

### 4. 데이터베이스 초기화

```bash
# 서버 실행 후
curl -X POST http://localhost:8001/admin/init-db
```

## 🚀 사용법

### 1. 서버 실행

```bash
# 개발 모드
python main.py

# 운영 모드
uvicorn main:app --host 0.0.0.0 --port 8001
```

### 2. 기본 사용 예시

```bash
# 1. 사용자 로그인
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "user"}'

# 2. 사용자 정보 조회
curl -X GET http://localhost:8001/users/me \
  -H "Authorization: Bearer YOUR_TOKEN"

# 3. 설정 옵션 조회
curl -X GET http://localhost:8001/settings/options \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. 사용자 설정 저장
curl -X POST http://localhost:8001/settings/me \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"option_ids": [1, 5, 9, 13]}'
```

## 📖 API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### 주요 엔드포인트

| 메서드 | 경로                | 설명           | 인증 필요 |
| ------ | ------------------- | -------------- | --------- |
| `POST` | `/auth/login`       | 사용자 로그인  | ❌        |
| `POST` | `/auth/logout`      | 로그아웃       | ✅        |
| `POST` | `/auth/refresh`     | 토큰 갱신      | ❌        |
| `GET`  | `/users/me`         | 내 정보 조회   | ✅        |
| `GET`  | `/settings/options` | 설정 옵션 목록 | ✅        |
| `GET`  | `/settings/me`      | 내 설정 조회   | ✅        |
| `POST` | `/settings/me`      | 내 설정 저장   | ✅        |
| `POST` | `/admin/init-db`    | DB 초기화      | ❌        |

## ⚙️ 환경 설정

### .env 파일 설정

```env
# 환경 설정
ENVIRONMENT=development
DEBUG=true

# 데이터베이스 설정
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# JWT 보안 설정
JWT_SECRET_KEY=your_secret_key_here_32_chars_minimum
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 서버 설정
HOST=0.0.0.0
PORT=8001

# 로깅 설정
LOG_LEVEL=INFO
```

### 주요 설정 옵션

| 설정                          | 기본값      | 설명                               |
| ----------------------------- | ----------- | ---------------------------------- |
| `ENVIRONMENT`                 | development | 실행 환경 (development/production) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30          | 액세스 토큰 만료 시간 (분)         |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | 7           | 리프레시 토큰 만료 시간 (일)       |
| `LOG_LEVEL`                   | INFO        | 로그 레벨                          |

## 🔧 개발

### 1. 개발 환경 설정

```bash
# 개발 모드로 실행
ENVIRONMENT=development python main.py

# 코드 변경 시 자동 재시작
uvicorn main:app --reload
```

### 2. 테스트

```bash
# 구문 검사
python -m py_compile main.py auth.py database.py models.py routers/*.py

# 서버 상태 확인
curl http://localhost:8001/health
```

### 3. 코드 구조

- **main.py**: 메인 애플리케이션 및 라우터 등록
- **auth.py**: JWT 인증 시스템 (통합)
- **database.py**: PostgreSQL 연결 관리
- **models.py**: Pydantic 스키마 정의
- **routers/**: 기능별 API 라우터 모음

## 🐳 배포

### Docker 배포

```bash
# 이미지 빌드
docker build -t hapa-db-module .

# 컨테이너 실행
docker run -p 8001:8001 --env-file .env hapa-db-module
```

### 운영 환경 배포

```bash
# 운영 환경 설정 사용
cp .env.production .env

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8001
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

<div align="center">
  <p>🚀 <strong>HAPA DB Module</strong> - 사용자 중심 개인화 마이크로서비스</p>
  <p>Made with ❤️ by HAPA Team</p>
</div>
