"""QA router: AI-powered question answering over knowledge base."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared_config.settings import Settings
from shared_models import User
from shared_schemas.common import DataResponse, ErrorDetail
from shared_schemas.qa import QARequest

from app.deps import get_current_user, get_db, get_settings_dep
from app.services.qa_service import QAService

router = APIRouter(prefix="/v1/qa", tags=["qa"])


@router.post(
    "/ask",
    summary="Ask a question about the knowledge base",
    description="Uses RAG (Retrieval-Augmented Generation) to answer questions. Set stream=true for SSE streaming.",
    responses={
        200: {"description": "Answer generated with sources and related questions"},
        400: {"description": "Model not configured or query too short", "model": ErrorDetail},
        401: {"description": "Not authenticated", "model": ErrorDetail},
        502: {"description": "AI service unavailable", "model": ErrorDetail},
    },
)
async def ask(
    body: QARequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings_dep),
):
    svc = QAService(db, current_user.tenant_id, settings)

    if body.stream:
        return StreamingResponse(
            svc.ask_stream(body.project_id, body.question, body.top_k),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = await svc.ask(body.project_id, body.question, body.top_k)
    return DataResponse(data=result)
