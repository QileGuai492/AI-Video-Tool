import { Button, Divider, Space, Typography, message } from "antd";
import { useRef } from "react";
import { cameraRef } from "../previs/cameraRef";
import { applyCameraPreset, CAMERA_PRESET_LABELS, type CameraPreset } from "../previs/cameraPresets";
import { usePrevisStore } from "../previs/store";
import type { ObjectType, SceneState } from "../previs/types";

const { Text } = Typography;

export default function EditorToolbar({
  onSave,
  mode = "advanced",
}: {
  onSave?: (scene: unknown) => void;
  mode?: "simple" | "advanced";
}) {
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const currentTime = usePrevisStore((state) => state.currentTime);
  const isPlaying = usePrevisStore((state) => state.isPlaying);
  const addObject = usePrevisStore((state) => state.addObject);
  const removeObject = usePrevisStore((state) => state.removeObject);
  const duplicateObject = usePrevisStore((state) => state.duplicateObject);
  const addKeyframe = usePrevisStore((state) => state.addKeyframe);
  const addCameraKeyframe = usePrevisStore((state) => state.addCameraKeyframe);
  const cameraKeyframes = usePrevisStore((state) => state.cameraKeyframes);
  const setIsPlaying = usePrevisStore((state) => state.setIsPlaying);
  const exportScene = usePrevisStore((state) => state.exportScene);
  const loadScene = usePrevisStore((state) => state.loadScene);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const objectTypes: { type: ObjectType; label: string }[] = [
    { type: "box", label: "方块" },
    { type: "cylinder", label: "圆柱" },
    { type: "sphere", label: "球体" },
    { type: "plane", label: "平面" },
    { type: "humanoid", label: "灰模人形" },
  ];

  const handleExport = () => {
    const scene = exportScene();
    const blob = new Blob([JSON.stringify(scene, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "previs-scene.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleAddCameraKeyframe = () => {
    addCameraKeyframe(currentTime, cameraRef.position, cameraRef.target);
    message.success(`已记录相机关键帧：${currentTime.toFixed(1)}s（共 ${cameraKeyframes.length + 1} 个）`);
  };

  const handleCameraPreset = (preset: CameraPreset) => {
    const next = applyCameraPreset(preset, cameraRef.position, cameraRef.target);
    addCameraKeyframe(currentTime, next.position, next.target);
    const label = CAMERA_PRESET_LABELS.find((item) => item.value === preset)?.label ?? preset;
    message.success(`已应用运镜预设「${label}」并记录关键帧：${currentTime.toFixed(1)}s`);
  };

  const handleImport = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const scene = JSON.parse(String(reader.result)) as SceneState;
        loadScene(scene);
      } catch {
        // 忽略解析失败
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ marginBottom: 16 }}>
      {mode === "advanced" && (
        <Space wrap style={{ marginBottom: 8 }}>
          <Text type="secondary">添加对象</Text>
          <Space.Compact>
            {objectTypes.map((item) => (
              <Button key={item.type} size="small" onClick={() => addObject(item.type)}>
                {item.label}
              </Button>
            ))}
          </Space.Compact>
          <Divider type="vertical" />
          <Text type="secondary">编辑</Text>
          <Space.Compact>
            <Button
              size="small"
              type="primary"
              disabled={!selectedObjectId}
              onClick={() => selectedObjectId && addKeyframe(selectedObjectId, currentTime)}
            >
              记录关键帧
            </Button>
            <Button
              size="small"
              disabled={!selectedObjectId}
              onClick={() => selectedObjectId && duplicateObject(selectedObjectId)}
            >
              复制
            </Button>
            <Button
              size="small"
              danger
              disabled={!selectedObjectId}
              onClick={() => selectedObjectId && removeObject(selectedObjectId)}
            >
              删除
            </Button>
          </Space.Compact>
          <Divider type="vertical" />
          <Text type="secondary">相机</Text>
          <Space.Compact>
            <Button size="small" onClick={handleAddCameraKeyframe}>
              记录相机（{cameraKeyframes.length}）
            </Button>
            {CAMERA_PRESET_LABELS.map((item) => (
              <Button key={item.value} size="small" onClick={() => handleCameraPreset(item.value)}>
                {item.label}
              </Button>
            ))}
          </Space.Compact>
        </Space>
      )}
      <Space wrap>
        <Text type="secondary">控制</Text>
        <Space.Compact>
          <Button size="small" onClick={() => setIsPlaying(!isPlaying)}>
            {isPlaying ? "暂停" : "播放"}
          </Button>
          <Button size="small" onClick={handleExport}>
            导出 JSON
          </Button>
          <Button size="small" onClick={() => fileInputRef.current?.click()}>
            导入 JSON
          </Button>
          {onSave && (
            <Button size="small" type="primary" onClick={() => onSave(exportScene())}>
              保存项目
            </Button>
          )}
        </Space.Compact>
      </Space>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        style={{ display: "none" }}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) handleImport(file);
          event.target.value = "";
        }}
      />
    </div>
  );
}
