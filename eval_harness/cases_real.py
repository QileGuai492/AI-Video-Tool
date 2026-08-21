"""真实 API 冒烟评测用例。

这些用例会调用真实 SiliconFlow API，仅在显式指定 --real 且已配置 Key 时运行。
"""

import time

from app.core.config import get_settings
from app.providers.base import (
    ImageGenerationRequest,
    LLMRequest,
    TTSRequest,
    VideoGenerationRequest,
)
from app.providers.siliconflow import (
    SiliconFlowImageProvider,
    SiliconFlowLLMProvider,
    SiliconFlowTTSProvider,
    SiliconFlowVideoProvider,
)
from eval_harness.models import EvalCase, EvalContext, EvalOutcome


def _skipped(details: str) -> EvalOutcome:
    return EvalOutcome(status="skipped", score=0.0, details=details)


def _real_available() -> bool:
    return bool(get_settings().siliconflow_api_key)


def _case_real_llm(ctx: EvalContext) -> EvalOutcome:
    """真实 LLM 冒烟：应能返回非空文本。"""
    if not _real_available():
        return _skipped("未配置 SILICONFLOW_API_KEY")
    provider = SiliconFlowLLMProvider()
    start = time.perf_counter()
    result = provider.complete(
        LLMRequest(system_prompt="你是短视频导演。", user_prompt="用一句话描述夕阳下的猫")
    )
    duration_ms = (time.perf_counter() - start) * 1000
    ok = bool(result.text)
    return EvalOutcome(
        status="pass" if ok else "fail",
        score=1.0 if ok else 0.0,
        metrics={"耗时_ms": duration_ms, "成本": float(result.cost)},
        details=f"输出：{result.text[:80]}",
    )


def _case_real_image(ctx: EvalContext) -> EvalOutcome:
    """真实文生图冒烟：应能返回图片 URL。"""
    if not _real_available():
        return _skipped("未配置 SILICONFLOW_API_KEY")
    provider = SiliconFlowImageProvider()
    start = time.perf_counter()
    result = provider.generate_image(ImageGenerationRequest(prompt="一只猫在夕阳下", aspect_ratio="16:9"))
    duration_ms = (time.perf_counter() - start) * 1000
    ok = bool(result.image_url)
    return EvalOutcome(
        status="pass" if ok else "fail",
        score=1.0 if ok else 0.0,
        metrics={"耗时_ms": duration_ms, "成本": float(result.cost)},
        details=f"图片 URL：{result.image_url[:120]}",
    )


def _case_real_tts(ctx: EvalContext) -> EvalOutcome:
    """真实 TTS 冒烟：应能返回音频文件。"""
    if not _real_available():
        return _skipped("未配置 SILICONFLOW_API_KEY")
    provider = SiliconFlowTTSProvider()
    start = time.perf_counter()
    result = provider.synthesize(TTSRequest(text="你好，这是一段测试配音", voice_id="female_01"))
    duration_ms = (time.perf_counter() - start) * 1000
    ok = bool(result.audio_url)
    return EvalOutcome(
        status="pass" if ok else "fail",
        score=1.0 if ok else 0.0,
        metrics={"耗时_ms": duration_ms, "成本": float(result.cost)},
        details=f"音频 URL：{result.audio_url}",
    )


def _case_real_video(ctx: EvalContext) -> EvalOutcome:
    """真实文生视频冒烟：提交并轮询到成功（耗时较长，手动运行）。

    为避免 SiliconFlow 偶发失败导致评测不稳定，最多重试 1 次。
    """
    if not _real_available():
        return _skipped("未配置 SILICONFLOW_API_KEY")

    provider = SiliconFlowVideoProvider()
    all_trace: list[str] = []
    start = time.perf_counter()

    for attempt in range(2):
        handle = provider.submit_video_task(
            VideoGenerationRequest(prompt="一只猫在夕阳下奔跑", duration=5, aspect_ratio="16:9")
        )
        trace: list[str] = []
        for _ in range(600):
            status = provider.query_video_task(handle)
            trace.append(status.state)
            if status.state == "succeeded":
                duration_ms = (time.perf_counter() - start) * 1000
                return EvalOutcome(
                    status="pass",
                    score=1.0,
                    metrics={"耗时_ms": duration_ms, "重试次数": float(attempt)},
                    details=f"视频 URL：{status.video_url}",
                    trace=all_trace + trace,
                )
            if status.state == "failed":
                all_trace.extend(trace)
                all_trace.append(f"attempt_{attempt}_failed")
                break
            time.sleep(1)
        else:
            all_trace.extend(trace)
            all_trace.append(f"attempt_{attempt}_timeout")

    return EvalOutcome(
        status="fail",
        score=0.0,
        metrics={"耗时_ms": (time.perf_counter() - start) * 1000},
        details="真实视频生成失败或超时（已重试 1 次）",
        trace=all_trace,
    )


def build_real_smoke_cases() -> list[EvalCase]:
    """构建真实 API 冒烟评测用例。"""
    return [
        EvalCase(
            id="real.llm",
            name="真实 LLM 冒烟",
            category="real",
            target="siliconflow_llm",
            description="调用真实 SiliconFlow LLM 验证连通性。",
            fn=_case_real_llm,
        ),
        EvalCase(
            id="real.image",
            name="真实文生图冒烟",
            category="real",
            target="siliconflow_image",
            description="调用真实 SiliconFlow 文生图验证连通性。",
            fn=_case_real_image,
        ),
        EvalCase(
            id="real.tts",
            name="真实 TTS 冒烟",
            category="real",
            target="siliconflow_tts",
            description="调用真实 SiliconFlow TTS 验证配音能力。",
            fn=_case_real_tts,
        ),
        EvalCase(
            id="real.video",
            name="真实文生视频冒烟",
            category="real",
            target="siliconflow_video",
            description="调用真实 SiliconFlow 文生视频并轮询到成功（耗时较长）。",
            fn=_case_real_video,
        ),
    ]
