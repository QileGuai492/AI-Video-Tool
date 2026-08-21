"""文件上传接口。

存储层已抽象，默认保存到本地 uploads 目录，可通过 STORAGE_BACKEND=oss 切换为阿里云 OSS。
"""

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.models import User
from app.storage import storage

router = APIRouter(prefix="/upload", tags=["文件上传"])

# 允许的文件类型
ALLOWED_IMAGE = {"jpg", "jpeg", "png", "webp"}
ALLOWED_AUDIO = {"mp3", "wav"}
ALLOWED_VIDEO = {"mp4"}

# 文件类型对应的存储目录
FOLDER_BY_TYPE = {
    "image": "images",
    "audio": "audio",
    "video": "videos",
}


@router.post("")
def upload_file(
    file: UploadFile = File(...),
    file_type: str = "image",
    current_user: User = Depends(get_current_user),
) -> dict:
    """上传文件并返回可访问 URL。"""
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower().lstrip(".")
    if suffix not in ALLOWED_IMAGE | ALLOWED_AUDIO | ALLOWED_VIDEO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的文件类型")

    if file_type not in FOLDER_BY_TYPE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file_type 不合法")

    # 限制大小
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件过大")

    # 通过存储抽象保存文件
    key = storage.upload(content=content, suffix=suffix, folder=FOLDER_BY_TYPE[file_type])
    file_url = storage.get_url(key)

    return {
        "file_url": file_url,
        "file_type": file_type,
        "size": len(content),
    }
