"""Blender 导入白模场景 JSON。"""

import json
from pathlib import Path

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

FPS = 24


def _create_mesh(name: str, obj_type: str, parent=None):
    """创建基础几何体或灰模人形。"""
    if obj_type == "box":
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.active_object
        obj.name = name
    elif obj_type == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1)
        obj = bpy.context.active_object
        obj.name = name
    elif obj_type == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5)
        obj = bpy.context.active_object
        obj.name = name
    elif obj_type == "plane":
        bpy.ops.mesh.primitive_plane_add(size=1)
        obj = bpy.context.active_object
        obj.name = name
    elif obj_type == "humanoid":
        bpy.ops.object.empty_add(type="ARROWS")
        obj = bpy.context.active_object
        obj.name = name
        parts = [
            ("body", (0, 0, 0.9), (0.6, 0.8, 0.3)),
            ("head", (0, 0, 1.55), (0.35, 0.35, 0.35)),
            ("left_leg", (-0.15, 0, 0.3), (0.18, 0.2, 0.6)),
            ("right_leg", (0.15, 0, 0.3), (0.18, 0.2, 0.6)),
            ("left_arm", (-0.42, 0, 1.0), (0.14, 0.18, 0.55)),
            ("right_arm", (0.42, 0, 1.0), (0.14, 0.18, 0.55)),
        ]
        for part_name, loc, scale in parts:
            bpy.ops.mesh.primitive_cube_add(size=1)
            part = bpy.context.active_object
            part.name = f"{name}_{part_name}"
            part.location = loc
            part.scale = scale
            part.parent = obj
    else:
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.active_object
        obj.name = name

    if parent is not None and obj.parent is None:
        obj.parent = parent
    return obj


class IMPORT_PREVIS_SCENE(Operator, ImportHelper):
    """导入白模场景 JSON。"""

    bl_idname = "import_scene.ai_video_previs"
    bl_label = "Import AI Video Previs (.json)"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        path = Path(self.filepath)
        if not path.exists():
            self.report({"ERROR"}, "文件不存在")
            return {"CANCELLED"}

        data = json.loads(path.read_text(encoding="utf-8"))
        scene = bpy.context.scene
        scene.frame_start = 1
        scene.frame_end = max(1, int(data.get("duration", 5) * FPS))

        for obj_data in data.get("objects", []):
            obj = _create_mesh(obj_data.get("name", "Object"), obj_data.get("type", "box"))
            obj.location = obj_data.get("position", [0, 0, 0])
            obj.rotation_euler = obj_data.get("rotation", [0, 0, 0])
            obj.scale = obj_data.get("scale", [1, 1, 1])

            for frame in data.get("keyframes", {}).get(obj_data.get("id", ""), []):
                frame_number = int(frame.get("time", 0) * FPS) + 1
                obj.location = frame.get("position", obj.location)
                obj.rotation_euler = frame.get("rotation", obj.rotation_euler)
                obj.scale = frame.get("scale", obj.scale)
                obj.keyframe_insert(data_path="location", frame=frame_number)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame_number)
                obj.keyframe_insert(data_path="scale", frame=frame_number)

        # 相机路径
        camera_keyframes = data.get("cameraKeyframes", [])
        if camera_keyframes:
            bpy.ops.object.camera_add()
            camera = bpy.context.active_object
            for frame in camera_keyframes:
                frame_number = int(frame.get("time", 0) * FPS) + 1
                camera.location = frame.get("position", camera.location)
                camera.keyframe_insert(data_path="location", frame=frame_number)

        self.report({"INFO"}, "白模场景导入完成")
        return {"FINISHED"}


def menu_func_import(self, context):
    """添加导入菜单项。"""
    self.layout.operator(IMPORT_PREVIS_SCENE.bl_idname, text="AI Video Previs (.json)")


def register() -> None:
    """注册导入器。"""
    bpy.utils.register_class(IMPORT_PREVIS_SCENE)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister() -> None:
    """注销导入器。"""
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.utils.unregister_class(IMPORT_PREVIS_SCENE)
