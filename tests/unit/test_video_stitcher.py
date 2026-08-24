"""视频拼接服务单元测试。"""

from pathlib import Path

from app.services.video_stitcher import (
    StitchingError,
    build_concat_file,
    extract_last_frame,
    merge_audio,
    stitch_videos,
)


def test_build_concat_file(local_tmp_path: Path) -> None:
    """生成 FFmpeg concat 文件列表。"""
    segment_paths = [local_tmp_path / "a.mp4", local_tmp_path / "b.mp4"]
    list_file = local_tmp_path / "list.txt"

    build_concat_file(segment_paths, list_file)

    content = list_file.read_text(encoding="utf-8")
    assert "a.mp4" in content
    assert "b.mp4" in content


def test_stitch_single_file_copies(local_tmp_path: Path) -> None:
    """单个片段时直接复制，不调用 FFmpeg。"""
    source = local_tmp_path / "source.mp4"
    source.write_bytes(b"video-data")
    output = local_tmp_path / "output.mp4"

    result = stitch_videos([source], output)

    assert result == output
    assert output.read_bytes() == b"video-data"


def test_stitch_empty_raises(local_tmp_path: Path) -> None:
    """没有片段时抛出 StitchingError。"""
    try:
        stitch_videos([], local_tmp_path / "out.mp4")
    except StitchingError:
        return
    raise AssertionError("应当抛出 StitchingError")


def test_stitch_two_real_clips(local_tmp_path: Path) -> None:
    """两个真实 MP4 片段应能拼接成功。"""
    mock_clip = Path("app/providers/assets/mock_clip.mp4")
    first = local_tmp_path / "first.mp4"
    second = local_tmp_path / "second.mp4"
    first.write_bytes(mock_clip.read_bytes())
    second.write_bytes(mock_clip.read_bytes())
    output = local_tmp_path / "output.mp4"

    stitch_videos([first, second], output)

    assert output.exists()
    assert output.stat().st_size > 0


def test_merge_audio_replaces_audio_track(local_tmp_path: Path) -> None:
    """外部 TTS 音频应能替换进视频并生成新文件。"""
    import subprocess

    from app.services.video_stitcher import _get_ffmpeg_executable

    source = Path("app/providers/assets/mock_clip.mp4")
    audio = local_tmp_path / "tts.wav"
    output = local_tmp_path / "merged.mp4"

    ffmpeg = _get_ffmpeg_executable()
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            "0.5",
            str(audio),
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )

    result = merge_audio(source, audio, output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0


def test_extract_last_frame(local_tmp_path: Path) -> None:
    """应能从视频中提取最后一帧为 JPG。"""
    source = Path("app/providers/assets/mock_clip.mp4")
    output = local_tmp_path / "last_frame.jpg"

    result = extract_last_frame(source, output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size > 0

