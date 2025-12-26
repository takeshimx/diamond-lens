from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import logging

logger = logging.getLogger(__name__)

# RAGサービスのインポート
try:
    from app.services.rag_service import MLBKnowledgeRAG
except ImportError:
    from backend.app.services.rag_service import MLBKnowledgeRAG

router = APIRouter(prefix="/rag", tags=["RAG"])

class RAGQuery(BaseModel):
    query: str
    session_id: Optional[str] = None
    n_results: Optional[int] = 3

class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[str]
    isRAG: bool = True


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_V2")


# RAGサービスのシングルトンインスタンス（起動時に一度だけ初期化）
rag_service = None

def get_rag_service() -> MLBKnowledgeRAG:
    """RAGサービスのインスタンスを取得（シングルトンパターン）"""
    global rag_service
    if rag_service is None:
        logger.info("Initializing RAG service...")
        rag_service = MLBKnowledgeRAG()
        logger.info("RAG service initialized")
    return rag_service

# Endpoint
@router.post("/ask-mlb-metrics", response_model=RAGQueryResponse)
async def ask_mlb_metrics(request: RAGQuery):
    """
    MLB メトリクス用語をRAGで回答

    Args:
        request: RAGQuery (query, session_id, n_results)
    
    Returns:
        RAGQueryResponse (answer, sources, isRAG)
    """
    try:
        if not GEMINI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY_V2 が設定されていません"
            )
        
        logger.info(f"RAG query received: {request.query}")

        # RAGサービスを取得
        rag = get_rag_service()

        # RAGで回答生成
        result = rag.generate_answer_with_context(
            query=request.query,
            gemini_api_key=GEMINI_API_KEY,
            n_results=request.n_results
        )

        return RAGQueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            isRAG=True
        )
    
    except Exception as e:
        logger.error(f"RAG処理エラー: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"RAG処理エラー: {str(e)}"
        )

@router.get("/health")
async def rag_health_check():
    """RAGサービスのヘルスチェック"""
    try:
        rag = get_rag_service()
        collection_count = rag.collection.count()
        
        return {
            "status": "ok",
            "service": "RAG",
            "documents_indexed": collection_count,
            "embedding_model": "all-MiniLM-L6-v2"
        }
    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"RAG service unavailable: {str(e)}"
        )