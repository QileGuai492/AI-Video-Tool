"""评测入口：python -m eval_harness [--real] [--judge] [--report PATH]"""

import argparse
import json
import os
import shutil
import statistics
from datetime import datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Harness 评测 Agent")
    parser.add_argument("--real", action="store_true", help="包含真实 SiliconFlow API 冒烟评测")
    parser.add_argument("--judge", action="store_true", help="兼容旧参数：LLM-as-Judge 现已默认包含")
    parser.add_argument("--report", default="logs/评测报告.md", help="报告输出路径")
    parser.add_argument("--clean", action="store_true", help="评测结束后清理 .eval_tmp 临时目录")
    parser.add_argument("--trend", action="store_true", help="记录历史趋势并输出趋势对比")
    parser.add_argument("--runs", type=int, default=1, help="重复运行次数，用于稳定性/方差统计")
    return parser.parse_args()


def main() -> None:
    """运行全部评测并输出报告。"""
    args = _parse_args()

    # 必须在导入 app 前完成环境隔离
    os.environ["APP_ENV"] = "local"
    if not args.real:
        os.environ["SILICONFLOW_API_KEY"] = ""
    os.environ["DATABASE_URL"] = "sqlite:///./.eval_tmp/eval.db"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["ORCHESTRATOR_BACKEND"] = "simple"
    Path(".eval_tmp").mkdir(exist_ok=True)

    from eval_harness.cases_agent import build_agent_cases
    from eval_harness.cases_deep import build_deep_cases
    from eval_harness.cases_real import build_real_smoke_cases
    from eval_harness.cases_system import build_system_cases
    from eval_harness.context import create_context
    from eval_harness.report import generate_markdown
    from eval_harness.runner import run_cases

    cases = build_agent_cases() + build_system_cases()
    if args.real:
        cases += build_real_smoke_cases()
    # LLM-as-Judge 默认纳入；未配置真实 LLM Key 时该用例会跳过
    cases += build_deep_cases()

    runs = max(1, args.runs)
    stability: dict | None = None
    if runs > 1:
        summaries: list = []
        results = None
        summary = None
        for _ in range(runs):
            run_ctx = create_context()
            run_results, run_summary = run_cases(cases, run_ctx)
            summaries.append(run_summary)
            results = run_results
            summary = run_summary
        stability = {
            "runs": runs,
            "pass_rate_mean": statistics.mean(item.pass_rate for item in summaries),
            "pass_rate_std": statistics.pstdev(item.pass_rate for item in summaries),
            "avg_score_mean": statistics.mean(item.avg_score for item in summaries),
            "avg_score_std": statistics.pstdev(item.avg_score for item in summaries),
            "duration_mean_ms": statistics.mean(item.total_duration_ms for item in summaries),
            "duration_std_ms": statistics.pstdev(item.total_duration_ms for item in summaries),
        }
    else:
        ctx = create_context()
        results, summary = run_cases(cases, ctx)

    mode = "Mock 隔离模式 + LLM-as-Judge"
    if args.real:
        mode = "Mock + 真实 API 冒烟模式 + LLM-as-Judge"

    history: list[dict] = []
    history_path = Path("logs/eval_history.json")
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []

    if args.trend:
        history.append(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "mode": mode,
                "total": summary.total,
                "passed": summary.passed,
                "failed": summary.failed,
                "errored": summary.errored,
                "pass_rate": summary.pass_rate,
                "avg_score": summary.avg_score,
                "total_duration_ms": summary.total_duration_ms,
            }
        )
        history_path.parent.mkdir(exist_ok=True)
        history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

    report_path = Path(args.report)
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(
        generate_markdown(results, summary, mode=mode, history=history, stability=stability),
        encoding="utf-8",
    )

    if args.clean:
        shutil.rmtree(".eval_tmp", ignore_errors=True)

    print(f"评测完成：总计 {summary.total}，通过 {summary.passed}，失败 {summary.failed}，"
          f"异常 {summary.errored}，跳过 {summary.skipped}，通过率 {summary.pass_rate:.1%}")
    print(f"报告已生成：{report_path}")


if __name__ == "__main__":
    main()
