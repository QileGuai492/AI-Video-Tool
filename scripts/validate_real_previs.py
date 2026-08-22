"""真实 SiliconFlow 白模端到端验证脚本。

前置条件：
- `.env` 中已配置 SILICONFLOW_API_KEY
- SiliconFlow 账户有余额/权限

用法：
    python scripts/validate_real_previs.py
"""

import os
import shutil
import time
import uuid
from pathlib import Path

os.environ["APP_ENV"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///./.eval_tmp/real_eval.db"
# 保留 .env 中的 SILICONFLOW_API_KEY，使用真实 Provider
Path(".eval_tmp").mkdir(exist_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    """执行真实白模端到端验证。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    Path("uploads/videos").mkdir(parents=True, exist_ok=True)
    shutil.copyfile("app/providers/assets/mock_clip.mp4", "uploads/videos/previs_real.mp4")

    with TestClient(app) as client:
        username = f"real_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "Real@12345", "email": f"{username}@example.com"},
        )
        print("register", response.status_code)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/v1/generate/video",
            headers=headers,
            json={
                "prompt": "真实白模端到端验证",
                "previs_video_url": "/uploads/videos/previs_real.mp4",
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
        print("submit", response.status_code, response.text[:200])
        task_id = response.json()["id"]

        final_status = None
        for _ in range(120):
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


if __name__ == "__main__":
    main()
