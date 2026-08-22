import { Card, Empty, Typography } from "antd";

const { Title } = Typography;

export default function Cost() {
  return (
    <div>
      <Title level={3}>成本中心</Title>
      <Card>
        <Empty description="成本中心开发中，后续展示余额、明细与趋势" />
      </Card>
    </div>
  );
}
