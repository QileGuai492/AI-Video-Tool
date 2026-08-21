"""模板接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
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


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Template:
    """获取模板详情。"""
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == current_user.id,
    ).first()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return template
