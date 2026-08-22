import { Button, Space, Typography } from "antd";
import { cameraRef } from "../previs/cameraRef";
import { usePrevisStore } from "../previs/store";
import type { ObjectType } from "../previs/types";

const { Text } = Typography;

export default function EditorToolbar({ onSave }: { onSave?: (scene: unknown) => void }) {
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const currentTime = usePrevisStore((state) => state.currentTime);
  const isPlaying = usePrevisStore((state) => state.isPlaying);
  const addObject = usePrevisStore((state) => state.addObject);
  const addKeyframe = usePrevisStore((state) => state.addKeyframe);
  const addCameraKeyframe = usePrevisStore((state) => state.addCameraKeyframe);
  const setIsPlaying = usePrevisStore((state) => state.setIsPlaying);
  const exportScene = usePrevisStore((state) => state.exportScene);

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

  return (
    <Space wrap style={{ marginBottom: 16 }}>
      <Text strong>添加对象：</Text>
      {objectTypes.map((item) => (
        <Button key={item.type} onClick={() => addObject(item.type)}>
          {item.label}
        </Button>
      ))}
      <Button
        type="primary"
        disabled={!selectedObjectId}
        onClick={() => selectedObjectId && addKeyframe(selectedObjectId, currentTime)}
      >
        记录关键帧
      </Button>
      <Button onClick={() => addCameraKeyframe(currentTime, cameraRef.position, cameraRef.target)}>
        记录相机
      </Button>
      <Button onClick={() => setIsPlaying(!isPlaying)}>{isPlaying ? "暂停" : "播放"}</Button>
      <Button onClick={handleExport}>导出 JSON</Button>
      {onSave && <Button onClick={() => onSave(exportScene())}>保存项目</Button>}
    </Space>
  );
}
