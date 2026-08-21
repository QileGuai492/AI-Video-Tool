"""成本相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel


class CostItemRead(BaseModel):
    """单次 API 调用成本。"""

    provider: str
    call_type: str
    cost: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CostTaskRead(BaseModel):
    """任务成本明细。"""

    task_id: int
    total_cost: float
    items: list[CostItemRead]


class CostSummaryRead(BaseModel):
    """用户成本汇总。"""

    total_cost: float
    task_count: int
    call_count: int
