import { Button, Card, Col, Input, Row, Select, Space, Typography } from "antd";
import PrevisCanvas from "../components/PrevisCanvas";

const { Title, Paragraph } = Typography;

export default function Workbench() {
  return (
    <div>
      <Title level={3}>创作工作台</Title>
      <Paragraph>第一版重点：自由建模 + 关键帧动画，后续接入白模生成与 AI 成片。</Paragraph>
      <Row gutter={16}>
        <Col span={10}>
          <Card title="文案与参数">
            <Input.TextArea rows={4} placeholder="输入创意文案" />
            <Space direction="vertical" style={{ width: "100%", marginTop: 16 }}>
              <Select
                placeholder="画面比例"
                defaultValue="16:9"
                options={[
                  { value: "16:9", label: "16:9" },
                  { value: "9:16", label: "9:16" },
                  { value: "1:1", label: "1:1" },
                ]}
              />
              <Button type="primary" block>
                提交生成
              </Button>
            </Space>
          </Card>
        </Col>
        <Col span={14}>
          <Card title="3D 白模编辑器">
            <PrevisCanvas />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
