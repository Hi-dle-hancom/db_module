"""
HAPA 보안 강화 JWT 관리자
암호학적으로 안전한 키 로드 및 관리 시스템
"""

import os
import logging
import secrets
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import warnings

logger = logging.getLogger(__name__)

class SecureJWTManager:
    """보안 강화된 JWT 키 관리자"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.secrets_dir = self.project_root / "secrets"
        self.environment = os.getenv("ENVIRONMENT", "development")
        self._secret_key: Optional[str] = None
        self._key_metadata: Dict[str, Any] = {}
    
    def get_jwt_secret_key(self) -> str:
        """안전한 JWT 시크릿 키 로드"""
        if self._secret_key:
            return self._secret_key
        
        # 1. 환경변수에서 우선 로드
        env_key = os.getenv("JWT_SECRET_KEY")
        if env_key and self._validate_key_security(env_key):
            self._secret_key = env_key
            logger.info("🔐 JWT 키를 환경변수에서 로드함")
            return self._secret_key
        
        # 2. 시크릿 파일에서 로드
        secret_file = self.secrets_dir / f"jwt_secret_{self.environment}.key"
        if secret_file.exists():
            try:
                with open(secret_file, 'r') as f:
                    file_key = f.read().strip()
                
                if self._validate_key_security(file_key):
                    self._secret_key = file_key
                    self._load_key_metadata()
                    logger.info(f"🔐 JWT 키를 파일에서 로드함: {secret_file.name}")
                    return self._secret_key
            except Exception as e:
                logger.error(f"시크릿 파일 로드 실패: {e}")
        
        # 3. 개발 환경에서만 안전한 키 생성
        if self.environment == "development":
            return self._generate_development_key()
        
        # 4. 운영 환경에서는 키가 없으면 실패
        raise ValueError(
            f"🚨 [{self.environment.upper()}] JWT_SECRET_KEY를 찾을 수 없습니다!\n"
            f"다음 중 하나를 설정해주세요:\n"
            f"  1. 환경변수: JWT_SECRET_KEY\n"
            f"  2. 시크릿 파일: {secret_file}\n"
            f"  3. 키 생성: python scripts/generate-jwt-secret.py --generate"
        )
    
    def _validate_key_security(self, key: str) -> bool:
        """키 보안 강도 검증"""
        if not key:
            return False
        
        # 최소 길이 검증 (256비트 = 32바이트 최소)
        if len(key) < 43:  # Base64로 32바이트 = 43+ 문자
            logger.warning(f"⚠️ JWT 키가 너무 짧습니다: {len(key)}자 (최소 43자 권장)")
            if self.environment == "production":
                return False
        
        # 약한 패턴 검사
        weak_patterns = [
            "secret", "key", "password", "admin", "test", "demo", "dev",
            "default", "change", "example", "sample", "hapa", "development"
        ]
        
        key_lower = key.lower()
        for pattern in weak_patterns:
            if pattern in key_lower:
                logger.warning(f"⚠️ JWT 키에 약한 패턴 감지: '{pattern}'")
                if self.environment == "production":
                    return False
        
        # 엔트로피 검증 (간단한 휴리스틱)
        unique_chars = len(set(key))
        if unique_chars < len(key) * 0.6:  # 60% 이상 고유 문자
            logger.warning(f"⚠️ JWT 키의 엔트로피가 낮습니다: {unique_chars}/{len(key)} 고유 문자")
            if self.environment == "production":
                return False
        
        return True
    
    def _generate_development_key(self) -> str:
        """개발 환경용 안전한 키 동적 생성"""
        warnings.warn(
            "🔶 개발 환경에서 임시 JWT 키를 생성합니다. "
            "운영 환경에서는 고정된 안전한 키를 사용하세요!",
            UserWarning
        )
        
        # 64바이트 암호학적으로 안전한 키 생성
        random_bytes = secrets.token_bytes(64)
        generated_key = secrets.token_urlsafe(64)
        
        # 키 식별자 생성
        key_hash = hashlib.sha256(generated_key.encode()).hexdigest()[:16]
        
        self._key_metadata = {
            'generated': True,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'key_id': f"dev_generated_{key_hash}",
            'entropy_bits': 512,
            'temporary': True
        }
        
        logger.info(f"🔐 개발용 임시 JWT 키 생성됨 (ID: {self._key_metadata['key_id']})")
        logger.warning("⚠️ 이 키는 서버 재시작 시 변경됩니다. 운영 환경에서는 고정 키를 사용하세요!")
        
        self._secret_key = generated_key
        return generated_key
    
    def _load_key_metadata(self):
        """키 메타데이터 로드"""
        meta_file = self.secrets_dir / f"jwt_secret_{self.environment}.json"
        if meta_file.exists():
            try:
                import json
                with open(meta_file, 'r') as f:
                    self._key_metadata = json.load(f)
                    
                logger.info(f"📊 키 메타데이터 로드됨: {self._key_metadata.get('key_id', 'unknown')}")
            except Exception as e:
                logger.warning(f"메타데이터 로드 실패: {e}")
    
    def get_key_info(self) -> Dict[str, Any]:
        """키 정보 반환 (보안 정보는 제외)"""
        if not self._secret_key:
            self.get_jwt_secret_key()
        
        return {
            'key_loaded': bool(self._secret_key),
            'key_length': len(self._secret_key) if self._secret_key else 0,
            'environment': self.environment,
            'key_id': self._key_metadata.get('key_id', 'unknown'),
            'created_at': self._key_metadata.get('created_at'),
            'is_temporary': self._key_metadata.get('temporary', False),
            'entropy_bits': self._key_metadata.get('entropy_bits', 'unknown')
        }
    
    def validate_jwt_setup(self) -> Dict[str, Any]:
        """JWT 설정 전체 검증"""
        result = {
            'status': 'healthy',
            'issues': [],
            'recommendations': []
        }
        
        try:
            key = self.get_jwt_secret_key()
            key_info = self.get_key_info()
            
            # 보안 검사
            if key_info['is_temporary']:
                result['issues'].append("임시 키 사용 중 (개발 환경에서만 허용)")
                if self.environment != "development":
                    result['status'] = 'warning'
            
            if key_info['key_length'] < 43:
                result['issues'].append(f"키 길이 부족: {key_info['key_length']}자 (최소 43자 권장)")
                result['status'] = 'warning'
            
            if self.environment == "production" and key_info['is_temporary']:
                result['issues'].append("운영 환경에서 임시 키 사용 중")
                result['status'] = 'critical'
            
            # 권장사항
            if not self._key_metadata.get('key_id'):
                result['recommendations'].append("키 메타데이터 파일이 없습니다. 키 생성 도구 사용 권장")
            
            if self.environment == "development" and not key_info['is_temporary']:
                result['recommendations'].append("개발 환경에서 고정 키 사용 중. 보안상 문제없음")
            
        except Exception as e:
            result['status'] = 'critical'
            result['issues'].append(f"JWT 키 로드 실패: {str(e)}")
        
        return result

# 전역 인스턴스
jwt_manager = SecureJWTManager()

# 하위 호환성을 위한 함수
def get_secure_secret_key() -> str:
    """보안 강화된 JWT 시크릿 키 반환"""
    return jwt_manager.get_jwt_secret_key()