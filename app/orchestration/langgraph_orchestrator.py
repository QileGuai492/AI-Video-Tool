"""LangGraph 任务编排器。

将视频生成流水线建模为状态图：
优化提示词 → 首帧 → 视频片段 → 音频 → 字幕 → 后处理 → 质量检查 → 完成。
"""

import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import get_settings
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
from app.providers.base import (
    ImageGenerationRequest,
    LLMRequest,
    VideoGenerationRequest,
)
from app.providers.registry import registry
from app.services.audio_service import generate_tts_audio
from app.services.character_consistency import evaluate_character_consistency
from app.services.character_feature import build_character_feature_pack
from app.services.media_download import download_and_store_video
from app.services.postprocess_service import postprocess_video
from app.services.previs_service import (
    build_segment_prompt,
    extract_keyframes,
    extract_shot_keyframes,
)
from app.services.quality_service import evaluate_video, evaluate_video_with_vlm
from app.services.subtitle_service import generate_subtitle
from app.services.task_service import calculate_segment_count
from app.services.video_stitcher import (
    StitchingError,
    burn_subtitle,
    extract_last_frame,
    merge_audio,
    stitch_videos,
)
from app.storage import storage

# 单个长视频任务内并行生成短视频片段的最大并发数
MAX_PARALLEL_SEGMENTS = 4

logger = logging.getLogger(__name__)


def _resolve_speech_text(task: VideoTask) -> str:
    """确定配音/字幕文本：优先显式台词，其次提取引号内对白，最后用提示词。"""
    if task.speech_text and task.speech_text.strip():
        return task.speech_text.strip()
    match = re.search(r"[“\"]([^”\"]+)[”\"]", task.prompt)
    if match:
        return match.group(1).strip()
    return task.optimized_prompt or task.prompt


def _infer_voice(text: str) -> str:
    """根据文案关键词推断默认配音角色。"""
    male_keywords = ["他", "男", "父亲", "国王", "蜘蛛侠", "钢铁侠", "蝙蝠侠", "超人", "哥哥", "叔叔", "先生"]
    female_keywords = ["她", "女", "母亲", "女王", "公主", "姐姐", "阿姨", "女士"]
    if any(keyword in text for keyword in male_keywords):
        return "male_01"
    if any(keyword in text for keyword in female_keywords):
        return "female_01"
    return "female_01"


class GenerationState(TypedDict, total=False):
    """LangGraph 状态。"""

    task_id: int
    optimized_prompt: str | None
    first_frame_url: str | None
    previs_frames: list[str]
    segment_urls: list[str]
    audio_url: str | None
    subtitle_url: str | None
    final_video_url: str | None
    quality_score: float
    error: str | None


def _load_task(task_id: int) -> VideoTask | None:
    """加载任务。"""
    db = SessionLocal()
    try:
        return db.query(VideoTask).filter(VideoTask.id == task_id).first()
    finally:
        db.close()


def _update_task_status(task_id: int, status: str) -> None:
    """更新任务状态。"""
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
        if task is not None:
            task.status = status
            db.commit()
    finally:
        db.close()


def _write_generation_log(
    task_id: int | None,
    user_id: int,
    provider: str,
    call_type: str,
    cost,
    status: str,
) -> None:
    """写入 API 调用日志。"""
    db = SessionLocal()
    try:
        log = GenerationLog(
            task_id=task_id,
            user_id=user_id,
            provider=provider,
            call_type=call_type,
            cost=cost,
            status=status,
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


def _wait_for_real_video(
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
            video_url = download_and_store_video(status.video_url)
            if video_url is None:
                # 下载失败时直接使用原始视频 URL，保证可下载
                return status.video_url
            return video_url
        time.sleep(1)
    raise RuntimeError("视频生成超时，请稍后重试")


def optimize_prompt(state: GenerationState) -> GenerationState:
    """优化提示词。"""
    task_id = state["task_id"]
    _update_task_status(task_id, "optimizing_prompt")
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
        if task is None:
            return {**state, "error": "任务不存在"}

        provider = registry.get_llm_provider()
        result = provider.complete(
            LLMRequest(
                system_prompt="你是一个短视频导演。",
                user_prompt=task.prompt,
            )
        )
        task.optimized_prompt = result.text
        _write_generation_log(
            task_id=task.id,
            user_id=task.user_id,
            provider=result.provider,
            call_type="llm",
            cost=result.cost,
            status="success",
        )
        db.commit()
        return {**state, "optimized_prompt": result.text}
    finally:
        db.close()


def generate_first_frame(state: GenerationState) -> GenerationState:
    """生成首帧。"""
    task_id = state["task_id"]
    _update_task_status(task_id, "generating_first_frame")
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
        if task is None:
            return {**state, "error": "任务不存在"}

        reference_image_urls: list[str] = list(task.reference_image_urls or [])
        character_identity_text = ""
        if task.character_id is not None:
            character = db.query(Character).filter(Character.id == task.character_id).first()
            if character is not None:
                reference_image_urls.append(character.reference_image_url)
                multi_views = (
                    db.query(CharacterMultiView)
                    .filter(CharacterMultiView.character_id == character.id)
                    .all()
                )
                reference_image_urls.extend(view.image_url for view in multi_views)
                feature_pack = build_character_feature_pack(db, character.id)
                if feature_pack and feature_pack.description:
                    character_identity_text += (
                        f"；角色“{feature_pack.name}”的外貌特征：{feature_pack.description}"
                    )

        if task.previs_video_url:
            # 白模只作为动作/镜头参考，首帧必须用真实生成图，避免成品保留白模外观
            shots = (task.camera_script or {}).get("shots", [])
            if shots:
                previs_frames = extract_shot_keyframes(task.previs_video_url, shots)
            else:
                previs_frames = extract_keyframes(task.previs_video_url)
            if not previs_frames:
                return {**state, "error": "白模视频未抽取到关键帧"}
            if task.image_url:
                return {
                    **state,
                    "first_frame_url": task.image_url,
                    "previs_frames": previs_frames,
                }
            provider = registry.get_image_provider()
            result = provider.generate_image(
                ImageGenerationRequest(
                    prompt=(state.get("optimized_prompt") or task.prompt) + character_identity_text,
                    reference_image_urls=reference_image_urls,
                )
            )
            _write_generation_log(
                task_id=task.id,
                user_id=task.user_id,
                provider=result.provider,
                call_type="image",
                cost=result.cost,
                status="success",
            )
            return {
                **state,
                "first_frame_url": result.image_url,
                "previs_frames": previs_frames,
            }

        if task.image_url:
            return {**state, "first_frame_url": task.image_url, "previs_frames": []}

        provider = registry.get_image_provider()
        result = provider.generate_image(
            ImageGenerationRequest(
                prompt=(state.get("optimized_prompt") or task.prompt) + character_identity_text,
                reference_image_urls=reference_image_urls,
            )
        )
        _write_generation_log(
            task_id=task.id,
            user_id=task.user_id,
            provider=result.provider,
            call_type="image",
            cost=result.cost,
            status="success",
        )
        return {**state, "first_frame_url": result.image_url, "previs_frames": []}
    finally:
        db.close()


def generate_video_segments(state: GenerationState) -> GenerationState:
    """生成多个视频片段。"""
    task_id = state["task_id"]
    _update_task_status(task_id, "generating_video")
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
        if task is None:
            return {**state, "error": "任务不存在"}

        previs_frames = state.get("previs_frames", [])
        segment_count = len(previs_frames) if previs_frames else calculate_segment_count(task.duration or 60)
        provider = registry.get_video_provider()
        segment_urls: list[str] = []
        mock_clip_path = Path("app/providers/assets/mock_clip.mp4")
        placeholder_content = mock_clip_path.read_bytes() if mock_clip_path.exists() else b"mock-video"
        camera_shots = (task.camera_script or {}).get("shots", [])
        reference_image_urls: list[str] = list(task.reference_image_urls or [])
        character_identity_text = ""
        if task.character_id is not None:
            character = db.query(Character).filter(Character.id == task.character_id).first()
            if character is not None:
                reference_image_urls.append(character.reference_image_url)
                multi_views = (
                    db.query(CharacterMultiView)
                    .filter(CharacterMultiView.character_id == character.id)
                    .all()
                )
                reference_image_urls.extend(view.image_url for view in multi_views)
                feature_pack = build_character_feature_pack(db, character.id)
                if feature_pack and feature_pack.description:
                    character_identity_text += (
                        f"；角色“{feature_pack.name}”的外貌特征：{feature_pack.description}"
                    )
        mapping_rules: dict[str, str] = {}
        if task.character_mappings:
            for mapping in task.character_mappings:
                object_id = mapping.get("object_id")
                character_id = mapping.get("character_id")
                if not object_id or not character_id:
                    continue
                character = db.query(Character).filter(Character.id == character_id).first()
                if character is None:
                    continue
                reference_image_urls.append(character.reference_image_url)
                mapping_rules[str(object_id)] = f"@图片{len(reference_image_urls)}的{character.name}"
                feature_pack = build_character_feature_pack(db, character.id)
                if feature_pack and feature_pack.description:
                    character_identity_text += (
                        f"；角色“{feature_pack.name}”的外貌特征：{feature_pack.description}"
                    )
        layout_text = ""
        scene = task.previs_scene_json or {}
        if scene.get("objects"):
            layout_parts = []
            for obj in scene.get("objects", []):
                position = obj.get("position") or [0, 0, 0]
                try:
                    x = float(position[0])
                except (TypeError, ValueError):
                    x = 0
                side = "左侧" if x < -0.5 else "右侧" if x > 0.5 else "中间"
                layout_parts.append(f"{obj.get('name') or obj.get('id')}在{side}")
            if layout_parts:
                layout_text = (
                    "空间布局：" + "；".join(layout_parts) + "；保持左右方向不变，不要镜像翻转"
                )

        def generate_segment(index: int, frame_url: str | None) -> tuple[int, str, str]:
            shot = camera_shots[index] if index < len(camera_shots) else None
            segment_prompt = build_segment_prompt(
                state.get("optimized_prompt") or task.prompt,
                shot,
                mapping_rules=mapping_rules,
            )
            if layout_text:
                segment_prompt = f"{segment_prompt}；{layout_text}"
            if character_identity_text:
                segment_prompt = f"{segment_prompt}{character_identity_text}"
            request = VideoGenerationRequest(
                prompt=segment_prompt,
                first_frame_url=frame_url,
                reference_image_urls=reference_image_urls,
                duration=5,
                aspect_ratio=task.aspect_ratio or "16:9",
                model=task.resolution or "720p",
            )
            handle = provider.submit_video_task(request)

            # Mock 场景直接使用本地占位视频，避免轮询等待
            if provider.name.startswith("mock"):
                key = storage.upload(content=placeholder_content, suffix="mp4", folder="videos")
                video_url = storage.get_url(key)
            else:
                # 轮询真实 Provider；失败或超时直接抛出，不再回退占位视频
                video_url = _wait_for_real_video(provider, handle)
            return index, segment_prompt, video_url

        def ensure_local_segment(segment_url: str) -> Path | None:
            """把片段 URL 转为本地路径，供尾帧提取使用。"""
            if segment_url.startswith("/uploads/"):
                return Path("uploads") / segment_url.removeprefix("/uploads/")
            downloaded = download_and_store_video(segment_url)
            if downloaded and downloaded.startswith("/uploads/"):
                return Path("uploads") / downloaded.removeprefix("/uploads/")
            return None

        use_consistency_chain = bool(
            segment_count > 1
            and (task.character_id is not None or task.character_mappings or task.reference_image_urls)
        )
        segment_results: list[tuple[str, str] | None] = [None] * segment_count
        first_frame_url = state.get("first_frame_url")
        if use_consistency_chain:
            current_frame_url = first_frame_url
            for index in range(segment_count):
                _, segment_prompt, video_url = generate_segment(index, current_frame_url)
                segment_results[index] = (segment_prompt, video_url)
                if index < segment_count - 1:
                    local_segment = ensure_local_segment(video_url)
                    if local_segment is not None:
                        frame_path: Path | None = None
                        try:
                            tmp_dir = Path("uploads/tmp")
                            tmp_dir.mkdir(parents=True, exist_ok=True)
                            frame_path = tmp_dir / f"tail_{uuid.uuid4().hex}.jpg"
                            extract_last_frame(local_segment, frame_path)
                            key = storage.upload(
                                content=frame_path.read_bytes(),
                                suffix="jpg",
                                folder="frames",
                            )
                            current_frame_url = storage.get_url(key)
                        except Exception:  # noqa: BLE001
                            logger.warning("尾帧提取失败，继续使用当前首帧", exc_info=True)
                        finally:
                            if frame_path is not None:
                                frame_path.unlink(missing_ok=True)
        else:
            with ThreadPoolExecutor(
                max_workers=min(segment_count, get_settings().video_segment_concurrency)
            ) as executor:
                futures = [
                    executor.submit(generate_segment, i, first_frame_url)
                    for i in range(segment_count)
                ]
                for future in as_completed(futures):
                    index, segment_prompt, video_url = future.result()
                    segment_results[index] = (segment_prompt, video_url)

        segment_urls = [url for _, url in segment_results]
        for index, (segment_prompt, video_url) in enumerate(segment_results):
            db.add(
                VideoSegment(
                    task_id=task.id,
                    segment_index=index,
                    video_url=video_url,
                    prompt_used=segment_prompt,
                    model_used=provider.name,
                    duration=5,
                )
            )

        db.commit()
        return {**state, "segment_urls": segment_urls}
    finally:
        db.close()


def generate_audio(state: GenerationState) -> GenerationState:
    """生成配音。"""
    task_id = state["task_id"]
    _update_task_status(task_id, "generating_audio")
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
        if task is None:
            return {**state, "error": "任务不存在"}
        try:
            speech_text = _resolve_speech_text(task)
            track = generate_tts_audio(
                db=db,
                user_id=task.user_id,
                task_id=task.id,
                text=speech_text,
                voice_id=task.voice_id or _infer_voice(speech_text),
            )
            task.audio_url = track.source_url
            db.commit()
            return {**state, "audio_url": track.source_url}
        except Exception:  # noqa: BLE001
            return state
    finally:
        db.close()


def generate_subtitle_node(state: GenerationState) -> GenerationState:
    """生成字幕。"""
    task_id = state["task_id"]
    _update_task_status(task_id, "generating_subtitle")
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == task_id).first()
        if task is None:
            return {**state, "error": "任务不存在"}
        if not task.with_subtitle:
            return state
        try:
            subtitle_url, _ = generate_subtitle(_resolve_speech_text(task))
            task.subtitle_url = subtitle_url
            db.commit()
            return {**state, "subtitle_url": subtitle_url}
        except Exception:  # noqa: BLE001
            return state
    finally:
        db.close()


def post_process(state: GenerationState) -> GenerationState:
    """拼接片段、替换 TTS 音轨并烧录字幕，生成最终成片。"""
    _update_task_status(state["task_id"], "post_processing")
    segment_urls = state.get("segment_urls", [])
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
            output = stitched_dir / f"{uuid.uuid4().hex}.mp4"
            stitch_videos(local_paths, output)
            key = storage.upload(content=output.read_bytes(), suffix="mp4", folder="videos")
            final_video_url = storage.get_url(key)
        except (StitchingError, OSError):
            final_video_url = local_paths[0].as_posix().replace("uploads/", "/uploads/")
    elif local_paths:
        # 只有部分片段可本地化时，回退到第一个本地片段
        final_video_url = local_paths[0].as_posix().replace("uploads/", "/uploads/")

    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == state["task_id"]).first()
        if task is None:
            return {**state, "final_video_url": final_video_url}

        tmp_dir = Path("uploads/tmp")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # 把 TTS 配音替换进成片，避免保留视频模型自带音轨（可能是日语等）
        if task.audio_url and task.audio_url.startswith("/uploads/") and final_video_url and final_video_url.startswith("/uploads/"):
            audio_path = Path("uploads") / task.audio_url.removeprefix("/uploads/")
            source_video = Path("uploads") / final_video_url.removeprefix("/uploads/")
            merged_output = tmp_dir / f"merged_{uuid.uuid4().hex}.mp4"
            try:
                merge_audio(source_video, audio_path, merged_output)
                key = storage.upload(content=merged_output.read_bytes(), suffix="mp4", folder="videos")
                final_video_url = storage.get_url(key)
            except Exception:  # noqa: BLE001
                logger.warning("音频合成失败，保留原视频音轨", exc_info=True)
            finally:
                merged_output.unlink(missing_ok=True)

        # 按需烧录字幕
        if task.with_subtitle:
            try:
                _, subtitle_content = generate_subtitle(_resolve_speech_text(task))
                srt_path = tmp_dir / f"sub_{uuid.uuid4().hex}.srt"
                srt_path.write_text(subtitle_content, encoding="utf-8")
                source_video = Path("uploads") / final_video_url.removeprefix("/uploads/")
                burned_output = tmp_dir / f"subbed_{uuid.uuid4().hex}.mp4"
                try:
                    burn_subtitle(source_video, srt_path, burned_output)
                    key = storage.upload(content=burned_output.read_bytes(), suffix="mp4", folder="videos")
                    final_video_url = storage.get_url(key)
                except Exception:  # noqa: BLE001
                    logger.warning("字幕烧录失败，保留原视频", exc_info=True)
                finally:
                    srt_path.unlink(missing_ok=True)
                    burned_output.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                logger.warning("字幕生成失败，保留原视频", exc_info=True)

        # 可选后处理：超分 / 插帧 / 锐化
        if (
            get_settings().video_postprocess_enabled
            and final_video_url
            and final_video_url.startswith("/uploads/")
        ):
            source_video = Path("uploads") / final_video_url.removeprefix("/uploads/")
            enhanced_output = tmp_dir / f"enhanced_{uuid.uuid4().hex}.mp4"
            try:
                postprocess_video(source_video, enhanced_output)
                key = storage.upload(content=enhanced_output.read_bytes(), suffix="mp4", folder="videos")
                final_video_url = storage.get_url(key)
            except Exception:  # noqa: BLE001
                logger.warning("视频后处理失败，保留原视频", exc_info=True)
            finally:
                enhanced_output.unlink(missing_ok=True)

        # 可选角色一致性检查（失败可自动重试）
        if (
            get_settings().character_consistency_check_enabled
            and task.reference_image_urls
            and final_video_url
        ):
            report = evaluate_character_consistency(list(task.reference_image_urls), final_video_url)
            if report is not None and not report.passed:
                retry_count = (
                    db.query(TaskRetry)
                    .filter(
                        TaskRetry.task_id == task.id,
                        TaskRetry.stage == "consistency_retry",
                    )
                    .count()
                )
                if retry_count < get_settings().character_consistency_max_retries:
                    db.add(
                        TaskRetry(
                            task_id=task.id,
                            user_id=task.user_id,
                            stage="consistency_retry",
                            attempt=retry_count + 1,
                            error_code="CONSISTENCY_LOW",
                            error_message=report.reason,
                        )
                    )
                    task.status = "pending"
                    db.commit()
                    logger.warning("角色一致性未通过，已安排自动重试：%s", report.reason)
                    raise RuntimeError("CONSISTENCY_LOW_RETRY")
                logger.warning("角色一致性检查未通过且已达最大重试：%s", report.reason)
    finally:
        db.close()

    return {**state, "final_video_url": final_video_url}


def quality_check(state: GenerationState) -> GenerationState:
    """质量评估。"""
    _update_task_status(state["task_id"], "quality_check")
    settings = get_settings()
    if settings.quality_vlm_enabled:
        report = evaluate_video_with_vlm(state.get("final_video_url"), settings.quality_threshold)
    else:
        report = evaluate_video(state.get("final_video_url"), settings.quality_threshold)
    return {**state, "quality_score": report.score}


def finalize(state: GenerationState) -> GenerationState:
    """完成并保存结果。"""
    db = SessionLocal()
    try:
        task = db.query(VideoTask).filter(VideoTask.id == state["task_id"]).first()
        if task is None:
            return state
        task.video_url = state.get("final_video_url")
        task.status = "completed"
        task.completed_at = utc_now()
        db.commit()
    finally:
        db.close()
    return state


class LangGraphOrchestrator:
    """基于 LangGraph 的状态图编排器。"""

    def run(self, task_id: int) -> None:
        """构建图并执行。"""
        builder = StateGraph(GenerationState)
        builder.add_node("optimize_prompt", optimize_prompt)
        builder.add_node("generate_first_frame", generate_first_frame)
        builder.add_node("generate_video_segments", generate_video_segments)
        builder.add_node("generate_audio", generate_audio)
        builder.add_node("generate_subtitle", generate_subtitle_node)
        builder.add_node("post_process", post_process)
        builder.add_node("quality_check", quality_check)
        builder.add_node("finalize", finalize)

        builder.add_edge(START, "optimize_prompt")
        builder.add_edge("optimize_prompt", "generate_first_frame")
        builder.add_edge("generate_first_frame", "generate_video_segments")
        builder.add_edge("generate_video_segments", "generate_audio")
        builder.add_edge("generate_audio", "generate_subtitle")
        builder.add_edge("generate_subtitle", "post_process")
        builder.add_edge("post_process", "quality_check")
        builder.add_edge("quality_check", "finalize")
        builder.add_edge("finalize", END)

        graph = builder.compile()
        try:
            graph.invoke({"task_id": task_id})
        except Exception:
            _update_task_status(task_id, "failed")
            raise
