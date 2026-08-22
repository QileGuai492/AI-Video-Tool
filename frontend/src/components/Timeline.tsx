import { InputNumber, Slider, Space, Typography } from "antd";
import { usePrevisStore } from "../previs/store";

const { Text } = Typography;

export default function Timeline() {
  const currentTime = usePrevisStore((state) => state.currentTime);
  const duration = usePrevisStore((state) => state.duration);
  const setCurrentTime = usePrevisStore((state) => state.setCurrentTime);
  const setDuration = usePrevisStore((state) => state.setDuration);
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const keyframes = usePrevisStore((state) => state.keyframes);

  const selectedKeyframes = selectedObjectId ? (keyframes[selectedObjectId] ?? []) : [];

  return (
    <div style={{ marginTop: 16 }}>
      <Space style={{ width: "100%" }} direction="vertical">
        <Space>
          <Text>时间：{currentTime.toFixed(1)}s</Text>
          <Text>时长：</Text>
          <InputNumber
            min={1}
            max={60}
            value={duration}
            onChange={(value) => setDuration(value ?? 5)}
            addonAfter="s"
          />
          {selectedObjectId && <Text>选中对象关键帧：{selectedKeyframes.length}</Text>}
        </Space>
        <Slider
          min={0}
          max={duration}
          step={0.1}
          value={currentTime}
          onChange={(value) => setCurrentTime(value)}
        />
      </Space>
    </div>
  );
}
