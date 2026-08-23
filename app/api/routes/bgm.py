"""BGM 曲库接口。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import BgmLibrary, User

router = APIRouter(prefix="/bgm", tags=["BGM 曲库"])


class BgmLibraryRead(BaseModel):
    """BGM 曲目响应。"""

    id: int
    name: str
    url: str
    tags: dict | None = None
    license: str | None = None
    is_builtin: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[BgmLibraryRead])
def list_bgm_library(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[BgmLibrary]:
    """列出可用 BGM 曲目。"""
    return db.query(BgmLibrary).order_by(BgmLibrary.id).all()
