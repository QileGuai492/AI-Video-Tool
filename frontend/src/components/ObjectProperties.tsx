import { Card, InputNumber, Space, Typography } from "antd";
import { usePrevisStore } from "../previs/store";
import type { Vec3 } from "../previs/types";

const { Text } = Typography;

function VectorInputs({
  label,
  value,
  onChange,
}: {
  label: string;
  value: Vec3;
  onChange: (next: Vec3) => void;
}) {
  return (
    <Space>
      <Text>{label}</Text>
      <InputNumber
        size="small"
        value={value[0]}
        onChange={(v) => onChange([v ?? 0, value[1], value[2]])}
      />
      <InputNumber
        size="small"
        value={value[1]}
        onChange={(v) => onChange([value[0], v ?? 0, value[2]])}
      />
      <InputNumber
        size="small"
        value={value[2]}
        onChange={(v) => onChange([value[0], value[1], v ?? 0])}
      />
    </Space>
  );
}

export default function ObjectProperties() {
  const objects = usePrevisStore((state) => state.objects);
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const updateObject = usePrevisStore((state) => state.updateObject);

  const object = objects.find((item) => item.id === selectedObjectId);

  if (!object) {
    return (
      <Card title="对象属性" size="small">
        <Text type="secondary">请先选择一个对象</Text>
      </Card>
    );
  }

  return (
    <Card title={`对象属性：${object.name}`} size="small">
      <Space direction="vertical" style={{ width: "100%" }}>
        <VectorInputs
          label="位置"
          value={object.position}
          onChange={(position) => updateObject(object.id, { position })}
        />
        <VectorInputs
          label="旋转"
          value={object.rotation}
          onChange={(rotation) => updateObject(object.id, { rotation })}
        />
        <VectorInputs
          label="缩放"
          value={object.scale}
          onChange={(scale) => updateObject(object.id, { scale })}
        />
      </Space>
    </Card>
  );
}
