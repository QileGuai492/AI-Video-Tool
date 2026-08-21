"""通义万相文生图 Provider。

使用阿里云 DashScope 异步任务接口，需配置 TONGYI_API_KEY。
"""

import time
from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.providers.base import ImageGenerationRequest, ImageGenerationResult

# DashScope 文生图接口
SUBMIT_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
TASK_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"


class TongyiImageProvider:
    """通义万相文生图 Provider。"""

    name = "tongyi"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.tongyi_api_key or ""
        self.model = "wanx-v1"

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """提交文生图任务并轮询结果。"""
        if not self.api_key:
            raise RuntimeError("未配置 TONGYI_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        size = self._resolve_size(request.aspect_ratio)
        payload = {
            "model": self.model,
            "input": {"prompt": request.prompt},
            "parameters": {"size": size, "n": 1},
        }

        with httpx.Client(timeout=60) as client:
            submit_response = client.post(SUBMIT_ENDPOINT, headers=headers, json=payload)
            submit_response.raise_for_status()
            task_id = submit_response.json()["output"]["task_id"]

            # 轮询任务结果
            for _ in range(60):
                task_response = client.get(TASK_ENDPOINT.format(task_id=task_id), headers=headers)
                task_response.raise_for_status()
                data = task_response.json()
                status = data["output"]["task_status"]
                if status == "SUCCEEDED":
                    image_url = data["output"]["results"][0]["url"]
                    return ImageGenerationResult(
                        image_url=image_url,
                        provider=self.name,
                        cost=Decimal("0.1"),
                        raw_response=data,
                    )
                if status == "FAILED":
                    raise RuntimeError("通义万相文生图失败")
                time.sleep(2)

        raise TimeoutError("通义万相文生图任务超时")

    def _resolve_size(self, aspect_ratio: str) -> str:
        """将比例映射为通义万相支持的尺寸。"""
        return {
            "16:9": "1280*720",
            "9:16": "720*1280",
            "1:1": "1024*1024",
        }.get(aspect_ratio, "1024*1024")
