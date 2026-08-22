import { Card, Empty, Typography } from "antd";

const { Title } = Typography;

export default function Tasks() {
  return (
    <div>
      <Title level={3}>任务中心</Title>
      <Card>
        <Empty description="任务列表开发中，后续展示实时进度与批量聚合" />
      </Card>
    </div>
  );
}
