"""用户设置接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Setting, User
from app.schemas.settings import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["用户设置"])


def _get_or_create_setting(db: Session, user_id: int) -> Setting:
    """获取当前用户设置，不存在则创建。"""
    setting = db.query(Setting).filter(Setting.user_id == user_id).first()
    if setting is None:
        setting = Setting(user_id=user_id)
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting


@router.get("", response_model=SettingsRead)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Setting:
    """获取当前用户设置。"""
    return _get_or_create_setting(db, current_user.id)


@router.put("", response_model=SettingsRead)
def update_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Setting:
    """更新当前用户设置。"""
    setting = _get_or_create_setting(db, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(setting, key, value)
    db.commit()
    db.refresh(setting)
    return setting
