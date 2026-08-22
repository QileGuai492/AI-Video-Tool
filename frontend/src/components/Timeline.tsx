import { Button, InputNumber, Slider, Space, Tag, Typography } from "antd";
import { usePrevisStore } from "../previs/store";

const { Text } = Typography;

export default function Timeline() {
  const currentTime = usePrevisStore((state) => state.currentTime);
  const duration = usePrevisStore((state) => state.duration);
  const shotMarkers = usePrevisStore((state) => state.shotMarkers);
  const setCurrentTime = usePrevisStore((state) => state.setCurrentTime);
  const setDuration = usePrevisStore((state) => state.setDuration);
  const addShotMarker = usePrevisStore((state) => state.addShotMarker);
  const removeShotMarker = usePrevisStore((state) => state.removeShotMarker);
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const keyframes = usePrevisStore((state) => state.keyframes);
  const cameraKeyframes = usePrevisStore((state) => state.cameraKeyframes);

  const selectedKeyframes = selectedObjectId ? (keyframes[selectedObjectId] ?? []) : [];

  return (
    <div style={{ marginTop: 16 }}>
      <Space style={{ width: "100%" }} direction="vertical">
        <Space wrap>
          <Text>时间：{currentTime.toFixed(1)}s</Text>
          <Text>时长：</Text>
          <InputNumber
            min={1}
            max={60}
            value={duration}
            onChange={(value) => setDuration(value ?? 5)}
            addonAfter="s"
          />
          <Button size="small" onClick={() => addShotMarker(currentTime)}>
            添加镜头切点
          </Button>
          {selectedObjectId && <Text>选中对象关键帧：{selectedKeyframes.length}</Text>}
          <Text>相机关键帧：{cameraKeyframes.length}</Text>
        </Space>
        <Space wrap>
          <Text>镜头切点：</Text>
          {shotMarkers.length === 0 ? (
            <Text type="secondary">暂无</Text>
          ) : (
            shotMarkers.map((marker) => (
              <Tag
                key={marker}
                closable
                onClose={(event) => {
                  event.preventDefault();
                  removeShotMarker(marker);
                }}
              >
                {marker.toFixed(1)}s
              </Tag>
            ))
          )}
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
