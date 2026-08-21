"""模板接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Template, User
from app.schemas.template import TemplateCreate, TemplateRead

router = APIRouter(prefix="/templates", tags=["模板"])


@router.post("", response_model=TemplateRead)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Template:
    """保存模板。"""
    template = Template(
        user_id=current_user.id,
        name=payload.name,
        config_json=payload.config_json,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("", response_model=list[TemplateRead])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Template]:
    """获取模板市场：返回内置模板与当前用户自己的模板。"""
    return (
        db.query(Template)
        .filter(or_(Template.is_builtin.is_(True), Template.user_id == current_user.id))
        .order_by(Template.is_builtin.desc(), Template.created_at.desc())
        .all()
    )


@router.post("/{template_id}/fork", response_model=TemplateRead)
def fork_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Template:
    """复制模板到当前用户。"""
    template = (
        db.query(Template)
        .filter(
            Template.id == template_id,
            or_(Template.is_builtin.is_(True), Template.user_id == current_user.id),
        )
        .first()
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    fork = Template(
        user_id=current_user.id,
        name=f"{template.name}（副本）",
        config_json=template.config_json,
    )
    db.add(fork)
    db.commit()
    db.refresh(fork)
    return fork


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Template:
    """获取模板详情（内置模板或当前用户模板）。"""
    template = (
        db.query(Template)
        .filter(
            Template.id == template_id,
            or_(Template.is_builtin.is_(True), Template.user_id == current_user.id),
        )
        .first()
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return template
