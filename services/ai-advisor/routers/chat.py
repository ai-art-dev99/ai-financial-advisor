"""
Chat Router
POST /chat/message    → Server-Sent Events streaming response
GET  /chat/history    → conversation history
DELETE /chat/session  → clear session
"""
import json
import logging
import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

from conversation import conversation_manager
from rag.retriever import rag_retriever
from rag.ingestor import DocumentIngestor
from llm.client import llm_client
from llm.prompt_builder import build_system_prompt
from llm.portfolio_fetcher import fetch_portfolio_context

logger = logging.getLogger(__name__)
router = APIRouter()
bearer = HTTPBearer()

_JWT_SECRET = os.getenv("JWT_SECRET_KEY", "change-me-in-production")


def get_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, _JWT_SECRET, algorithms=["HS256"])
        return payload["sub"]
    except (JWTError, KeyError):
        raise HTTPException(401, "Invalid token")


class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    include_portfolio: bool = True


class HistoryResponse(BaseModel):
    session_id: str
    messages: list


@router.post("/message")
async def chat_message(
    payload: ChatMessage,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    user_id: str = Depends(get_user_id),
):
    """
    Stream a chat response using Server-Sent Events (SSE).
    Each event is: data: {"type": "token"|"done"|"error", "content": "..."}
    """
    session_id = payload.session_id or f"{user_id}:{uuid.uuid4().hex[:8]}"
    access_token = credentials.credentials

    async def event_stream():
        full_response = ""
        try:
            # 1. Load conversation history
            history = await conversation_manager.get_history(session_id)

            # 2. Fetch portfolio context (non-blocking, degrades gracefully)
            portfolio_summary, risk_profile = None, None
            if payload.include_portfolio:
                portfolio_summary, risk_profile = await fetch_portfolio_context(
                    user_id, access_token
                )
                # Update portfolio in RAG store
                if portfolio_summary:
                    ingestor = DocumentIngestor()
                    await ingestor.ingest_portfolio_snapshot(
                        user_id,
                        portfolio_summary.get("holdings", []),
                        portfolio_summary,
                    )

            # 3. RAG retrieval
            rag_context = rag_retriever.retrieve(payload.message, user_id)

            # 4. Build system prompt
            system_prompt = build_system_prompt(
                risk_profile=risk_profile,
                portfolio_summary=portfolio_summary,
                rag_context=rag_context,
            )

            # 5. Build message list (history + new message)
            messages = history + [{"role": "user", "content": payload.message}]

            # 6. Send session_id first so client can track it
            yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            # 7. Stream Claude's response
            async for chunk in llm_client.stream(messages, system_prompt):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

            # 8. Done signal
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            # 9. Save to history
            if full_response:
                await conversation_manager.append_messages(session_id, [
                    {"role": "user", "content": payload.message},
                    {"role": "assistant", "content": full_response},
                ])

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(
    session_id: str,
    user_id: str = Depends(get_user_id),
):
    messages = await conversation_manager.get_history(session_id)
    return HistoryResponse(session_id=session_id, messages=messages)


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str,
    user_id: str = Depends(get_user_id),
):
    await conversation_manager.clear_session(session_id)
    return {"message": "Session cleared", "session_id": session_id}