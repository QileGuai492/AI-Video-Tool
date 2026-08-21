"""简单任务编排器。

当前实现为 Sprint 1 的直写流水线：
提示词优化 → 首帧生成 → 多片段生成 → 完成。
后续 Sprint 4 将替换为 LangGraph 状态图实现。
"""

import time
import uuid
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.db.session import SessionLocal
from app.models import (
    Character,
    CharacterMultiView,
    GenerationLog,
    TaskRetry,
    VideoSegment,
    VideoTask,
)
from app.providers.base import ImageGenerationRequest, LLMRequest, VideoGenerationRequest
from app.providers.registry import registry
from app.services.audio_service import generate_tts_audio
from app.services.media_download import download_and_store_video
from app.services.subtitle_service import generate_subtitle
from app.services.task_service import calculate_segment_count
from app.services.video_stitcher import StitchingError, stitch_videos
from app.storage import storage


class SimpleTaskOrchestrator:
    """基于顺序调用的简单任务编排器。"""

    def _get_reference_image_urls(self, db: Session, character_id: int | None) -> list[str]:
        """根据角色 ID 获取参考图 URL 列表。"""
        if character_id is None:
            return []
        character = db.query(Character).filter(Character.id == character_id).first()
        if character is None:
            return []
        urls = [character.reference_image_url]
        multi_views = (
            db.query(CharacterMultiView)
            .filter(CharacterMultiView.character_id == character_id)
            .all()
        )
        urls.extend(view.image_url for view in multi_views)
        return urls

    def run(self, task_id: int) -> None:
        """执行完整生成流水线。"""
        db = SessionLocal()
        try:
            task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
            if task is None:
                return

            # 1. 优化提示词
            task.status = "optimizing_prompt"
            db.commit()

            llm_provider = registry.get_llm_provider()
            llm_result = llm_provider.complete(
                LLMRequest(
                    system_prompt="你是一个短视频导演。",
                    user_prompt=task.prompt,
                )
            )
            task.optimized_prompt = llm_result.text
            self._write_generation_log(
                db=db,
                task_id=task.id,
                user_id=task.user_id,
                provider=llm_result.provider,
                call_type="llm",
                cost=llm_result.cost,
                status="success",
            )
            db.commit()

            # 2. 生成首帧
            task.status = "generating_first_frame"
            db.commit()

            reference_image_urls = self._get_reference_image_urls(db, task.character_id)
            image_provider = registry.get_image_provider()
            image_result = image_provider.generate_image(
                ImageGenerationRequest(
                    prompt=task.optimized_prompt or task.prompt,
                    reference_image_urls=reference_image_urls,
                )
            )
            first_frame_url = image_result.image_url
            self._write_generation_log(
                db=db,
                task_id=task.id,
                user_id=task.user_id,
                provider=image_result.provider,
                call_type="image",
                cost=image_result.cost,
                status="success",
            )
            db.commit()

            # 3. 生成视频片段（Mock 直接返回成功）
            task.status = "generating_video"
            db.commit()

            segment_count = calculate_segment_count(task.duration or 60)
            video_provider = registry.get_video_provider()
            final_video_url: str | None = None

            # Mock 占位视频使用真实可拼接的小 MP4，保证拼接服务可验证
            mock_clip_path = Path("app/providers/assets/mock_clip.mp4")
            placeholder_video_content = mock_clip_path.read_bytes()
            segment_urls: list[str] = []

            for index in range(segment_count):
                video_request = VideoGenerationRequest(
                    prompt=task.optimized_prompt or task.prompt,
                    first_frame_url=first_frame_url,
                    reference_image_urls=reference_image_urls,
                    duration=5,
                    aspect_ratio=task.aspect_ratio or "16:9",
                    model=video_provider.name,
                )
                handle = video_provider.submit_video_task(video_request)
                segment_url = None

                if video_provider.name.startswith("mock"):
                    # Mock 场景直接使用本地占位视频
                    segment_key = storage.upload(
                        content=placeholder_video_content,
                        suffix="mp4",
                        folder="videos",
                    )
                    segment_url = storage.get_url(segment_key)
                else:
                    # 真实场景轮询并下载视频到共享存储；失败或超时不再静默回退占位视频
                    segment_url = self._wait_for_real_video(video_provider, handle)

                segment_urls.append(segment_url)
                segment = VideoSegment(
                    task_id=task.id,
                    segment_index=index,
                    video_url=segment_url,
                    prompt_used=task.optimized_prompt,
                    model_used=video_provider.name,
                    duration=5,
                )
                db.add(segment)
                final_video_url = segment_url

            # 4. 拼接片段：优先把远程片段补下到本地，全部本地后再拼接
            local_paths: list[Path] = []
            for url in segment_urls:
                if url.startswith("/uploads/"):
                    local_paths.append(Path("uploads") / url.removeprefix("/uploads/"))
                else:
                    downloaded = download_and_store_video(url)
                    if downloaded and downloaded.startswith("/uploads/"):
                        local_paths.append(Path("uploads") / downloaded.removeprefix("/uploads/"))

            final_video_url = segment_urls[0] if segment_urls else None
            if len(local_paths) == len(segment_urls) and len(local_paths) > 1:
                try:
                    stitched_dir = Path("uploads/stitched")
                    stitched_dir.mkdir(parents=True, exist_ok=True)
                    stitched_path = stitched_dir / f"{uuid.uuid4().hex}.mp4"
                    stitch_videos(local_paths, stitched_path)
                    stitched_content = stitched_path.read_bytes()
                    final_key = storage.upload(
                        content=stitched_content,
                        suffix="mp4",
                        folder="videos",
                    )
                    final_video_url = storage.get_url(final_key)
                except (StitchingError, OSError):
                    # 拼接失败时回退到第一个本地片段
                    final_video_url = local_paths[0].as_posix().replace("uploads/", "/uploads/")
            elif local_paths:
                # 只有部分片段可本地化时，回退到第一个本地片段
                final_video_url = local_paths[0].as_posix().replace("uploads/", "/uploads/")

            # 5. 自动生成配音与字幕（失败不阻塞主流程）
            try:
                audio_track = generate_tts_audio(
                    db=db,
                    user_id=task.user_id,
                    task_id=task.id,
                    text=task.optimized_prompt or task.prompt,
                    voice_id="female_01",
                )
                task.audio_url = audio_track.source_url
            except Exception:  # noqa: BLE001
                task.audio_url = None

            try:
                subtitle_url, _ = generate_subtitle(task.optimized_prompt or task.prompt)
                task.subtitle_url = subtitle_url
            except Exception:  # noqa: BLE001
                task.subtitle_url = None

            task.video_url = final_video_url
            task.status = "completed"
            task.completed_at = utc_now()
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
            if task is not None:
                task.status = "failed"
                attempt_count = (
                    db.query(TaskRetry).filter(TaskRetry.task_id == task.id).count() + 1
                )
                db.add(
                    TaskRetry(
                        task_id=task.id,
                        stage="pipeline",
                        attempt=attempt_count,
                        error_code="INTERNAL_ERROR",
                        error_message=str(exc)[:500],
                    )
                )
                db.commit()
            raise exc
        finally:
            db.close()

    def _wait_for_real_video(
        self,
        video_provider,
        handle,
        max_attempts: int = 600,
    ) -> str:
        """轮询真实视频 Provider 直到成功，失败或超时直接抛出异常。

        返回本地存储 URL；若下载失败则返回原始远程 URL，保证下载接口仍可用。
        """
        for _ in range(max_attempts):
            status = video_provider.query_video_task(handle)
            if status.state == "failed":
                raise RuntimeError(status.error_message or "视频生成失败")
            if status.state == "succeeded":
                if not status.video_url:
                    raise RuntimeError("视频生成成功但未返回视频 URL")
                segment_url = download_and_store_video(status.video_url)
                if segment_url is None:
                    # 下载失败时直接使用原始视频 URL，保证可下载
                    return status.video_url
                return segment_url
            time.sleep(1)
        raise RuntimeError("视频生成超时，请稍后重试")

    def _write_generation_log(
        self,
        db: Session,
        task_id: int | None,
        user_id: int,
        provider: str,
        call_type: str,
        cost: Decimal,
        status: str,
        error_code: str | None = None,
    ) -> None:
        """写入 API 调用日志，用于成本审计。"""
        log = GenerationLog(
            task_id=task_id,
            user_id=user_id,
            provider=provider,
            call_type=call_type,
            cost=cost,
            status=status,
            error_code=error_code,
        )
        db.add(log)
