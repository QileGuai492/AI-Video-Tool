"""成本查询接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import GenerationLog, User, VideoTask
from app.schemas.cost import CostItemRead, CostSummaryRead, CostTaskRead

router = APIRouter(prefix="/cost", tags=["成本"])


@router.get("/task/{task_id}", response_model=CostTaskRead)
def get_task_cost(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostTaskRead:
    """查询指定任务的成本明细。"""
    task = db.query(VideoTask).filter(
        VideoTask.id == task_id,
        VideoTask.user_id == current_user.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    logs = (
        db.query(GenerationLog)
        .filter(GenerationLog.task_id == task_id, GenerationLog.user_id == current_user.id)
        .all()
    )
    total = sum(float(log.cost or 0) for log in logs)
    return CostTaskRead(
        task_id=task_id,
        total_cost=total,
        items=[CostItemRead.model_validate(log) for log in logs],
    )


@router.get("/summary", response_model=CostSummaryRead)
def get_cost_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CostSummaryRead:
    """查询当前用户的成本汇总。"""
    total_cost = (
        db.query(func.coalesce(func.sum(GenerationLog.cost), 0))
        .filter(GenerationLog.user_id == current_user.id)
        .scalar()
    )
    task_count = (
        db.query(func.count(VideoTask.id))
        .filter(VideoTask.user_id == current_user.id)
        .scalar()
    )
    call_count = (
        db.query(func.count(GenerationLog.id))
        .filter(GenerationLog.user_id == current_user.id)
        .scalar()
    )
    return CostSummaryRead(
        total_cost=float(total_cost or 0),
        task_count=int(task_count or 0),
        call_count=int(call_count or 0),
    )
