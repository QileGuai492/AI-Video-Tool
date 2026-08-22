"""系统级端到端评测用例。

覆盖认证、视频任务提交/状态/下载、参数校验、角色库、历史记录、成本汇总。
"""

import time
import uuid

from app.models import User, VideoTask
from eval_harness.models import EvalCase, EvalContext, EvalOutcome


def _outcome(ok: bool, score: float, metrics: dict, details: str, trace: list[str] | None = None) -> EvalOutcome:
    return EvalOutcome(
        status="pass" if ok and score >= 0.999 else "fail",
        score=score,
        metrics=metrics,
        details=details,
        trace=trace or [],
    )


def _register(ctx: EvalContext, tag: str) -> tuple[dict, int]:
    """注册一个新用户，返回认证头和用户 ID。"""
    username = f"eval_{tag}_{uuid.uuid4().hex[:8]}"
    password = "Eval@12345"
    response = ctx.client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password, "email": f"{username}@example.com"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    db = ctx.db_session()
    try:
        user = db.query(User).filter(User.username == username).first()
        user_id = user.id if user else 1
    finally:
        db.close()
    return {"Authorization": f"Bearer {token}"}, user_id


def _case_auth(ctx: EvalContext) -> EvalOutcome:
    """系统认证：注册与登录应可用。"""
    username = f"auth_{uuid.uuid4().hex[:8]}"
    password = "Eval@12345"
    register = ctx.client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password, "email": f"{username}@example.com"},
    )
    login = ctx.client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    checks = {
        "注册成功": register.status_code == 200,
        "返回令牌": bool(register.json().get("access_token")),
        "登录成功": login.status_code == 200,
        "登录令牌可用": bool(login.json().get("access_token")),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"注册耗时_ms": register.elapsed.total_seconds() * 1000},
        details=f"注册状态：{register.status_code}，登录状态：{login.status_code}",
        trace=list(checks.items()),
    )


def _case_generate_flow(ctx: EvalContext) -> EvalOutcome:
    """系统生成链路：提交任务、查询状态、下载视频。"""
    headers, _ = _register(ctx, "gen")
    submit = ctx.client.post(
        "/api/v1/generate/video",
        headers=headers,
        json={
            "prompt": "一只猫在夕阳下奔跑",
            "duration": 5,
            "aspect_ratio": "16:9",
            "quality": "standard",
        },
    )
    if submit.status_code != 200:
        return _outcome(False, 0.0, {}, f"提交失败：{submit.text}")

    task_id = submit.json()["id"]
    status = None
    for _ in range(10):
        status = ctx.client.get(f"/api/v1/generate/status/{task_id}", headers=headers)
        if status.status_code == 200 and status.json()["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.5)

    download = ctx.client.get(f"/api/v1/generate/{task_id}/download", headers=headers)
    checks = {
        "提交成功": submit.status_code == 200,
        "状态查询成功": status is not None and status.status_code == 200,
        "任务完成": status is not None and status.json().get("status") == "completed",
        "下载成功": download.status_code in {200, 307},
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={
            "任务ID": float(task_id),
            "提交耗时_ms": submit.elapsed.total_seconds() * 1000,
            "下载状态码": float(download.status_code),
        },
        details=f"任务状态：{status.json().get('status') if status else 'unknown'}，下载状态：{download.status_code}",
        trace=list(checks.items()),
    )


def _case_validation(ctx: EvalContext) -> EvalOutcome:
    """系统健壮性：非法参数应返回统一校验错误。"""
    headers, _ = _register(ctx, "val")
    response = ctx.client.post(
        "/api/v1/generate/video",
        headers=headers,
        json={"prompt": "", "duration": 3, "aspect_ratio": "invalid"},
    )
    body = response.json()
    checks = {
        "返回 422": response.status_code == 422,
        "统一错误码": body.get("code") == "VALIDATION_ERROR",
        "错误详情存在": bool(body.get("details")),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"状态码": float(response.status_code)},
        details=f"响应：{response.text[:200]}",
        trace=list(checks.items()),
    )


def _case_character_flow(ctx: EvalContext) -> EvalOutcome:
    """角色库：创建角色并携带角色 ID 提交任务。"""
    headers, _ = _register(ctx, "char")
    character = ctx.client.post(
        "/api/v1/characters",
        headers=headers,
        json={"name": "评测角色", "reference_image_url": "https://example.com/ref.png"},
    )
    if character.status_code != 200:
        return _outcome(False, 0.0, {}, f"创建角色失败：{character.text}")
    character_id = character.json()["id"]

    submit = ctx.client.post(
        "/api/v1/generate/video",
        headers=headers,
        json={
            "prompt": "角色在花园里散步",
            "duration": 5,
            "aspect_ratio": "9:16",
            "character_id": character_id,
        },
    )
    checks = {
        "创建角色成功": character.status_code == 200,
        "携带角色提交成功": submit.status_code == 200,
        "任务 ID 存在": bool(submit.json().get("id")),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"角色ID": float(character_id)},
        details=f"角色创建：{character.status_code}，任务提交：{submit.status_code}",
        trace=list(checks.items()),
    )


def _case_history(ctx: EvalContext) -> EvalOutcome:
    """历史记录：应能查询当前用户的任务列表。"""
    headers, _ = _register(ctx, "hist")
    response = ctx.client.get("/api/v1/history", headers=headers)
    checks = {
        "查询成功": response.status_code == 200,
        "返回列表": isinstance(response.json(), list),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"历史数量": float(len(response.json()))},
        details=f"历史数量：{len(response.json())}",
        trace=list(checks.items()),
    )


def _case_cost_summary(ctx: EvalContext) -> EvalOutcome:
    """成本汇总：应能返回成本与任务统计。"""
    headers, _ = _register(ctx, "cost")
    response = ctx.client.get("/api/v1/cost/summary", headers=headers)
    body = response.json() if response.status_code == 200 else {}
    checks = {
        "查询成功": response.status_code == 200,
        "包含总成本": "total_cost" in body,
        "包含任务数": "task_count" in body,
        "包含调用数": "call_count" in body,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"总成本": float(body.get("total_cost", 0))},
        details=f"响应：{response.text[:200]}",
        trace=list(checks.items()),
    )


def _case_cancel_retry(ctx: EvalContext) -> EvalOutcome:
    """任务控制：应能取消 pending 任务并重试 failed 任务。"""
    headers, user_id = _register(ctx, "ctrl")
    db = ctx.db_session()
    try:
        pending = VideoTask(
            user_id=user_id,
            prompt="待取消任务",
            status="pending",
            duration=5,
            aspect_ratio="16:9",
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)

        failed = VideoTask(
            user_id=user_id,
            prompt="待重试任务",
            status="failed",
            duration=5,
            aspect_ratio="16:9",
        )
        db.add(failed)
        db.commit()
        db.refresh(failed)

        cancel = ctx.client.post(f"/api/v1/generate/{pending.id}/cancel", headers=headers)
        retry = ctx.client.post(f"/api/v1/generate/{failed.id}/retry", headers=headers)

        checks = {
            "取消成功": cancel.status_code == 200 and cancel.json().get("status") == "cancelled",
            "重试成功": retry.status_code == 200 and retry.json().get("status") == "pending",
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"取消状态码": float(cancel.status_code), "重试状态码": float(retry.status_code)},
            details=f"取消：{cancel.status_code}，重试：{retry.status_code}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


def _case_template(ctx: EvalContext) -> EvalOutcome:
    """模板：应能创建并读取模板。"""
    headers, _ = _register(ctx, "tmpl")
    create = ctx.client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "评测模板", "config_json": {"prompt": "测试模板", "duration": 5}},
    )
    if create.status_code != 200:
        return _outcome(False, 0.0, {}, f"创建模板失败：{create.text}")
    template_id = create.json()["id"]
    detail = ctx.client.get(f"/api/v1/templates/{template_id}", headers=headers)
    checks = {
        "创建成功": create.status_code == 200,
        "读取成功": detail.status_code == 200,
        "模板 ID 一致": detail.json().get("id") == template_id,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"模板ID": float(template_id)},
        details=f"创建：{create.status_code}，读取：{detail.status_code}",
        trace=list(checks.items()),
    )


def _case_upload(ctx: EvalContext) -> EvalOutcome:
    """上传：应能上传图片并返回 URL。"""
    headers, _ = _register(ctx, "up")
    response = ctx.client.post(
        "/api/v1/upload",
        headers=headers,
        files={"file": ("test.png", b"fake-image-bytes", "image/png")},
        data={"file_type": "image"},
    )
    body = response.json() if response.status_code == 200 else {}
    checks = {
        "上传成功": response.status_code == 200,
        "返回 URL": bool(body.get("file_url")),
        "返回大小": body.get("size") == len(b"fake-image-bytes"),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"上传大小": float(body.get("size", 0))},
        details=f"上传状态：{response.status_code}，URL：{body.get('file_url', '')}",
        trace=list(checks.items()),
    )


def _case_auth_wrong_password(ctx: EvalContext) -> EvalOutcome:
    """认证边界：错误密码应返回 401。"""
    username = f"wrong_{uuid.uuid4().hex[:8]}"
    password = "Eval@12345"
    ctx.client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password, "email": f"{username}@example.com"},
    )
    response = ctx.client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "wrong-password"},
    )
    ok = response.status_code == 401
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_auth_duplicate_register(ctx: EvalContext) -> EvalOutcome:
    """认证边界：重复注册应返回 400。"""
    username = f"dup_{uuid.uuid4().hex[:8]}"
    payload = {"username": username, "password": "Eval@12345", "email": f"{username}@example.com"}
    first = ctx.client.post("/api/v1/auth/register", json=payload)
    second = ctx.client.post("/api/v1/auth/register", json=payload)
    ok = first.status_code == 200 and second.status_code == 400
    return _outcome(ok, 1.0 if ok else 0.0, {"首次": float(first.status_code), "重复": float(second.status_code)}, f"首次：{first.status_code}，重复：{second.status_code}")


def _case_auth_invalid_token(ctx: EvalContext) -> EvalOutcome:
    """认证边界：无效 Token 应返回 401。"""
    response = ctx.client.get("/api/v1/history", headers={"Authorization": "Bearer invalid.token.value"})
    ok = response.status_code == 401
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_auth_missing_auth(ctx: EvalContext) -> EvalOutcome:
    """认证边界：未携带 Token 应返回 401。"""
    response = ctx.client.get("/api/v1/history")
    ok = response.status_code == 401
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_auth_missing_fields(ctx: EvalContext) -> EvalOutcome:
    """认证边界：缺少必填字段应返回 422。"""
    response = ctx.client.post("/api/v1/auth/register", json={"username": ""})
    body = response.json()
    ok = response.status_code == 422 and body.get("code") == "VALIDATION_ERROR"
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_generate_task_not_found(ctx: EvalContext) -> EvalOutcome:
    """任务控制：查询不存在任务应返回 404。"""
    headers, _ = _register(ctx, "notfound")
    response = ctx.client.get("/api/v1/generate/status/999999", headers=headers)
    ok = response.status_code == 404
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_generate_download_not_ready(ctx: EvalContext) -> EvalOutcome:
    """任务控制：下载未完成任务应返回 404。"""
    headers, user_id = _register(ctx, "notready")
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=user_id, prompt="未完成", status="generating_video", duration=5, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        response = ctx.client.get(f"/api/v1/generate/{task.id}/download", headers=headers)
        ok = response.status_code == 404
        return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")
    finally:
        db.close()


def _case_generate_cancel_completed(ctx: EvalContext) -> EvalOutcome:
    """任务控制：取消已完成任务应返回 400。"""
    headers, user_id = _register(ctx, "cancel_done")
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=user_id, prompt="已完成", status="completed", duration=5, aspect_ratio="16:9", video_url="/uploads/videos/x.mp4")
        db.add(task)
        db.commit()
        db.refresh(task)
        response = ctx.client.post(f"/api/v1/generate/{task.id}/cancel", headers=headers)
        ok = response.status_code == 400
        return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")
    finally:
        db.close()


def _case_generate_retry_non_failed(ctx: EvalContext) -> EvalOutcome:
    """任务控制：重试非失败任务应返回 400。"""
    headers, user_id = _register(ctx, "retry_bad")
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=user_id, prompt="进行中", status="generating_video", duration=5, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        response = ctx.client.post(f"/api/v1/generate/{task.id}/retry", headers=headers)
        ok = response.status_code == 400
        return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")
    finally:
        db.close()


def _case_generate_oversized_prompt(ctx: EvalContext) -> EvalOutcome:
    """参数边界：超长 prompt 应返回 422。"""
    headers, _ = _register(ctx, "longprompt")
    response = ctx.client.post(
        "/api/v1/generate/video",
        headers=headers,
        json={"prompt": "长" * 2001, "duration": 5, "aspect_ratio": "16:9"},
    )
    ok = response.status_code == 422
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_generate_status_invalid_id(ctx: EvalContext) -> EvalOutcome:
    """参数边界：非数字任务 ID 应返回 422。"""
    headers, _ = _register(ctx, "badid")
    response = ctx.client.get("/api/v1/generate/status/abc", headers=headers)
    ok = response.status_code == 422
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_generate_retry_missing_task(ctx: EvalContext) -> EvalOutcome:
    """任务控制：重试不存在任务应返回 404。"""
    headers, _ = _register(ctx, "retry_missing")
    response = ctx.client.post("/api/v1/generate/999999/retry", headers=headers)
    ok = response.status_code == 404
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_generate_cancel_missing_task(ctx: EvalContext) -> EvalOutcome:
    """任务控制：取消不存在任务应返回 404。"""
    headers, _ = _register(ctx, "cancel_missing")
    response = ctx.client.post("/api/v1/generate/999999/cancel", headers=headers)
    ok = response.status_code == 404
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_upload_invalid_type(ctx: EvalContext) -> EvalOutcome:
    """上传边界：不支持的文件类型应返回 400。"""
    headers, _ = _register(ctx, "upbadtype")
    response = ctx.client.post(
        "/api/v1/upload",
        headers=headers,
        files={"file": ("test.txt", b"hello", "text/plain")},
        data={"file_type": "image"},
    )
    ok = response.status_code == 400
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_upload_invalid_file_type_param(ctx: EvalContext) -> EvalOutcome:
    """上传边界：非法的 file_type 应返回 400。"""
    headers, _ = _register(ctx, "upbadparam")
    response = ctx.client.post(
        "/api/v1/upload?file_type=document",
        headers=headers,
        files={"file": ("test.png", b"fake", "image/png")},
    )
    ok = response.status_code == 400
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_upload_empty_file(ctx: EvalContext) -> EvalOutcome:
    """上传边界：空文件应能返回 URL（当前策略允许）。"""
    headers, _ = _register(ctx, "upempty")
    response = ctx.client.post(
        "/api/v1/upload",
        headers=headers,
        files={"file": ("empty.png", b"", "image/png")},
        data={"file_type": "image"},
    )
    ok = response.status_code == 200 and bool(response.json().get("file_url"))
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_history_pagination(ctx: EvalContext) -> EvalOutcome:
    """历史记录：分页参数应生效。"""
    headers, _ = _register(ctx, "histpage")
    for i in range(2):
        ctx.client.post(
            "/api/v1/generate/video",
            headers=headers,
            json={"prompt": f"分页任务 {i}", "duration": 5, "aspect_ratio": "16:9"},
        )
    response = ctx.client.get("/api/v1/history?page=1&page_size=1", headers=headers)
    ok = response.status_code == 200 and len(response.json()) == 1
    return _outcome(ok, 1.0 if ok else 0.0, {"数量": float(len(response.json()))}, f"返回数量：{len(response.json())}")


def _case_history_filter_status(ctx: EvalContext) -> EvalOutcome:
    """历史记录：按状态过滤应生效。"""
    headers, _ = _register(ctx, "histfilter")
    ctx.client.post(
        "/api/v1/generate/video",
        headers=headers,
        json={"prompt": "过滤任务", "duration": 5, "aspect_ratio": "16:9"},
    )
    response = ctx.client.get("/api/v1/history?status=completed", headers=headers)
    ok = response.status_code == 200 and all(item["status"] == "completed" for item in response.json())
    return _outcome(ok, 1.0 if ok else 0.0, {"数量": float(len(response.json()))}, f"返回数量：{len(response.json())}")


def _case_cost_task_detail(ctx: EvalContext) -> EvalOutcome:
    """成本：任务成本明细应返回调用记录。"""
    headers, _ = _register(ctx, "costdetail")
    submit = ctx.client.post(
        "/api/v1/generate/video",
        headers=headers,
        json={"prompt": "成本明细任务", "duration": 5, "aspect_ratio": "16:9"},
    )
    if submit.status_code != 200:
        return _outcome(False, 0.0, {}, f"提交失败：{submit.text}")
    task_id = submit.json()["id"]
    response = ctx.client.get(f"/api/v1/cost/task/{task_id}", headers=headers)
    ok = response.status_code == 200 and isinstance(response.json().get("items"), list)
    return _outcome(ok, 1.0 if ok else 0.0, {"明细数": float(len(response.json().get("items", [])))}, f"状态码：{response.status_code}")


def _case_cost_summary_after_task(ctx: EvalContext) -> EvalOutcome:
    """成本：提交任务后汇总应包含任务数。"""
    headers, _ = _register(ctx, "costafter")
    ctx.client.post(
        "/api/v1/generate/video",
        headers=headers,
        json={"prompt": "成本汇总任务", "duration": 5, "aspect_ratio": "16:9"},
    )
    response = ctx.client.get("/api/v1/cost/summary", headers=headers)
    ok = response.status_code == 200 and response.json().get("task_count", 0) >= 1
    return _outcome(ok, 1.0 if ok else 0.0, {"任务数": float(response.json().get("task_count", 0))}, f"状态码：{response.status_code}")


def _case_template_not_found(ctx: EvalContext) -> EvalOutcome:
    """模板：读取不存在模板应返回 404。"""
    headers, _ = _register(ctx, "tmpl404")
    response = ctx.client.get("/api/v1/templates/999999", headers=headers)
    ok = response.status_code == 404
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_template_create_missing_name(ctx: EvalContext) -> EvalOutcome:
    """模板：缺少名称应返回 422。"""
    headers, _ = _register(ctx, "tmplbad")
    response = ctx.client.post("/api/v1/templates", headers=headers, json={"config_json": {}})
    ok = response.status_code == 422
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_character_not_found(ctx: EvalContext) -> EvalOutcome:
    """角色：读取不存在角色应返回 404。"""
    headers, _ = _register(ctx, "char404")
    response = ctx.client.get("/api/v1/characters/999999", headers=headers)
    ok = response.status_code == 404
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_character_create_missing_name(ctx: EvalContext) -> EvalOutcome:
    """角色：缺少名称应返回 422。"""
    headers, _ = _register(ctx, "charbad")
    response = ctx.client.post("/api/v1/characters", headers=headers, json={"reference_image_url": "https://example.com/a.png"})
    ok = response.status_code == 422
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_character_multi_views(ctx: EvalContext) -> EvalOutcome:
    """角色：多视角参考图应能添加并读取。"""
    headers, _ = _register(ctx, "multiview")
    character = ctx.client.post(
        "/api/v1/characters",
        headers=headers,
        json={"name": "多视角角色", "reference_image_url": "https://example.com/front.png"},
    )
    if character.status_code != 200:
        return _outcome(False, 0.0, {}, f"创建角色失败：{character.text}")
    char_id = character.json()["id"]
    view = ctx.client.post(
        f"/api/v1/characters/{char_id}/multi-views",
        headers=headers,
        json={"view_name": "侧面", "image_url": "https://example.com/side.png"},
    )
    detail = ctx.client.get(f"/api/v1/characters/{char_id}", headers=headers)
    ok = view.status_code == 200 and len(detail.json().get("multi_views", [])) >= 1
    return _outcome(ok, 1.0 if ok else 0.0, {"视角数": float(len(detail.json().get("multi_views", [])))}, f"视角状态：{view.status_code}")


def _case_character_user_isolation(ctx: EvalContext) -> EvalOutcome:
    """权限：用户 B 不能读取用户 A 的角色。"""
    headers_a, _ = _register(ctx, "chariso_a")
    headers_b, _ = _register(ctx, "chariso_b")
    character = ctx.client.post(
        "/api/v1/characters",
        headers=headers_a,
        json={"name": "A的角色", "reference_image_url": "https://example.com/a.png"},
    )
    if character.status_code != 200:
        return _outcome(False, 0.0, {}, f"创建角色失败：{character.text}")
    char_id = character.json()["id"]
    response = ctx.client.get(f"/api/v1/characters/{char_id}", headers=headers_b)
    ok = response.status_code == 404
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_task_user_isolation(ctx: EvalContext) -> EvalOutcome:
    """权限：用户 B 不能下载用户 A 的任务视频。"""
    headers_a, _ = _register(ctx, "taskiso_a")
    headers_b, _ = _register(ctx, "taskiso_b")
    submit = ctx.client.post(
        "/api/v1/generate/video",
        headers=headers_a,
        json={"prompt": "A的任务", "duration": 5, "aspect_ratio": "16:9"},
    )
    if submit.status_code != 200:
        return _outcome(False, 0.0, {}, f"提交失败：{submit.text}")
    task_id = submit.json()["id"]
    response = ctx.client.get(f"/api/v1/generate/{task_id}/download", headers=headers_b)
    ok = response.status_code == 404
    return _outcome(ok, 1.0 if ok else 0.0, {"状态码": float(response.status_code)}, f"状态码：{response.status_code}")


def _case_concurrent_tasks(ctx: EvalContext) -> EvalOutcome:
    """并发：同一用户连续提交多个任务应全部完成且互不干扰。"""
    headers, _ = _register(ctx, "concurrent")
    ids = []
    for i in range(3):
        submit = ctx.client.post(
            "/api/v1/generate/video",
            headers=headers,
            json={"prompt": f"并发任务 {i}", "duration": 5, "aspect_ratio": "16:9"},
        )
        if submit.status_code != 200:
            return _outcome(False, 0.0, {}, f"第 {i} 个任务提交失败：{submit.text}")
        ids.append(submit.json()["id"])

    all_completed = True
    for task_id in ids:
        status = ctx.client.get(f"/api/v1/generate/status/{task_id}", headers=headers)
        if status.status_code != 200 or status.json().get("status") != "completed":
            all_completed = False
            break
    ok = all_completed and len(ids) == 3
    return _outcome(ok, 1.0 if ok else 0.0, {"任务数": float(len(ids))}, f"任务 IDs：{ids}")


def _case_batch_generate(ctx: EvalContext) -> EvalOutcome:
    """批量生成：应返回多个任务 ID。"""
    headers, _ = _register(ctx, "batch")
    response = ctx.client.post(
        "/api/v1/generate/batch",
        headers=headers,
        json={"prompt": "批量生成", "count": 3, "duration": 5, "aspect_ratio": "16:9", "quality": "standard"},
    )
    body = response.json() if response.status_code == 200 else {}
    checks = {
        "批量提交成功": response.status_code == 200,
        "数量正确": body.get("count") == 3,
        "任务 ID 列表完整": len(body.get("task_ids", [])) == 3,
        "批次 ID 存在": bool(body.get("batch_id")),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"任务数": float(body.get("count", 0))},
        details=f"状态码：{response.status_code}",
        trace=list(checks.items()),
    )


def _case_template_market(ctx: EvalContext) -> EvalOutcome:
    """模板市场：应能列出模板并复制。"""
    headers, _ = _register(ctx, "market")
    create = ctx.client.post(
        "/api/v1/templates",
        headers=headers,
        json={"name": "市场模板", "config_json": {"prompt": "测试"}},
    )
    if create.status_code != 200:
        return _outcome(False, 0.0, {}, f"创建模板失败：{create.text}")
    template_id = create.json()["id"]
    list_response = ctx.client.get("/api/v1/templates", headers=headers)
    fork = ctx.client.post(f"/api/v1/templates/{template_id}/fork", headers=headers)
    checks = {
        "创建成功": create.status_code == 200,
        "列表包含模板": list_response.status_code == 200 and any(item["id"] == template_id for item in list_response.json()),
        "复制成功": fork.status_code == 200 and fork.json()["id"] != template_id,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"模板ID": float(template_id)},
        details=f"创建：{create.status_code}，列表：{list_response.status_code}，复制：{fork.status_code}",
        trace=list(checks.items()),
    )


def _case_metrics(ctx: EvalContext) -> EvalOutcome:
    """监控指标：应返回基础运行数据。"""
    response = ctx.client.get("/api/v1/metrics")
    body = response.json() if response.status_code == 200 else {}
    checks = {
        "指标接口成功": response.status_code == 200,
        "状态正常": body.get("status") == "ok",
        "包含用户数": "users" in body,
        "包含任务统计": "tasks" in body,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"用户数": float(body.get("users", 0))},
        details=f"状态码：{response.status_code}",
        trace=list(checks.items()),
    )


def _case_previs_flow(ctx: EvalContext) -> EvalOutcome:
    """白模预演：模板、项目、更新与渲染应可用。"""
    headers, _ = _register(ctx, "previs")
    template = ctx.client.post(
        "/api/v1/previs/templates",
        headers=headers,
        json={"name": "评测白模模板", "description": "测试", "scene_json": {"objects": []}, "category": "人物"},
    )
    if template.status_code != 200:
        return _outcome(False, 0.0, {}, f"创建模板失败：{template.text}")
    template_id = template.json()["id"]

    project = ctx.client.post(
        "/api/v1/previs/projects",
        headers=headers,
        json={
            "title": "评测白模项目",
            "template_id": template_id,
            "mode": "manual",
            "scene_json": {"objects": [{"type": "box"}]},
            "camera_script": {"shots": []},
            "mapping_rules": {"blue": "女主"},
        },
    )
    if project.status_code != 200:
        return _outcome(False, 0.0, {}, f"创建项目失败：{project.text}")
    project_id = project.json()["id"]

    update = ctx.client.put(
        f"/api/v1/previs/projects/{project_id}",
        headers=headers,
        json={"title": "改名后的白模项目"},
    )
    render = ctx.client.post(f"/api/v1/previs/projects/{project_id}/render", headers=headers)
    detail = ctx.client.get(f"/api/v1/previs/projects/{project_id}", headers=headers)

    checks = {
        "模板创建成功": template.status_code == 200,
        "项目创建成功": project.status_code == 200,
        "项目更新成功": update.status_code == 200 and update.json()["title"] == "改名后的白模项目",
        "渲染成功": render.status_code == 200 and render.json()["status"] == "ready",
        "详情可查": detail.status_code == 200 and detail.json()["id"] == project_id,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"项目ID": float(project_id)},
        details=f"模板：{template.status_code}，项目：{project.status_code}，渲染：{render.status_code}",
        trace=list(checks.items()),
    )


def build_system_cases() -> list[EvalCase]:
    """构建系统级评测用例集。"""
    return [
        EvalCase(
            id="system.auth",
            name="认证注册与登录",
            category="system",
            target="api_auth",
            description="验证注册、登录与令牌返回。",
            fn=_case_auth,
        ),
        EvalCase(
            id="system.generate_flow",
            name="视频生成端到端链路",
            category="system",
            target="api_generate",
            description="验证提交任务、状态查询、下载成片的完整链路。",
            fn=_case_generate_flow,
        ),
        EvalCase(
            id="system.validation",
            name="参数校验与错误处理",
            category="system",
            target="api_error_handling",
            description="验证非法参数返回统一的中文错误结构。",
            fn=_case_validation,
        ),
        EvalCase(
            id="system.character_flow",
            name="角色库与角色一致性流程",
            category="system",
            target="api_character",
            description="验证角色创建及携带角色 ID 提交任务。",
            fn=_case_character_flow,
        ),
        EvalCase(
            id="system.history",
            name="历史记录查询",
            category="system",
            target="api_history",
            description="验证历史任务列表接口。",
            fn=_case_history,
        ),
        EvalCase(
            id="system.cost_summary",
            name="成本汇总查询",
            category="system",
            target="api_cost",
            description="验证成本汇总接口。",
            fn=_case_cost_summary,
        ),
        EvalCase(
            id="system.cancel_retry",
            name="任务取消与重试",
            category="system",
            target="api_task_control",
            description="验证取消 pending 任务与重试 failed 任务。",
            fn=_case_cancel_retry,
        ),
        EvalCase(
            id="system.template",
            name="模板创建与读取",
            category="system",
            target="api_template",
            description="验证模板接口的创建与详情读取。",
            fn=_case_template,
        ),
        EvalCase(
            id="system.upload",
            name="文件上传",
            category="system",
            target="api_upload",
            description="验证文件上传并返回可访问 URL。",
            fn=_case_upload,
        ),
        EvalCase(id="system.auth_wrong_password", name="认证-错误密码", category="system", target="api_auth", description="错误密码应返回 401。", fn=_case_auth_wrong_password),
        EvalCase(id="system.auth_duplicate_register", name="认证-重复注册", category="system", target="api_auth", description="重复用户名应返回 400。", fn=_case_auth_duplicate_register),
        EvalCase(id="system.auth_invalid_token", name="认证-无效 Token", category="system", target="api_auth", description="无效 Token 应返回 401。", fn=_case_auth_invalid_token),
        EvalCase(id="system.auth_missing_auth", name="认证-缺少认证", category="system", target="api_auth", description="未携带 Token 应返回 401。", fn=_case_auth_missing_auth),
        EvalCase(id="system.auth_missing_fields", name="认证-缺少字段", category="system", target="api_auth", description="缺少必填字段应返回 422。", fn=_case_auth_missing_fields),
        EvalCase(id="system.generate_task_not_found", name="任务-查询不存在", category="system", target="api_generate", description="查询不存在任务应返回 404。", fn=_case_generate_task_not_found),
        EvalCase(id="system.generate_download_not_ready", name="任务-下载未完成", category="system", target="api_generate", description="未完成任务下载应返回 404。", fn=_case_generate_download_not_ready),
        EvalCase(id="system.generate_cancel_completed", name="任务-取消已完成", category="system", target="api_task_control", description="取消已完成任务应返回 400。", fn=_case_generate_cancel_completed),
        EvalCase(id="system.generate_retry_non_failed", name="任务-重试非失败", category="system", target="api_task_control", description="重试非失败任务应返回 400。", fn=_case_generate_retry_non_failed),
        EvalCase(id="system.generate_oversized_prompt", name="参数-超长 Prompt", category="system", target="api_error_handling", description="超长 Prompt 应返回 422。", fn=_case_generate_oversized_prompt),
        EvalCase(id="system.generate_status_invalid_id", name="参数-非法任务 ID", category="system", target="api_error_handling", description="非数字任务 ID 应返回 422。", fn=_case_generate_status_invalid_id),
        EvalCase(id="system.generate_retry_missing_task", name="任务-重试不存在", category="system", target="api_task_control", description="重试不存在任务应返回 404。", fn=_case_generate_retry_missing_task),
        EvalCase(id="system.generate_cancel_missing_task", name="任务-取消不存在", category="system", target="api_task_control", description="取消不存在任务应返回 404。", fn=_case_generate_cancel_missing_task),
        EvalCase(id="system.upload_invalid_type", name="上传-非法类型", category="system", target="api_upload", description="不支持的文件类型应返回 400。", fn=_case_upload_invalid_type),
        EvalCase(id="system.upload_invalid_file_type_param", name="上传-非法 file_type", category="system", target="api_upload", description="非法的 file_type 应返回 400。", fn=_case_upload_invalid_file_type_param),
        EvalCase(id="system.upload_empty_file", name="上传-空文件", category="system", target="api_upload", description="空文件应能返回 URL。", fn=_case_upload_empty_file),
        EvalCase(id="system.history_pagination", name="历史-分页", category="system", target="api_history", description="分页参数应生效。", fn=_case_history_pagination),
        EvalCase(id="system.history_filter_status", name="历史-状态过滤", category="system", target="api_history", description="按状态过滤应生效。", fn=_case_history_filter_status),
        EvalCase(id="system.cost_task_detail", name="成本-任务明细", category="system", target="api_cost", description="任务成本明细应返回调用记录。", fn=_case_cost_task_detail),
        EvalCase(id="system.cost_summary_after_task", name="成本-提交后汇总", category="system", target="api_cost", description="提交任务后汇总应包含任务数。", fn=_case_cost_summary_after_task),
        EvalCase(id="system.template_not_found", name="模板-不存在", category="system", target="api_template", description="读取不存在模板应返回 404。", fn=_case_template_not_found),
        EvalCase(id="system.template_create_missing_name", name="模板-缺少名称", category="system", target="api_template", description="缺少名称应返回 422。", fn=_case_template_create_missing_name),
        EvalCase(id="system.character_not_found", name="角色-不存在", category="system", target="api_character", description="读取不存在角色应返回 404。", fn=_case_character_not_found),
        EvalCase(id="system.character_create_missing_name", name="角色-缺少名称", category="system", target="api_character", description="缺少名称应返回 422。", fn=_case_character_create_missing_name),
        EvalCase(id="system.character_multi_views", name="角色-多视角", category="system", target="api_character", description="多视角参考图应能添加并读取。", fn=_case_character_multi_views),
        EvalCase(id="system.character_user_isolation", name="权限-角色隔离", category="system", target="api_character", description="用户 B 不能读取用户 A 的角色。", fn=_case_character_user_isolation),
        EvalCase(id="system.task_user_isolation", name="权限-任务隔离", category="system", target="api_generate", description="用户 B 不能下载用户 A 的任务视频。", fn=_case_task_user_isolation),
        EvalCase(id="system.concurrent_tasks", name="并发-多任务", category="system", target="api_generate", description="同一用户连续提交多个任务应全部完成。", fn=_case_concurrent_tasks),
        EvalCase(id="system.batch_generate", name="批量生成", category="system", target="api_generate", description="批量提交应返回多个任务 ID。", fn=_case_batch_generate),
        EvalCase(id="system.template_market", name="模板市场", category="system", target="api_template", description="模板市场应能列出并复制模板。", fn=_case_template_market),
        EvalCase(id="system.metrics", name="监控指标", category="system", target="api_monitor", description="监控指标接口应返回基础运行数据。", fn=_case_metrics),
        EvalCase(id="system.previs_flow", name="白模预演流程", category="system", target="api_previs", description="白模模板、项目、更新与渲染应可用。", fn=_case_previs_flow),
    ]
