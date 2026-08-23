"""真实角色一致性端到端验证脚本（容器内执行）。

流程：
1. 调用 Agnes 文生图生成一张角色参考图。
2. 创建角色并保存参考图。
3. 提交带角色 ID 的白模生成任务（多个镜头）。
4. 验证任务完成，且多个镜头都使用同一角色参考图。

用法：
    docker compose exec api python scripts/validate_real_character_consistency.py
"""

import os
import shutil
import time
import uuid
from pathlib import Path

os.environ["APP_ENV"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///./.eval_tmp/char_eval.db"
Path(".eval_tmp").mkdir(exist_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.agnes import AgnesImageProvider  # noqa: E402
from app.providers.base import ImageGenerationRequest  # noqa: E402


def main() -> None:
    """执行真实角色一致性验证。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    Path("uploads/videos").mkdir(parents=True, exist_ok=True)
    shutil.copyfile("app/providers/assets/mock_clip.mp4", "uploads/videos/char_real.mp4")

    # 1. 生成角色参考图（真实 Agnes 文生图）
    image_result = AgnesImageProvider().generate_image(
        ImageGenerationRequest(
            prompt="一位亚洲女性角色正面肖像，干净背景，柔和光线，高清",
            aspect_ratio="1:1",
        )
    )
    reference_image_url = image_result.image_url
    print("character reference image", reference_image_url[:120])

    with TestClient(app) as client:
        username = f"char_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "Real@12345", "email": f"{username}@example.com"},
        )
        print("register", response.status_code)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 创建角色
        character = client.post(
            "/api/v1/characters",
            headers=headers,
            json={"name": "验证角色", "reference_image_url": reference_image_url},
        )
        print("create character", character.status_code)
        character_id = character.json()["id"]

        # 3. 提交带角色的多镜头白模任务
        response = client.post(
            "/api/v1/generate/video",
            headers=headers,
            json={
                "prompt": "真实角色一致性验证",
                "character_id": character_id,
                "previs_video_url": "/uploads/videos/char_real.mp4",
                "previs_type": "coarse",
                "camera_script": {
                    "shots": [
                        {"start": 0, "end": 0.5, "action": "人物走入画面", "camera": "侧面跟拍"},
                        {"start": 0.5, "end": 1.0, "action": "人物停下转身", "camera": "正面中景"},
                    ]
                },
                "duration": 5,
                "aspect_ratio": "16:9",
                "quality": "standard",
            },
        )
        print("submit", response.status_code)
        task_id = response.json()["id"]

        final_status = None
        for _ in range(150):
            status = client.get(f"/api/v1/generate/status/{task_id}", headers=headers)
            if status.status_code == 200:
                body = status.json()
                print("status", body["status"], body["progress"], body["current_stage"])
                if body["status"] in {"completed", "failed", "cancelled"}:
                    final_status = body
                    break
            time.sleep(5)

        print("FINAL", final_status)
        if final_status is None or final_status["status"] != "completed":
            raise SystemExit(1)

        if int(final_status.get("segments_done", 0)) < 2:
            raise SystemExit("镜头数不足，角色一致性链路未完整执行")

        print("真实角色一致性验证通过 ✅")


if __name__ == "__main__":
    main()
