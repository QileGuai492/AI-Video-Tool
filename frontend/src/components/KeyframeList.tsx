import { Button, Card, List, Space, Typography } from "antd";
import { usePrevisStore } from "../previs/store";

const { Text } = Typography;

export default function KeyframeList() {
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const keyframes = usePrevisStore((state) => state.keyframes);
  const removeKeyframe = usePrevisStore((state) => state.removeKeyframe);

  const list = selectedObjectId ? (keyframes[selectedObjectId] ?? []) : [];

  return (
    <Card title="关键帧列表" size="small">
      {!selectedObjectId || list.length === 0 ? (
        <Text type="secondary">暂无关键帧</Text>
      ) : (
        <List
          size="small"
          dataSource={list}
          renderItem={(frame) => (
            <List.Item
              actions={[
                <Button
                  key="delete"
                  size="small"
                  danger
                  onClick={() => selectedObjectId && removeKeyframe(selectedObjectId, frame.time)}
                >
                  删除
                </Button>,
              ]}
            >
              <Space>
                <Text>{frame.time.toFixed(1)}s</Text>
                <Text type="secondary">
                  P({frame.position.map((v) => v.toFixed(1)).join(",")})
                </Text>
              </Space>
            </List.Item>
          )}
        />
      )}
    </Card>
  );
}
