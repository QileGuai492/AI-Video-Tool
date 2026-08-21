"""深度指标与 LLM-as-Judge 评测用例。"""

from app.providers.base import LLMRequest
from app.providers.registry import registry
from eval_harness.judge import LLMJudge
from eval_harness.models import EvalCase, EvalContext, EvalOutcome


def _case_prompt_llm_judge(ctx: EvalContext) -> EvalOutcome:
    """PromptAgent 输出质量：使用 LLM-as-Judge 打分。"""
    judge = LLMJudge()
    if not judge.available:
        return EvalOutcome(status="skipped", score=0.0, details="未配置真实 LLM，跳过 LLM 裁判")

    provider = registry.get_llm_provider()
    result = provider.complete(
        LLMRequest(
            system_prompt="你是一个短视频导演。",
            user_prompt="一只猫在夕阳下奔跑",
        )
    )
    score = judge.score(
        result.text or "",
        "提示词是否具体、有画面感、包含主体/动作/环境/光线/风格等要素，且没有冗余。",
    )
    if score is None:
        return EvalOutcome(status="error", score=0.0, details="LLM 裁判未能返回分数")
    return EvalOutcome(
        status="pass" if score >= 0.6 else "fail",
        score=score,
        metrics={"llm_judge_score": score},
        details=f"LLM 裁判得分：{score:.2f}",
    )


def build_deep_cases() -> list[EvalCase]:
    """构建深度指标评测用例。"""
    return [
        EvalCase(
            id="deep.prompt_llm_judge",
            name="PromptAgent LLM-as-Judge 质量打分",
            category="deep",
            target="prompt_agent",
            description="使用真实 LLM 对 PromptAgent 输出做主观质量评分。",
            fn=_case_prompt_llm_judge,
        )
    ]
