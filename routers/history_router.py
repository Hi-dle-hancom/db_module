"""
HAPA DB Module - 히스토리 관리 라우터
MongoDB를 사용한 대화 히스토리 관리 API 엔드포인트
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Path

# 🔧 선택적 MongoDB 의존성 import (import 실패 시에도 라우터 등록은 가능)
try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from pymongo import DESCENDING
    from pymongo.errors import DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ MongoDB 의존성 없음: {e}")
    MONGODB_AVAILABLE = False
    # 임시 클래스들 (라우터 등록을 위해)
    class AsyncIOMotorDatabase:
        pass
    DESCENDING = -1
    class DuplicateKeyError(Exception):
        pass

from auth import get_current_user
from models import (
    ConversationEntry,
    ConversationSession,
    ConversationStatus,
    ConversationType,
    HistoryCreateRequest,
    HistoryResponse,
    HistorySearchRequest,
    HistoryStats,
    SessionCreateRequest,
    UserInDB,
)

# 선택적 MongoDB 연결
try:
    from database import get_mongo_db
except ImportError:
    # MongoDB가 없는 경우 더미 함수
    async def get_mongo_db():
        return None

router = APIRouter(prefix="/history", tags=["history"])

# ====== 세션 관리 엔드포인트 ======

@router.post("/sessions", response_model=ConversationSession)
async def create_session(
    request: SessionCreateRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """새로운 대화 세션을 생성합니다."""
    # MongoDB 가용성 체크
    if not MONGODB_AVAILABLE or db is None:
        raise HTTPException(
            status_code=503,
            detail="History service is temporarily unavailable (MongoDB not connected)"
        )
    
    try:
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        current_time = datetime.now()

        # MongoDB 세션 문서 생성
        session_doc = {
            "document_type": "session",
            "session_id": session_id,
            "user_id": current_user.id,
            "session_title": request.session_title or f"Session {session_id[:8]}",
            "status": ConversationStatus.ACTIVE.value,
            "primary_language": request.primary_language or "python",
            "tags": request.tags or [],
            "project_name": request.project_name,
            "total_entries": 0,
            "question_count": 0,
            "answer_count": 0,
            "created_at": current_time,
            "updated_at": current_time,
            "last_activity": current_time
        }

        # MongoDB에 삽입
        collection = db["history"]
        await collection.insert_one(session_doc)

        # 응답 객체 생성
        return ConversationSession(
            session_id=session_doc['session_id'],
            user_id=session_doc['user_id'],
            session_title=session_doc['session_title'],
            status=ConversationStatus(session_doc['status']),
            primary_language=session_doc['primary_language'],
            tags=session_doc['tags'],
            project_name=session_doc['project_name'],
            total_entries=session_doc['total_entries'],
            question_count=session_doc['question_count'],
            answer_count=session_doc['answer_count'],
            created_at=session_doc['created_at'],
            updated_at=session_doc['updated_at'],
            last_activity=session_doc['last_activity'],
        )

    except DuplicateKeyError:
        raise HTTPException(
            status_code=409, 
            detail=f"중복된 세션 ID입니다: {session_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"세션 생성에 실패했습니다: {str(e)}"
        )

@router.get("/sessions", response_model=List[Dict[str, Any]])
async def get_recent_sessions(
    limit: int = Query(20, description="조회할 세션 개수", ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """최근 대화 세션 목록을 조회합니다."""
    # MongoDB 가용성 체크
    if not MONGODB_AVAILABLE or db is None:
        # MongoDB가 없는 경우 빈 배열 반환 (404 대신 빈 결과로 처리)
        return []
    
    try:
        collection = db["history"]
        
        # MongoDB 쿼리 (세션만 조회)
        cursor = collection.find({
            "document_type": "session",
            "user_id": current_user.id
        }).sort("last_activity", DESCENDING).limit(limit)
        
        # 결과 변환
        result = []
        async for doc in cursor:
            doc['timestamp'] = doc['created_at'].isoformat()
            doc.pop('_id', None)  # MongoDB ObjectId 제거
            doc.pop('document_type', None)  # 불필요한 필드 제거
            result.append(doc)
        
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"세션 목록 조회에 실패했습니다: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_history(
    session_id: str = Path(..., description="조회할 세션 ID"),
    limit: int = Query(50, description="조회할 엔트리 개수", ge=1, le=200),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """특정 세션의 대화 히스토리를 조회합니다."""
    try:
        collection = db["history"]
        
        # 세션 소유권 확인
        session = await collection.find_one({
            "document_type": "session",
            "session_id": session_id,
            "user_id": current_user.id
        })
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"세션을 찾을 수 없거나 접근 권한이 없습니다: {session_id}"
            )
        
        # MongoDB 쿼리 (엔트리만 조회)
        cursor = collection.find({
            "document_type": "entry",
            "session_id": session_id,
            "user_id": current_user.id
        }).sort("created_at", DESCENDING).limit(limit)
        
        # 결과 변환
        result = []
        async for doc in cursor:
            doc['timestamp'] = doc['created_at'].isoformat()
            doc.pop('_id', None)  # MongoDB ObjectId 제거
            doc.pop('document_type', None)  # 불필요한 필드 제거
            result.append(doc)
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"세션 히스토리 조회에 실패했습니다: {str(e)}"
        )

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str = Path(..., description="삭제할 세션 ID"),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """특정 세션과 관련된 모든 데이터를 삭제합니다."""
    try:
        collection = db["history"]
        
        # 세션 소유권 확인
        session = await collection.find_one({
            "document_type": "session",
            "session_id": session_id,
            "user_id": current_user.id
        })
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"세션을 찾을 수 없거나 접근 권한이 없습니다: {session_id}"
            )
        
        # 세션과 관련된 모든 엔트리 삭제
        entries_result = await collection.delete_many({
            "document_type": "entry",
            "session_id": session_id,
            "user_id": current_user.id
        })
        
        # 세션 삭제
        session_result = await collection.delete_one({
            "document_type": "session",
            "session_id": session_id,
            "user_id": current_user.id
        })
        
        return {
            "success": True,
            "message": f"세션 {session_id}이 성공적으로 삭제되었습니다.",
            "session_id": session_id,
            "deleted_entries": entries_result.deleted_count,
            "deleted_sessions": session_result.deleted_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"세션 삭제에 실패했습니다: {str(e)}"
        )

# ====== 히스토리 엔트리 관리 엔드포인트 ======

@router.post("/entries", response_model=HistoryResponse)
async def add_history_entry(
    request: HistoryCreateRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """대화 세션에 새로운 엔트리를 추가합니다."""
    try:
        collection = db["history"]
        
        # 세션 존재 및 소유권 확인
        session = await collection.find_one({
            "document_type": "session",
            "session_id": request.session_id,
            "user_id": current_user.id
        })
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"세션을 찾을 수 없거나 접근 권한이 없습니다: {request.session_id}"
            )

        entry_id = f"entry_{uuid.uuid4().hex[:8]}"
        current_time = datetime.now()

        # MongoDB 엔트리 문서 생성
        entry_doc = {
            "document_type": "entry",
            "entry_id": entry_id,
            "session_id": request.session_id,
            "user_id": current_user.id,
            "conversation_type": request.conversation_type.value,
            "content": request.content,
            "language": request.language,
            "code_snippet": request.code_snippet,
            "file_name": request.file_name,
            "line_number": request.line_number,
            "response_time": request.response_time,
            "confidence_score": request.confidence_score,
            "created_at": current_time
        }

        # MongoDB에 삽입
        await collection.insert_one(entry_doc)

        # 세션 통계 업데이트
        await _update_session_stats(collection, request.session_id, request.conversation_type)

        return HistoryResponse(
            success=True,
            entry_id=entry_id,
            session_id=request.session_id,
            message="히스토리 엔트리가 추가되었습니다.",
            timestamp=current_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"히스토리 엔트리 추가에 실패했습니다: {str(e)}"
        )

# ====== 검색 및 통계 엔드포인트 ======

@router.post("/search", response_model=List[Dict[str, Any]])
async def search_history(
    request: HistorySearchRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """대화 히스토리를 검색합니다."""
    try:
        collection = db["history"]
        
        # MongoDB 검색 쿼리 구성
        query = {
            "document_type": "entry",  # 엔트리만 검색
            "user_id": current_user.id,
            "$text": {"$search": request.query}  # 텍스트 검색
        }

        # 추가 필터 조건들
        if request.session_ids:
            query["session_id"] = {"$in": request.session_ids}

        if request.language:
            query["language"] = request.language

        if request.conversation_type:
            query["conversation_type"] = request.conversation_type.value

        if request.date_from or request.date_to:
            date_filter = {}
            if request.date_from:
                date_filter["$gte"] = request.date_from
            if request.date_to:
                date_filter["$lte"] = request.date_to
            query["created_at"] = date_filter

        # MongoDB 쿼리 실행
        cursor = collection.find(query).sort("created_at", DESCENDING).limit(request.limit)
        
        # 결과 변환
        result = []
        async for doc in cursor:
            doc['timestamp'] = doc['created_at'].isoformat()
            doc.pop('_id', None)
            doc.pop('document_type', None)
            result.append(doc)
        
        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"히스토리 검색에 실패했습니다: {str(e)}"
        )

@router.get("/stats", response_model=HistoryStats)
async def get_history_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """대화 히스토리 통계를 조회합니다."""
    try:
        collection = db["history"]
        
        # MongoDB Aggregation Pipeline (세션 통계)
        session_pipeline = [
            {"$match": {"document_type": "session", "user_id": current_user.id}},
            {"$group": {
                "_id": None,
                "total_sessions": {"$sum": 1},
                "active_sessions": {"$sum": {"$cond": [{"$eq": ["$status", "active"]}, 1, 0]}},
                "total_entries": {"$sum": "$total_entries"},
                "total_questions": {"$sum": "$question_count"},
                "total_answers": {"$sum": "$answer_count"},
            }}
        ]

        session_result = await collection.aggregate(session_pipeline).to_list(1)
        session_stats = session_result[0] if session_result else {}

        # 언어 분포 통계
        language_pipeline = [
            {"$match": {"document_type": "session", "user_id": current_user.id}},
            {"$group": {"_id": "$primary_language", "count": {"$sum": 1}}}
        ]

        language_result = await collection.aggregate(language_pipeline).to_list(None)
        language_distribution = {item["_id"]: item["count"] for item in language_result}

        return HistoryStats(
            total_sessions=session_stats.get("total_sessions", 0),
            active_sessions=session_stats.get("active_sessions", 0),
            total_entries=session_stats.get("total_entries", 0),
            total_questions=session_stats.get("total_questions", 0),
            total_answers=session_stats.get("total_answers", 0),
            language_distribution=language_distribution,
            sessions_today=0,  # TODO: 구현 필요
            sessions_this_week=0,  # TODO: 구현 필요
            average_session_length=0.0  # TODO: 구현 필요
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"히스토리 통계 조회에 실패했습니다: {str(e)}"
        )

# ====== 헬스 체크 엔드포인트 ======

@router.get("/health")
async def health_check(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db),
):
    """히스토리 서비스의 상태를 확인합니다."""
    try:
        collection = db["history"]
        
        total_sessions = await collection.count_documents({"document_type": "session"})
        total_entries = await collection.count_documents({"document_type": "entry"})

        return {
            "status": "healthy",
            "service": "history",
            "version": "1.0.0",
            "total_sessions": total_sessions,
            "total_entries": total_entries,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "history",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }

# ====== 헬퍼 함수 ======

async def _update_session_stats(collection, session_id: str, conversation_type: ConversationType):
    """세션 통계 업데이트"""
    try:
        update_query = {
            "$inc": {"total_entries": 1},
            "$set": {"updated_at": datetime.now(), "last_activity": datetime.now()}
        }

        if conversation_type == ConversationType.QUESTION:
            update_query["$inc"]["question_count"] = 1
        elif conversation_type == ConversationType.ANSWER:
            update_query["$inc"]["answer_count"] = 1

        await collection.update_one(
            {
                "document_type": "session",
                "session_id": session_id
            },
            update_query
        )

    except Exception as e:
        # 통계 업데이트 실패는 치명적이지 않음
        pass