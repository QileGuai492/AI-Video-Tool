"""生成 Allure HTML 测试报告。

依赖：
- 已安装 allure-pytest（运行 pytest 时生成 allure-results）
- 已安装 Allure Commandline（提供 allure 命令）

用法：
    python scripts/generate_allure_report.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

RESULTS_DIR = Path("allure-results")
REPORT_DIR = Path("allure-report")


def main() -> None:
    """生成 Allure 报告。"""
    if not RESULTS_DIR.exists():
        print("未找到 allure-results，请先运行：pytest --alluredir=allure-results")
        sys.exit(1)

    allure = shutil.which("allure")
    if allure is None:
        print("未找到 allure 命令，请先安装 Allure Commandline。")
        print("安装参考：https://allurereport.org/docs/install/")
        sys.exit(1)

    subprocess.run(
        [allure, "generate", str(RESULTS_DIR), "-o", str(REPORT_DIR), "--clean"],
        check=True,
    )
    print(f"Allure 报告已生成：{REPORT_DIR}")


if __name__ == "__main__":
    main()
