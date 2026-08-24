"""Agent 能力评测用例。

覆盖项目中的 PromptAgent、ImageAgent、VideoGenAgent、AudioAgent、
SubtitleAgent、PostProcessAgent、QualityCheckAgent 以及调度编排 Agent。
"""

import shutil
import time
import uuid
from pathlib import Path
from unittest import mock

from app.models import VideoSegment, VideoTask
from app.orchestration import simple as simple_module
from app.orchestration.langgraph_orchestrator import LangGraphOrchestrator
from app.orchestration.simple import SimpleTaskOrchestrator
from app.providers.base import (
    ImageGenerationRequest,
    LLMRequest,
    VideoGenerationRequest,
    VideoTaskHandle,
    VideoTaskStatus,
)
from app.providers.registry import registry
from app.services.audio_service import generate_bgm_audio, generate_tts_audio
from app.services.quality_service import evaluate_video
from app.services.subtitle_service import generate_subtitle
from app.services.video_stitcher import stitch_videos
from eval_harness.models import EvalCase, EvalContext, EvalOutcome
from eval_harness.trajectory import (
    Trajectory,
    TrajectoryStep,
    format_trajectory,
    trajectory_similarity,
    validate_tool_use,
)


def _outcome(
    ok: bool,
    score: float,
    metrics: dict,
    details: str,
    trace: list[str] | None = None,
    trajectory: list[dict] | None = None,
) -> EvalOutcome:
    """构造评测结果。"""
    return EvalOutcome(
        status="pass" if ok and score >= 0.999 else "fail",
        score=score,
        metrics=metrics,
        details=details,
        trace=trace or [],
        trajectory=trajectory,
    )


def _case_prompt_agent(ctx: EvalContext) -> EvalOutcome:
    """PromptAgent：应能优化提示词并保留核心语义。"""
    provider = registry.get_llm_provider()
    start = time.perf_counter()
    result = provider.complete(
        LLMRequest(
            system_prompt="你是一个短视频导演。",
            user_prompt="一只猫在夕阳下奔跑",
        )
    )
    duration_ms = (time.perf_counter() - start) * 1000

    checks = {
        "非空输出": bool(result.text),
        "保留原文关键词": ("猫" in result.text) and ("夕阳" in result.text),
        "返回 Provider": bool(result.provider),
        "成本非负": result.cost >= 0,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={
            "输出长度": float(len(result.text or "")),
            "耗时_ms": duration_ms,
            "成本": float(result.cost),
        },
        details=f"输出前 80 字：{result.text[:80]}",
        trace=list(checks.items()),
    )


def _case_image_agent(ctx: EvalContext) -> EvalOutcome:
    """ImageAgent：应能生成首帧图片 URL。"""
    provider = registry.get_image_provider()
    start = time.perf_counter()
    result = provider.generate_image(
        ImageGenerationRequest(prompt="一只猫在夕阳下奔跑", aspect_ratio="16:9")
    )
    duration_ms = (time.perf_counter() - start) * 1000

    checks = {
        "图片 URL 非空": bool(result.image_url),
        "URL 格式合法": result.image_url.startswith(("http://", "https://", "/uploads/")),
        "返回 Provider": bool(result.provider),
        "成本非负": result.cost >= 0,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"耗时_ms": duration_ms, "成本": float(result.cost)},
        details=f"图片 URL：{result.image_url}",
        trace=list(checks.items()),
    )


def _case_video_agent(ctx: EvalContext) -> EvalOutcome:
    """VideoGenAgent：应能提交视频任务并最终返回成功状态。"""
    provider = registry.get_video_provider()
    handle = provider.submit_video_task(
        VideoGenerationRequest(prompt="一只猫在夕阳下奔跑", duration=5, aspect_ratio="16:9")
    )

    checks = {
        "任务句柄非空": bool(handle.external_task_id),
        "Provider 正确": handle.provider == provider.name,
    }
    if not all(checks.values()):
        return _outcome(False, 0.0, {}, "提交阶段失败", list(checks.items()))

    start = time.perf_counter()
    status = None
    trace = []
    for _ in range(6):
        status = provider.query_video_task(handle)
        trace.append(f"state={status.state}")
        if status.state in {"succeeded", "failed"}:
            break
        time.sleep(1)
    duration_ms = (time.perf_counter() - start) * 1000

    checks["最终成功"] = status is not None and status.state == "succeeded"
    checks["视频 URL 非空"] = bool(status and status.video_url)
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"耗时_ms": duration_ms},
        details=f"最终状态：{status.state if status else 'unknown'}，URL：{status.video_url if status else ''}",
        trace=trace,
    )


def _case_audio_agent(ctx: EvalContext) -> EvalOutcome:
    """AudioAgent：应能生成 TTS 音频记录。"""
    db = ctx.db_session()
    try:
        start = time.perf_counter()
        track = generate_tts_audio(
            db=db,
            user_id=1,
            task_id=None,
            text="这是一段测试配音",
            voice_id="female_01",
        )
        duration_ms = (time.perf_counter() - start) * 1000
        checks = {
            "音频记录已创建": track.id is not None,
            "音频 URL 非空": bool(track.source_url),
            "文本内容保留": track.text_content == "这是一段测试配音",
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"耗时_ms": duration_ms},
            details=f"音频 URL：{track.source_url}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


def _case_subtitle_agent(ctx: EvalContext) -> EvalOutcome:
    """SubtitleAgent：应能生成 SRT 字幕文件。"""
    start = time.perf_counter()
    url, content = generate_subtitle("海边日出，浪花拍岸")
    duration_ms = (time.perf_counter() - start) * 1000
    checks = {
        "字幕 URL 非空": bool(url),
        "SRT 后缀正确": url.endswith(".srt"),
        "内容包含原文": "海边日出，浪花拍岸" in content,
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"耗时_ms": duration_ms, "内容长度": float(len(content))},
        details=f"字幕 URL：{url}",
        trace=list(checks.items()),
    )


def _case_post_process_agent(ctx: EvalContext) -> EvalOutcome:
    """PostProcessAgent：应能拼接多个视频片段。"""
    mock_clip = Path("app/providers/assets/mock_clip.mp4")
    if not mock_clip.exists():
        return _outcome(False, 0.0, {}, "缺少 mock_clip.mp4")

    temp_dir = Path(".eval_tmp") / f"stitch-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    first = temp_dir / "first.mp4"
    second = temp_dir / "second.mp4"
    output = temp_dir / "output.mp4"
    first.write_bytes(mock_clip.read_bytes())
    second.write_bytes(mock_clip.read_bytes())

    start = time.perf_counter()
    try:
        result_path = stitch_videos([first, second], output)
        duration_ms = (time.perf_counter() - start) * 1000
        checks = {
            "输出文件存在": result_path.exists(),
            "输出非空": result_path.stat().st_size > 0,
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"耗时_ms": duration_ms, "输出大小": float(result_path.stat().st_size)},
            details=f"输出路径：{result_path}",
            trace=list(checks.items()),
        )
    except Exception as exc:  # noqa: BLE001
        return _outcome(False, 0.0, {}, f"拼接失败：{exc}", [str(exc)])
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _case_quality_agent(ctx: EvalContext) -> EvalOutcome:
    """QualityCheckAgent：应能给出 0~10 的质量分。"""
    report = evaluate_video("https://example.com/video.mp4", threshold=7.5)
    checks = {
        "分数在 0~10": 0.0 <= report.score <= 10.0,
        "有通过结论": isinstance(report.passed, bool),
        "有原因说明": bool(report.reason),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"质量分": report.score},
        details=f"质量分：{report.score}，结论：{report.passed}，原因：{report.reason}",
        trace=list(checks.items()),
    )


def _case_simple_orchestrator(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（Simple）：应能完成完整视频生成流水线。"""
    db = ctx.db_session()
    try:
        task = VideoTask(
            user_id=1,
            prompt="一只猫在夕阳下奔跑",
            status="pending",
            duration=5,
            aspect_ratio="16:9",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        start = time.perf_counter()
        SimpleTaskOrchestrator().run(task_id)
        duration_ms = (time.perf_counter() - start) * 1000

        db.refresh(task)
        checks = {
            "任务完成": task.status == "completed",
            "视频 URL 非空": bool(task.video_url),
            "字幕 URL 非空": bool(task.subtitle_url),
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"耗时_ms": duration_ms},
            details=f"任务状态：{task.status}，视频：{task.video_url}，字幕：{task.subtitle_url}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


def _case_langgraph_orchestrator(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（LangGraph）：应能完成状态图流水线。"""
    db = ctx.db_session()
    try:
        task = VideoTask(
            user_id=1,
            prompt="海边日出，浪花拍岸",
            status="pending",
            duration=5,
            aspect_ratio="16:9",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        start = time.perf_counter()
        LangGraphOrchestrator().run(task_id)
        duration_ms = (time.perf_counter() - start) * 1000

        db.refresh(task)
        checks = {
            "任务完成": task.status == "completed",
            "视频 URL 非空": bool(task.video_url),
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"耗时_ms": duration_ms},
            details=f"任务状态：{task.status}，视频：{task.video_url}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


def _case_audio_bgm(ctx: EvalContext) -> EvalOutcome:
    """AudioAgent BGM：应能生成 BGM 音频记录。"""
    db = ctx.db_session()
    try:
        start = time.perf_counter()
        track = generate_bgm_audio(db=db, user_id=1, task_id=None, bgm_id=None)
        duration_ms = (time.perf_counter() - start) * 1000
        checks = {
            "BGM 记录已创建": track.id is not None,
            "BGM URL 非空": bool(track.source_url),
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"耗时_ms": duration_ms},
            details=f"BGM URL：{track.source_url}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


def _case_quality_no_video(ctx: EvalContext) -> EvalOutcome:
    """QualityCheckAgent：无视频时应判定为未通过。"""
    report = evaluate_video(None, threshold=7.5)
    checks = {
        "分数为 0": report.score == 0.0,
        "未通过": report.passed is False,
        "有原因": bool(report.reason),
    }
    score = sum(checks.values()) / len(checks)
    return _outcome(
        ok=score == 1.0,
        score=score,
        metrics={"质量分": report.score},
        details=f"质量分：{report.score}，结论：{report.passed}",
        trace=list(checks.items()),
    )


def _case_post_process_single(ctx: EvalContext) -> EvalOutcome:
    """PostProcessAgent：单片段拼接应直接复制成功。"""
    mock_clip = Path("app/providers/assets/mock_clip.mp4")
    if not mock_clip.exists():
        return _outcome(False, 0.0, {}, "缺少 mock_clip.mp4")
    temp_dir = Path(".eval_tmp") / f"stitch-single-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    source = temp_dir / "source.mp4"
    output = temp_dir / "output.mp4"
    source.write_bytes(mock_clip.read_bytes())
    try:
        start = time.perf_counter()
        result = stitch_videos([source], output)
        duration_ms = (time.perf_counter() - start) * 1000
        ok = result.exists() and result.stat().st_size > 0
        return _outcome(
            ok=ok,
            score=1.0 if ok else 0.0,
            metrics={"耗时_ms": duration_ms, "输出大小": float(result.stat().st_size)},
            details=f"输出：{result}",
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _case_simple_multi_segment(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（Simple）：多片段任务应生成多个片段并完成。"""
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=1, prompt="多片段测试", status="pending", duration=10, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        start = time.perf_counter()
        SimpleTaskOrchestrator().run(task.id)
        duration_ms = (time.perf_counter() - start) * 1000
        segments = db.query(VideoSegment).filter(VideoSegment.task_id == task.id).all()
        db.refresh(task)
        checks = {
            "任务完成": task.status == "completed",
            "片段数量为 2": len(segments) == 2,
            "视频 URL 非空": bool(task.video_url),
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"耗时_ms": duration_ms, "片段数": float(len(segments))},
            details=f"片段数：{len(segments)}，视频：{task.video_url}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


def _case_langgraph_multi_segment(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（LangGraph）：多片段任务应生成多个片段并完成。"""
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=1, prompt="多片段 LangGraph", status="pending", duration=10, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        start = time.perf_counter()
        LangGraphOrchestrator().run(task.id)
        duration_ms = (time.perf_counter() - start) * 1000
        segments = db.query(VideoSegment).filter(VideoSegment.task_id == task.id).all()
        db.refresh(task)
        checks = {
            "任务完成": task.status == "completed",
            "片段数量为 2": len(segments) == 2,
            "视频 URL 非空": bool(task.video_url),
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={"耗时_ms": duration_ms, "片段数": float(len(segments))},
            details=f"片段数：{len(segments)}，视频：{task.video_url}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


class _FailingTTSProvider:
    """模拟 TTS 失败的 Provider。"""

    name = "mock_tts"

    def synthesize(self, request):
        raise RuntimeError("模拟 TTS 失败")


class _FailingVideoProvider:
    """模拟真实视频生成失败的 Provider。"""

    name = "siliconflow"

    def submit_video_task(self, request):
        return VideoTaskHandle(provider=self.name, external_task_id="fail")

    def query_video_task(self, handle):
        return VideoTaskStatus(state="failed", error_code="API_SERVER_ERROR", error_message="模拟视频失败")


class _TrajectoryLLMProvider:
    """带轨迹录制的 LLM Provider 包装器。"""

    def __init__(self, ctx: EvalContext, task_id: str, original) -> None:
        self.ctx = ctx
        self.task_id = task_id
        self.original = original

    @property
    def name(self) -> str:
        return self.original.name

    def complete(self, request: LLMRequest):
        start = time.perf_counter()
        result = self.original.complete(request)
        latency_ms = (time.perf_counter() - start) * 1000
        self.ctx.record_trajectory(
            self.task_id,
            TrajectoryStep(
                agent="llm",
                action="complete",
                params={"system_prompt": request.system_prompt[:50]},
                result=result.text[:80],
                ok=True,
                cost=float(result.cost),
                latency_ms=latency_ms,
            ),
        )
        return result


class _TrajectoryImageProvider:
    """带轨迹录制的文生图 Provider 包装器。"""

    def __init__(self, ctx: EvalContext, task_id: str, original) -> None:
        self.ctx = ctx
        self.task_id = task_id
        self.original = original

    @property
    def name(self) -> str:
        return self.original.name

    def generate_image(self, request: ImageGenerationRequest):
        start = time.perf_counter()
        result = self.original.generate_image(request)
        latency_ms = (time.perf_counter() - start) * 1000
        self.ctx.record_trajectory(
            self.task_id,
            TrajectoryStep(
                agent="image",
                action="generate_image",
                params={"prompt": request.prompt[:50], "reference_count": len(request.reference_image_urls)},
                result=result.image_url[:80],
                ok=True,
                cost=float(result.cost),
                latency_ms=latency_ms,
            ),
        )
        return result


class _TrajectoryVideoProvider:
    """带轨迹录制的视频 Provider 包装器。"""

    def __init__(self, ctx: EvalContext, task_id: str, original) -> None:
        self.ctx = ctx
        self.task_id = task_id
        self.original = original

    @property
    def name(self) -> str:
        return self.original.name

    def submit_video_task(self, request: VideoGenerationRequest):
        start = time.perf_counter()
        handle = self.original.submit_video_task(request)
        latency_ms = (time.perf_counter() - start) * 1000
        self.ctx.record_trajectory(
            self.task_id,
            TrajectoryStep(
                agent="video",
                action="submit_video_task",
                params={
                    "duration": request.duration,
                    "aspect_ratio": request.aspect_ratio,
                    "has_first_frame": bool(request.first_frame_url),
                    "reference_count": len(request.reference_image_urls),
                },
                result=f"handle={handle.external_task_id}",
                ok=True,
                latency_ms=latency_ms,
            ),
        )
        return handle

    def query_video_task(self, handle: VideoTaskHandle):
        start = time.perf_counter()
        status = self.original.query_video_task(handle)
        latency_ms = (time.perf_counter() - start) * 1000
        self.ctx.record_trajectory(
            self.task_id,
            TrajectoryStep(
                agent="video",
                action="query_video_task",
                params={"external_task_id": handle.external_task_id},
                result=f"state={status.state}",
                ok=status.state in {"succeeded", "processing"},
                latency_ms=latency_ms,
            ),
        )
        return status


class _TrajectoryTTSProvider:
    """带轨迹录制的 TTS Provider 包装器。"""

    def __init__(self, ctx: EvalContext, task_id: str, original) -> None:
        self.ctx = ctx
        self.task_id = task_id
        self.original = original

    @property
    def name(self) -> str:
        return self.original.name

    def synthesize(self, request):
        start = time.perf_counter()
        result = self.original.synthesize(request)
        latency_ms = (time.perf_counter() - start) * 1000
        self.ctx.record_trajectory(
            self.task_id,
            TrajectoryStep(
                agent="tts",
                action="synthesize",
                params={"voice_id": request.voice_id},
                result=result.audio_url[:80],
                ok=True,
                cost=float(result.cost),
                latency_ms=latency_ms,
            ),
        )
        return result


def _case_simple_audio_failure_nonblocking(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（Simple）：TTS 失败不应阻塞主流程完成。"""
    original = registry.tts_providers
    registry.tts_providers = {"mock": _FailingTTSProvider()}
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=1, prompt="TTS 失败测试", status="pending", duration=5, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        SimpleTaskOrchestrator().run(task.id)
        db.refresh(task)
        checks = {
            "任务仍完成": task.status == "completed",
            "音频为空": task.audio_url is None,
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={},
            details=f"任务状态：{task.status}，音频：{task.audio_url}",
            trace=list(checks.items()),
        )
    finally:
        registry.tts_providers = original
        db.close()


def _case_simple_subtitle_failure_nonblocking(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（Simple）：字幕失败不应阻塞主流程完成。"""
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=1, prompt="字幕失败测试", status="pending", duration=5, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        with mock.patch.object(simple_module, "generate_subtitle", side_effect=RuntimeError("模拟字幕失败")):
            SimpleTaskOrchestrator().run(task.id)
        db.refresh(task)
        checks = {
            "任务仍完成": task.status == "completed",
            "字幕为空": task.subtitle_url is None,
        }
        score = sum(checks.values()) / len(checks)
        return _outcome(
            ok=score == 1.0,
            score=score,
            metrics={},
            details=f"任务状态：{task.status}，字幕：{task.subtitle_url}",
            trace=list(checks.items()),
        )
    finally:
        db.close()


def _case_simple_video_failure_marks_failed(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（Simple）：真实视频失败应标记任务失败而不是占位完成。"""
    original = registry.video_providers
    registry.video_providers = {"siliconflow": _FailingVideoProvider()}
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=1, prompt="视频失败测试", status="pending", duration=5, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        try:
            SimpleTaskOrchestrator().run(task.id)
        except RuntimeError:
            pass
        db.refresh(task)
        ok = task.status == "failed"
        return _outcome(
            ok=ok,
            score=1.0 if ok else 0.0,
            metrics={},
            details=f"任务状态：{task.status}",
            trace=[f"status={task.status}"],
        )
    finally:
        registry.video_providers = original
        db.close()


def _case_langgraph_video_failure_marks_failed(ctx: EvalContext) -> EvalOutcome:
    """调度 Agent（LangGraph）：真实视频失败应标记任务失败。"""
    original = registry.video_providers
    registry.video_providers = {"siliconflow": _FailingVideoProvider()}
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=1, prompt="LangGraph 视频失败测试", status="pending", duration=5, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        try:
            LangGraphOrchestrator().run(task.id)
        except RuntimeError:
            pass
        db.refresh(task)
        ok = task.status == "failed"
        return _outcome(
            ok=ok,
            score=1.0 if ok else 0.0,
            metrics={},
            details=f"任务状态：{task.status}",
            trace=[f"status={task.status}"],
        )
    finally:
        registry.video_providers = original
        db.close()


def _case_trajectory_golden(ctx: EvalContext) -> EvalOutcome:
    """轨迹评测：完整流水线的实际轨迹应与黄金轨迹匹配。"""
    original_llm = registry.llm_providers
    original_image = registry.image_providers
    original_video = registry.video_providers
    original_tts = registry.tts_providers
    db = ctx.db_session()
    try:
        task = VideoTask(user_id=1, prompt="一只猫在夕阳下奔跑", status="pending", duration=5, aspect_ratio="16:9")
        db.add(task)
        db.commit()
        db.refresh(task)
        run_id = str(task.id)

        registry.llm_providers = {"mock": _TrajectoryLLMProvider(ctx, run_id, original_llm["mock"])}
        registry.image_providers = {"mock": _TrajectoryImageProvider(ctx, run_id, original_image["mock"])}
        registry.video_providers = {"mock": _TrajectoryVideoProvider(ctx, run_id, original_video["mock"])}
        registry.tts_providers = {"mock": _TrajectoryTTSProvider(ctx, run_id, original_tts["mock"])}

        SimpleTaskOrchestrator().run(task.id)

        trajectory = next((item for item in ctx.trajectories if item.task_id == run_id), None)
        if trajectory is None:
            return _outcome(False, 0.0, {}, "未捕获到任何轨迹", ["trajectory is None"])

        golden = Trajectory(
            task_id="golden",
            steps=[
                TrajectoryStep(agent="llm", action="complete"),
                TrajectoryStep(agent="image", action="generate_image"),
                TrajectoryStep(agent="video", action="submit_video_task"),
                TrajectoryStep(agent="tts", action="synthesize"),
            ],
        )
        similarity = trajectory_similarity(trajectory, golden)
        tool_ok, tool_score, tool_issues = validate_tool_use(
            trajectory,
            [
                {"agent": "llm", "action": "complete", "params_contains": {"system_prompt": "你是一个短视频导演。"}},
                {"agent": "image", "action": "generate_image", "params_contains": {"reference_count": 0}},
                {"agent": "video", "action": "submit_video_task", "params_contains": {"duration": 5, "has_first_frame": True}},
                {"agent": "tts", "action": "synthesize", "params_contains": {"voice_id": "female_01"}},
            ],
        )
        ok = similarity >= 0.8 and tool_ok
        return _outcome(
            ok=ok,
            score=similarity if ok else similarity * 0.5,
            metrics={"trajectory_similarity": similarity, "tool_use_score": tool_score, "trajectory_steps": float(len(trajectory.steps))},
            details=f"轨迹相似度：{similarity:.2f}，工具调用得分：{tool_score:.2f}",
            trace=format_trajectory(trajectory),
            trajectory=trajectory.to_dict()["steps"],
        )
    finally:
        registry.llm_providers = original_llm
        registry.image_providers = original_image
        registry.video_providers = original_video
        registry.tts_providers = original_tts
        db.close()


def _case_tool_use_correctness(ctx: EvalContext) -> EvalOutcome:
    """工具调用正确性：参考图应传给文生图，首帧与参考图应传给视频生成。"""
    original_llm = registry.llm_providers
    original_image = registry.image_providers
    original_video = registry.video_providers
    original_tts = registry.tts_providers
    db = ctx.db_session()
    try:
        task = VideoTask(
            user_id=1,
            prompt="带参考图的角色任务",
            status="pending",
            duration=5,
            aspect_ratio="16:9",
            reference_image_urls=["https://example.com/ref.png"],
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        run_id = str(task.id)

        registry.llm_providers = {"mock": _TrajectoryLLMProvider(ctx, run_id, original_llm["mock"])}
        registry.image_providers = {"mock": _TrajectoryImageProvider(ctx, run_id, original_image["mock"])}
        registry.video_providers = {"mock": _TrajectoryVideoProvider(ctx, run_id, original_video["mock"])}
        registry.tts_providers = {"mock": _TrajectoryTTSProvider(ctx, run_id, original_tts["mock"])}

        SimpleTaskOrchestrator().run(task.id)

        trajectory = next((item for item in ctx.trajectories if item.task_id == run_id), None)
        if trajectory is None:
            return _outcome(False, 0.0, {}, "未捕获到任何轨迹", ["trajectory is None"])

        ok, score, issues = validate_tool_use(
            trajectory,
            [
                {"agent": "image", "action": "generate_image", "params_contains": {"reference_count": 1}},
                {"agent": "video", "action": "submit_video_task", "params_contains": {"has_first_frame": True, "reference_count": 1}},
            ],
        )
        return _outcome(
            ok=ok,
            score=score,
            metrics={"tool_use_score": score, "trajectory_steps": float(len(trajectory.steps))},
            details=f"工具调用得分：{score:.2f}",
            trace=issues or format_trajectory(trajectory),
            trajectory=trajectory.to_dict()["steps"],
        )
    finally:
        registry.llm_providers = original_llm
        registry.image_providers = original_image
        registry.video_providers = original_video
        registry.tts_providers = original_tts
        db.close()


def build_agent_cases() -> list[EvalCase]:
    """构建 Agent 能力评测用例集。"""
    return [
        EvalCase(
            id="agent.prompt",
            name="PromptAgent 提示词优化",
            category="agent",
            target="prompt_agent",
            description="验证 LLM Provider 能返回优化后的提示词并保留核心语义。",
            fn=_case_prompt_agent,
            latency_budget_ms=5000,
            cost_budget=0.1,
        ),
        EvalCase(
            id="agent.image",
            name="ImageAgent 首帧生成",
            category="agent",
            target="image_agent",
            description="验证文生图 Provider 能返回合法图片 URL。",
            fn=_case_image_agent,
        ),
        EvalCase(
            id="agent.video",
            name="VideoGenAgent 视频生成",
            category="agent",
            target="video_gen_agent",
            description="验证视频 Provider 能提交任务并轮询到成功状态。",
            fn=_case_video_agent,
            latency_budget_ms=15000,
            cost_budget=0.1,
        ),
        EvalCase(
            id="agent.audio",
            name="AudioAgent TTS 配音",
            category="agent",
            target="audio_agent",
            description="验证 TTS 服务能生成音频记录与 URL。",
            fn=_case_audio_agent,
        ),
        EvalCase(
            id="agent.subtitle",
            name="SubtitleAgent 字幕生成",
            category="agent",
            target="subtitle_agent",
            description="验证字幕服务能生成 SRT 文件并保留原文。",
            fn=_case_subtitle_agent,
        ),
        EvalCase(
            id="agent.post_process",
            name="PostProcessAgent 视频拼接",
            category="agent",
            target="post_process_agent",
            description="验证 FFmpeg/MoviePy 拼接能力。",
            fn=_case_post_process_agent,
        ),
        EvalCase(
            id="agent.quality",
            name="QualityCheckAgent 质量评估",
            category="agent",
            target="quality_check_agent",
            description="验证质量评估能给出 0~10 分与通过结论。",
            fn=_case_quality_agent,
        ),
        EvalCase(
            id="agent.orchestrator.simple",
            name="调度 Agent（Simple）完整流水线",
            category="agent",
            target="orchestrator",
            description="验证 SimpleTaskOrchestrator 能端到端完成视频生成。",
            fn=_case_simple_orchestrator,
            latency_budget_ms=10000,
            cost_budget=0.1,
        ),
        EvalCase(
            id="agent.orchestrator.langgraph",
            name="调度 Agent（LangGraph）完整流水线",
            category="agent",
            target="orchestrator",
            description="验证 LangGraphOrchestrator 能端到端完成视频生成。",
            fn=_case_langgraph_orchestrator,
        ),
        EvalCase(id="agent.audio_bgm", name="AudioAgent BGM 生成", category="agent", target="audio_agent", description="验证 BGM 音频记录生成。", fn=_case_audio_bgm),
        EvalCase(id="agent.quality_no_video", name="QualityCheckAgent 无视频判定", category="agent", target="quality_check_agent", description="无视频时应判定未通过。", fn=_case_quality_no_video),
        EvalCase(id="agent.post_process_single", name="PostProcessAgent 单片段拼接", category="agent", target="post_process_agent", description="单片段拼接应直接复制成功。", fn=_case_post_process_single),
        EvalCase(id="agent.orchestrator.simple_multi_segment", name="调度 Agent（Simple）多片段", category="agent", target="orchestrator", description="多片段任务应生成 2 个片段并完成。", fn=_case_simple_multi_segment),
        EvalCase(id="agent.orchestrator.langgraph_multi_segment", name="调度 Agent（LangGraph）多片段", category="agent", target="orchestrator", description="多片段任务应生成 2 个片段并完成。", fn=_case_langgraph_multi_segment),
        EvalCase(id="agent.orchestrator.simple_audio_failure_nonblocking", name="调度 Agent（Simple）TTS 失败不阻塞", category="agent", target="orchestrator", description="TTS 失败时任务仍应完成且音频为空。", fn=_case_simple_audio_failure_nonblocking),
        EvalCase(id="agent.orchestrator.simple_subtitle_failure_nonblocking", name="调度 Agent（Simple）字幕失败不阻塞", category="agent", target="orchestrator", description="字幕失败时任务仍应完成且字幕为空。", fn=_case_simple_subtitle_failure_nonblocking),
        EvalCase(id="agent.orchestrator.simple_video_failure_marks_failed", name="调度 Agent（Simple）视频失败标记失败", category="agent", target="orchestrator", description="真实视频失败应标记任务失败而不是占位完成。", fn=_case_simple_video_failure_marks_failed),
        EvalCase(id="agent.orchestrator.langgraph_video_failure_marks_failed", name="调度 Agent（LangGraph）视频失败标记失败", category="agent", target="orchestrator", description="LangGraph 视频失败应标记任务失败。", fn=_case_langgraph_video_failure_marks_failed),
        EvalCase(
            id="agent.trajectory.golden",
            name="轨迹评测-黄金轨迹对比",
            category="agent",
            target="orchestrator",
            description="完整流水线实际轨迹应与黄金轨迹匹配，并校验关键工具调用。",
            fn=_case_trajectory_golden,
            latency_budget_ms=10000,
            cost_budget=0.1,
        ),
        EvalCase(
            id="agent.tool_use.correctness",
            name="工具调用正确性",
            category="agent",
            target="orchestrator",
            description="参考图应传给文生图，首帧与参考图应传给视频生成。",
            fn=_case_tool_use_correctness,
            latency_budget_ms=10000,
            cost_budget=0.1,
        ),
    ]
