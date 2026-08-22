import { Card, Empty, Typography } from "antd";

const { Title } = Typography;

export default function Templates() {
  return (
    <div>
      <Title level={3}>模板市场</Title>
      <Card>
        <Empty description="模板市场开发中，后续展示白模模板与复制功能" />
      </Card>
    </div>
  );
}
