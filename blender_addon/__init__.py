"""AI 视频生成工具 - 白模场景导入 Blender Add-on。"""

bl_info = {
    "name": "AI Video Previs Import",
    "author": "AI Video Tool",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "File > Import > AI Video Previs (.json)",
    "description": "导入 Three.js 白模场景 JSON 到 Blender",
    "category": "Import-Export",
}

from . import io_previs


def register() -> None:
    """注册插件。"""
    io_previs.register()


def unregister() -> None:
    """注销插件。"""
    io_previs.unregister()
