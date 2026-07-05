from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.knowledge import (
    FetchResultResponse,
    KnowledgeItemResponse,
    SourceCreate,
    SourceResponse,
)
from xautopilot.services.ingestion_service import (
    SourceNotFoundError,
    create_source,
    ingest_from_source,
    list_knowledge_items,
    list_sources,
)

router = APIRouter(prefix="/v1", tags=["knowledge"])


@router.get("/sources", response_model=list[SourceResponse])
async def get_sources(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_sources(db, current_user.id)


@router.post("/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def add_source(
    data: SourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_source(db, current_user.id, data)


@router.post("/sources/{source_id}/fetch", response_model=FetchResultResponse)
async def fetch_source(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await ingest_from_source(db, current_user.id, source_id)
    except SourceNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found") from None
    return FetchResultResponse(source_id=source_id, **result)


@router.get("/knowledge/items", response_model=list[KnowledgeItemResponse])
async def get_knowledge_items(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_knowledge_items(db, current_user.id)
