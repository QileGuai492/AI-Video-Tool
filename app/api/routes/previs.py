"""白模预演接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import PrevisProject, PrevisTemplate, User
from app.schemas.previs import (
    PrevisProjectCreate,
    PrevisProjectRead,
    PrevisProjectUpdate,
    PrevisTemplateCreate,
    PrevisTemplateRead,
)

router = APIRouter(prefix="/previs", tags=["白模预演"])


@router.get("/templates", response_model=list[PrevisTemplateRead])
def list_previs_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PrevisTemplate]:
    """获取白模模板：内置模板 + 当前用户自定义模板。"""
    return (
        db.query(PrevisTemplate)
        .filter(or_(PrevisTemplate.is_builtin.is_(True), PrevisTemplate.user_id == current_user.id))
        .order_by(PrevisTemplate.is_builtin.desc(), PrevisTemplate.created_at.desc())
        .all()
    )


@router.post("/templates", response_model=PrevisTemplateRead)
def create_previs_template(
    payload: PrevisTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrevisTemplate:
    """保存自定义白模模板。"""
    template = PrevisTemplate(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        thumbnail_url=payload.thumbnail_url,
        scene_json=payload.scene_json,
        category=payload.category,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.post("/projects", response_model=PrevisProjectRead)
def create_previs_project(
    payload: PrevisProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrevisProject:
    """创建白模项目。"""
    project = PrevisProject(
        user_id=current_user.id,
        template_id=payload.template_id,
        title=payload.title,
        mode=payload.mode,
        scene_json=payload.scene_json,
        camera_script=payload.camera_script,
        mapping_rules=payload.mapping_rules,
        status="draft",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[PrevisProjectRead])
def list_previs_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PrevisProject]:
    """获取当前用户的白模项目列表。"""
    return (
        db.query(PrevisProject)
        .filter(PrevisProject.user_id == current_user.id)
        .order_by(PrevisProject.updated_at.desc())
        .all()
    )


@router.get("/projects/{project_id}", response_model=PrevisProjectRead)
def get_previs_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrevisProject:
    """获取白模项目详情。"""
    project = _get_owned_project(db, project_id, current_user.id)
    return project


@router.put("/projects/{project_id}", response_model=PrevisProjectRead)
def update_previs_project(
    project_id: int,
    payload: PrevisProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrevisProject:
    """保存白模项目场景/镜头脚本。"""
    project = _get_owned_project(db, project_id, current_user.id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.post("/projects/{project_id}/render", response_model=PrevisProjectRead)
def render_previs_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrevisProject:
    """渲染白模视频。

    Phase 1 先模拟渲染状态流转；后续接入 Three.js 录制/Blender 渲染服务。
    """
    project = _get_owned_project(db, project_id, current_user.id)
    project.status = "rendering"
    db.commit()
    # TODO: 接入真实白模渲染服务后，这里改为异步任务
    project.status = "ready"
    db.commit()
    db.refresh(project)
    return project


def _get_owned_project(db: Session, project_id: int, user_id: int) -> PrevisProject:
    """获取当前用户拥有的白模项目。"""
    project = (
        db.query(PrevisProject)
        .filter(PrevisProject.id == project_id, PrevisProject.user_id == user_id)
        .first()
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="白模项目不存在")
    return project
