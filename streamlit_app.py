"""Streamlit 前端（Sprint 1 MVP）。

运行方式：
    streamlit run streamlit_app.py

默认连接 http://localhost:8000，可通过环境变量 API_BASE_URL 修改。
Docker 部署时：API_BASE_URL=http://api:8000，PUBLIC_API_BASE_URL=http://localhost:8000。
"""

import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
PUBLIC_API_BASE_URL = os.getenv("PUBLIC_API_BASE_URL", API_BASE_URL).rstrip("/")
API_PREFIX = f"{API_BASE_URL}/api/v1"


def api_request(
    method: str,
    path: str,
    token: str | None = None,
    json: dict | None = None,
) -> httpx.Response:
    """发起后端请求。"""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{API_PREFIX}{path}", headers=headers, json=json, timeout=60)


def get_error_message(response: httpx.Response, fallback: str = "请求失败") -> str:
    """从后端响应中提取人类可读的错误信息。"""
    try:
        data = response.json()
    except Exception:
        return fallback

    detail = data.get("detail", data.get("message", fallback))

    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                location = ".".join(str(part) for part in item.get("loc", []))
                message = item.get("msg", "参数错误")
                parts.append(f"{location}: {message}" if location else message)
            else:
                parts.append(str(item))
        return "；".join(parts)

    if isinstance(detail, str):
        return detail

    return str(detail)


def download_video_file(task_id: int) -> httpx.Response:
    """携带登录凭证下载视频文件。"""
    headers = {}
    token = st.session_state.get("token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.get(
        f"{API_PREFIX}/generate/{task_id}/download",
        headers=headers,
        follow_redirects=True,
        timeout=120,
    )


def render_login_register() -> None:
    """登录 / 注册页面。"""
    st.title("AI 视频生成工具")
    mode = st.radio("选择操作", ["登录", "注册"], horizontal=True)

    username = st.text_input("用户名")
    password = st.text_input("密码", type="password")
    email = st.text_input("邮箱（注册时选填）")

    if st.button("提交"):
        if mode == "注册":
            response = api_request("POST", "/auth/register", json={
                "username": username,
                "password": password,
                "email": email or None,
            })
        else:
            response = api_request("POST", "/auth/login", json={
                "username": username,
                "password": password,
            })

        if response.status_code == 200:
            data = response.json()
            st.session_state["token"] = data["access_token"]
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error(get_error_message(response, "请求失败"))


def render_create() -> None:
    """创作页面。"""
    st.subheader("创作视频")
    prompt = st.text_area("输入创意", placeholder="例如：一只猫在雨天奔跑")
    duration = st.slider("时长（秒）", 5, 60, 5, step=5)
    aspect_ratio = st.selectbox("画面比例", ["16:9", "9:16", "1:1"])
    quality_options = {"快速": "fast", "标准": "standard", "高清": "high"}
    quality_label = st.selectbox("质量档位", list(quality_options.keys()), index=1)
    quality = quality_options[quality_label]

    # 可选角色
    characters_response = api_request("GET", "/characters", token=st.session_state.get("token"))
    character_options = {"不使用角色": None}
    if characters_response.status_code == 200:
        for character in characters_response.json():
            character_options[f"{character['id']} - {character['name']}"] = character["id"]
    selected_character = st.selectbox("选择角色（可选）", list(character_options.keys()))
    character_id = character_options[selected_character]

    if st.button("开始生成"):
        if not prompt.strip():
            st.warning("请输入创意")
            return
        response = api_request(
            "POST",
            "/generate/video",
            token=st.session_state.get("token"),
            json={
                "prompt": prompt.strip(),
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "quality": quality,
                "character_id": character_id,
            },
        )
        if response.status_code == 200:
            data = response.json()
            st.success(f"任务已提交，任务 ID：{data['id']}")
            st.session_state["last_task_id"] = data["id"]
        else:
            st.error(get_error_message(response, "提交失败"))


def render_characters() -> None:
    """角色库页面。"""
    st.subheader("角色库")

    # 创建角色
    with st.form("create_character_form"):
        st.markdown("### 创建角色")
        name = st.text_input("角色名称")
        reference_image_url = st.text_input("参考图 URL")
        description = st.text_area("角色描述（选填）")
        submitted = st.form_submit_button("保存角色")
        if submitted:
            if not name.strip() or not reference_image_url.strip():
                st.warning("角色名称和参考图 URL 必填")
            else:
                response = api_request(
                    "POST",
                    "/characters",
                    token=st.session_state.get("token"),
                    json={
                        "name": name.strip(),
                        "reference_image_url": reference_image_url.strip(),
                        "description": description.strip() or None,
                    },
                )
                if response.status_code == 200:
                    st.success("角色已保存")
                else:
                    st.error(get_error_message(response, "保存失败"))

    # 角色列表
    st.markdown("### 角色列表")
    response = api_request("GET", "/characters", token=st.session_state.get("token"))
    if response.status_code != 200:
        st.error(get_error_message(response, "获取角色失败"))
        return

    characters = response.json()
    if not characters:
        st.info("暂无角色")
        return

    for character in characters:
        character_id = character["id"]
        st.markdown(f"**{character['name']}**（ID: {character_id}）")
        st.write(f"参考图：{character['reference_image_url']}")

        # 查看详情（含多角度图）
        detail_response = api_request(
            "GET",
            f"/characters/{character_id}",
            token=st.session_state.get("token"),
        )
        if detail_response.status_code == 200:
            multi_views = detail_response.json().get("multi_views", [])
            if multi_views:
                st.write("多角度参考图：")
                for view in multi_views:
                    st.write(f"- {view['view_name']}: {view['image_url']}")

        # 添加多角度图
        with st.form(f"add_multi_view_{character_id}"):
            view_name = st.text_input("角度名称", key=f"view_name_{character_id}")
            image_url = st.text_input("图片 URL", key=f"image_url_{character_id}")
            add_submitted = st.form_submit_button("添加多角度图")
            if add_submitted:
                if not view_name.strip() or not image_url.strip():
                    st.warning("角度名称和图片 URL 必填")
                else:
                    add_response = api_request(
                        "POST",
                        f"/characters/{character_id}/multi-views",
                        token=st.session_state.get("token"),
                        json={"view_name": view_name.strip(), "image_url": image_url.strip()},
                    )
                    if add_response.status_code == 200:
                        st.success("多角度图已添加")
                    else:
                        st.error(add_response.json().get("detail", "添加失败"))


def render_audio_subtitle() -> None:
    """音频与字幕页面。"""
    st.subheader("音频与字幕")

    st.markdown("### 生成配音")
    tts_text = st.text_area("配音文本", key="tts_text")
    voice_id = st.text_input("音色", value="female_01", key="voice_id")
    if st.button("生成配音"):
        if not tts_text.strip():
            st.warning("请输入配音文本")
        else:
            response = api_request(
                "POST",
                "/generate/audio",
                token=st.session_state.get("token"),
                json={"type": "tts", "text": tts_text.strip(), "voice_id": voice_id},
            )
            if response.status_code == 200:
                data = response.json()
                st.success(f"配音已生成：{data['source_url']}")
            else:
                st.error(get_error_message(response, "生成失败"))

    st.markdown("### 生成背景音乐")
    if st.button("生成背景音乐"):
        response = api_request(
            "POST",
            "/generate/audio",
            token=st.session_state.get("token"),
            json={"type": "bgm"},
        )
        if response.status_code == 200:
            data = response.json()
            st.success(f"背景音乐已生成：{data['source_url']}")
        else:
            st.error(get_error_message(response, "生成失败"))

    st.markdown("### 生成字幕")
    subtitle_text = st.text_area("字幕文本", key="subtitle_text")
    if st.button("生成字幕"):
        if not subtitle_text.strip():
            st.warning("请输入字幕文本")
        else:
            response = api_request(
                "POST",
                "/generate/subtitle",
                token=st.session_state.get("token"),
                json={"text": subtitle_text.strip()},
            )
            if response.status_code == 200:
                data = response.json()
                st.success(f"字幕已生成：{data['subtitle_url']}")
                st.code(data["content"])
            else:
                st.error(get_error_message(response, "生成失败"))


def render_cost() -> None:
    """成本页面。"""
    st.subheader("成本")

    summary_response = api_request("GET", "/cost/summary", token=st.session_state.get("token"))
    if summary_response.status_code == 200:
        st.json(summary_response.json())
    else:
        st.error(summary_response.json().get("detail", "获取成本汇总失败"))

    st.markdown("### 查询任务成本")
    task_id = st.number_input("任务 ID", min_value=1, step=1, key="cost_task_id")
    if st.button("查询任务成本"):
        response = api_request(
            "GET",
            f"/cost/task/{int(task_id)}",
            token=st.session_state.get("token"),
        )
        if response.status_code == 200:
            st.json(response.json())
        else:
            st.error(get_error_message(response, "查询失败"))


def render_task_status() -> None:
    """任务进度页面。"""
    st.subheader("任务进度")
    task_id = st.number_input("任务 ID", min_value=1, step=1, value=st.session_state.get("last_task_id", 1))
    if st.button("查询进度"):
        response = api_request(
            "GET",
            f"/generate/status/{int(task_id)}",
            token=st.session_state.get("token"),
        )
        if response.status_code == 200:
            data = response.json()
            st.write(f"状态：{data['status']}")
            st.progress(data["progress"])
            st.write(f"当前阶段：{data['current_stage']}")
            st.write(f"片段进度：{data['segments_done']} / {data['segments_total']}")
            st.write(f"预估成本：{data['estimated_cost']} 元")
            if data["status"] == "completed":
                try:
                    file_response = download_video_file(int(task_id))
                    if file_response.status_code == 200:
                        st.download_button(
                            "下载视频",
                            data=file_response.content,
                            file_name=f"task_{int(task_id)}.mp4",
                            mime="video/mp4",
                            key=f"download_task_{int(task_id)}",
                        )
                    else:
                        st.error(get_error_message(file_response, "下载失败"))
                except Exception:  # noqa: BLE001
                    st.error("下载失败，请稍后重试")
        else:
            st.error(get_error_message(response, "查询失败"))


def render_history() -> None:
    """历史记录页面。"""
    st.subheader("历史记录")
    response = api_request("GET", "/history", token=st.session_state.get("token"))
    if response.status_code == 200:
        tasks = response.json()
        if not tasks:
            st.info("暂无历史任务")
        for task in tasks:
            st.markdown(
                f"**任务 #{task['id']}** - {task['prompt'][:30]} - {task['status']}"
            )
            if task.get("video_url"):
                if st.button(
                    f"准备下载任务 {task['id']}",
                    key=f"prepare_download_{task['id']}",
                ):
                    file_response = download_video_file(task["id"])
                    if file_response.status_code == 200:
                        st.session_state[f"download_data_{task['id']}"] = file_response.content
                    else:
                        st.error(get_error_message(file_response, "下载失败"))
                if f"download_data_{task['id']}" in st.session_state:
                    st.download_button(
                        "点击保存视频",
                        data=st.session_state[f"download_data_{task['id']}"],
                        file_name=f"task_{task['id']}.mp4",
                        mime="video/mp4",
                        key=f"save_download_{task['id']}",
                    )
    else:
        st.error(get_error_message(response, "获取历史失败"))


def main() -> None:
    """应用入口。"""
    st.set_page_config(page_title="AI 视频生成工具", layout="wide")

    if "token" not in st.session_state:
        render_login_register()
        return

    st.sidebar.write(f"当前用户：{st.session_state.get('username', '')}")
    page = st.sidebar.radio(
        "导航",
        ["创作", "任务进度", "历史记录", "角色库", "音频/字幕", "成本"],
    )

    if st.sidebar.button("退出登录"):
        st.session_state.clear()
        st.rerun()

    if page == "创作":
        render_create()
    elif page == "任务进度":
        render_task_status()
    elif page == "历史记录":
        render_history()
    elif page == "角色库":
        render_characters()
    elif page == "音频/字幕":
        render_audio_subtitle()
    else:
        render_cost()


if __name__ == "__main__":
    main()
