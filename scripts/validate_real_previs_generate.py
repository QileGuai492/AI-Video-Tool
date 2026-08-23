"""真实文字生成白模验证脚本（容器内执行）。

调用 Agnes LLM 生成白模场景 JSON，并验证项目创建成功。

用法：
    docker compose exec api python scripts/validate_real_previs_generate.py
"""

import os
import uuid
from pathlib import Path

os.environ["APP_ENV"] = "local"
os.environ["DATABASE_URL"] = "sqlite:///./.eval_tmp/previs_gen_eval.db"
Path(".eval_tmp").mkdir(exist_ok=True)

from fastapi.testclient import TestClient  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    """执行真实文字生成白模验证。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as client:
        username = f"previs_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": "Real@12345", "email": f"{username}@example.com"},
        )
        print("register", response.status_code)
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(
            "/api/v1/previs/generate",
            headers=headers,
            json={"prompt": "一只猫在夕阳下的街道上奔跑，镜头从侧面跟拍", "title": "真实文字生成白模"},
        )
        print("generate", response.status_code)
        if response.status_code != 200:
            print(response.text[:500])
            raise SystemExit(1)

        data = response.json()
        print("mode", data["mode"])
        print("objects", len(data["scene_json"].get("objects", [])))
        print("shots", len(data.get("camera_script", {}).get("shots", [])))

        if data["mode"] != "auto":
            raise SystemExit("模式不是 auto")
        if not data["scene_json"].get("objects"):
            raise SystemExit("生成场景没有对象")
        print("真实文字生成白模验证通过 ✅")


if __name__ == "__main__":
    main()
