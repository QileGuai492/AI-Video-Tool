"""角色库接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Character, CharacterMultiView, User
from app.schemas.character import (
    CharacterCreate,
    CharacterDetailRead,
    CharacterMultiViewCreate,
    CharacterMultiViewRead,
    CharacterRead,
)

router = APIRouter(prefix="/characters", tags=["角色库"])


def _get_owned_character(db: Session, character_id: int, user_id: int) -> Character:
    """获取当前用户拥有的角色，不存在时返回 404。"""
    character = db.query(Character).filter(
        Character.id == character_id,
        Character.user_id == user_id,
    ).first()
    if character is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return character


@router.get("", response_model=list[CharacterRead])
def list_characters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Character]:
    """获取当前用户的角色列表。"""
    return db.query(Character).filter(Character.user_id == current_user.id).all()


@router.post("", response_model=CharacterRead)
def create_character(
    payload: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Character:
    """上传 / 创建角色。"""
    character = Character(
        user_id=current_user.id,
        name=payload.name,
        reference_image_url=payload.reference_image_url,
        description=payload.description,
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return character


@router.get("/{character_id}", response_model=CharacterDetailRead)
def get_character_detail(
    character_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Character:
    """获取角色详情，包含多角度参考图。"""
    return _get_owned_character(db, character_id, current_user.id)


@router.post("/{character_id}/multi-views", response_model=CharacterMultiViewRead)
def add_character_multi_view(
    character_id: int,
    payload: CharacterMultiViewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CharacterMultiView:
    """为角色添加多角度参考图。"""
    _get_owned_character(db, character_id, current_user.id)
    multi_view = CharacterMultiView(
        character_id=character_id,
        view_name=payload.view_name,
        image_url=payload.image_url,
    )
    db.add(multi_view)
    db.commit()
    db.refresh(multi_view)
    return multi_view
