from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os

from rag.ingestor import DocumentIngestor

router = APIRouter()
bearer = HTTPBearer()
_JWT_SECRET = os.getenv("JWT_SECRET_KEY", "change-me-in-production")


def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, _JWT_SECRET, algorithms=["HS256"])
        return payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(401, "Invalid token")


@router.post("/news")
async def trigger_news_ingestion(user_id: str = Depends(get_user_id)):
    """Manually trigger financial news ingestion into RAG store."""
    ingestor = DocumentIngestor()
    count = await ingestor.ingest_news()
    return {"ingested": count, "message": f"Ingested {count} news articles into RAG store"}


@router.post("/knowledge")
async def refresh_knowledge_base(user_id: str = Depends(get_user_id)):
    """Re-seed the financial knowledge base."""
    ingestor = DocumentIngestor()
    await ingestor.ingest_knowledge_base()
    return {"message": "Knowledge base refreshed"}