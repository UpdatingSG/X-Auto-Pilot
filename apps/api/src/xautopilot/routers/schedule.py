from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from xautopilot.database import get_db
from xautopilot.dependencies import get_current_user
from xautopilot.models.user import User
from xautopilot.schemas.schedule import ScheduleResponse, ScheduleUpdate
from xautopilot.services.schedule_service import get_schedule, update_schedule

router = APIRouter(prefix="/v1/schedule", tags=["schedule"])


@router.get("", response_model=ScheduleResponse)
async def read_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_schedule(db, current_user.id)


@router.put("", response_model=ScheduleResponse)
async def save_schedule(
    data: ScheduleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = data.model_dump(exclude_none=True)
    if "posting_windows" in payload:
        payload["posting_windows"] = [w.model_dump() if hasattr(w, "model_dump") else w for w in payload["posting_windows"]]
    return await update_schedule(db, current_user.id, payload)
