"""视频后处理服务单元测试。"""

from pathlib import Path
from unittest import mock

from app.core.config import get_settings
from app.services.postprocess_service import (
    PostProcessError,
    enhance_video,
    interpolate_frames,
    postprocess_video,
)


def test_enhance_video(local_tmp_path: Path) -> None:
    """超分/放大应生成新视频文件。"""
    source = Path("app/providers/assets/mock_clip.mp4")
    output = local_tmp_path / "enhanced.mp4"

    result = enhance_video(source, output, target_resolution="720p", sharpen=True)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


def test_interpolate_frames(local_tmp_path: Path) -> None:
    """插帧应生成新视频文件。"""
    source = Path("app/providers/assets/mock_clip.mp4")
    output = local_tmp_path / "interpolated.mp4"

    result = interpolate_frames(source, output, factor=2)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


def test_postprocess_video(local_tmp_path: Path) -> None:
    """完整后处理应生成新视频文件。"""
    settings = get_settings()
    with mock.patch.object(settings, "video_interpolate_factor", 1):
        source = Path("app/providers/assets/mock_clip.mp4")
        output = local_tmp_path / "postprocessed.mp4"

        result = postprocess_video(source, output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


def test_interpolate_factor_one_copies(local_tmp_path: Path) -> None:
    """插帧因子为 1 时应直接复制。"""
    source = local_tmp_path / "source.mp4"
    source.write_bytes(b"video-data")
    output = local_tmp_path / "out.mp4"

    interpolate_frames(source, output, factor=1)

    assert output.read_bytes() == b"video-data"


def test_enhance_missing_input_raises(local_tmp_path: Path) -> None:
    """输入不存在时应抛出 PostProcessError。"""
    try:
        enhance_video(local_tmp_path / "missing.mp4", local_tmp_path / "out.mp4")
    except PostProcessError:
        return
    raise AssertionError("应当抛出 PostProcessError")
