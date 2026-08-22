# Blender 白模导入 Add-on

## 功能

将 Three.js 白模编辑器导出的 `previs-scene.json` 导入 Blender：

- 支持方块 / 圆柱 / 球体 / 平面 / 灰模人形
- 恢复对象位置 / 旋转 / 缩放
- 恢复对象关键帧动画
- 恢复相机关键帧路径

## 安装

1. 打开 Blender。
2. 菜单 `Edit > Preferences > Add-ons`。
3. 点击 `Install...`，选择本目录。
4. 启用 `AI Video Previs Import`。

## 使用

1. 在 Web 编辑器导出 `previs-scene.json`。
2. Blender 菜单 `File > Import > AI Video Previs (.json)`。
3. 选择 JSON 文件。
4. 导入后可在 Blender 中精修材质、灯光、动作并渲染白模视频。
