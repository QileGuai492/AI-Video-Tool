import { useCallback, useEffect, useState } from "react";
import { Button, Card, Col, Empty, Row, Space, Tag, Typography, message } from "antd";
import client from "../api/client";

const { Title, Paragraph, Text } = Typography;

interface TemplateItem {
  id: number;
  name: string;
  config_json: Record<string, unknown>;
  is_builtin: boolean;
  created_at: string;
}

export default function Templates() {
  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await client.get("/templates");
      setTemplates(response.data);
    } catch {
      message.error("加载模板失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleFork = async (templateId: number) => {
    try {
      await client.post(`/templates/${templateId}/fork`);
      message.success("模板已复制到我的模板");
      load();
    } catch {
      message.error("复制模板失败");
    }
  };

  const handleDelete = async (templateId: number) => {
    if (!window.confirm("确定删除该模板？")) return;
    try {
      await client.delete(`/templates/${templateId}`);
      message.success("模板已删除");
      load();
    } catch {
      message.error("删除模板失败");
    }
  };

  return (
    <div>
      <Title level={3}>模板市场</Title>
      <Button onClick={load} loading={loading} style={{ marginBottom: 16 }}>
        刷新
      </Button>
      {templates.length === 0 ? (
        <Card>
          <Empty description="暂无模板" />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {templates.map((template) => (
            <Col key={template.id} xs={24} sm={12} md={8}>
              <Card
                title={template.name}
                extra={
                  template.is_builtin ? <Tag color="blue">内置</Tag> : <Tag>我的</Tag>
                }
              >
                <Paragraph type="secondary" ellipsis={{ rows: 3 }}>
                  {JSON.stringify(template.config_json)}
                </Paragraph>
                <Space>
                  <Text type="secondary">
                    {new Date(template.created_at).toLocaleDateString()}
                  </Text>
                  <Button size="small" onClick={() => handleFork(template.id)}>
                    复制
                  </Button>
                  {!template.is_builtin ? (
                    <Button size="small" danger onClick={() => handleDelete(template.id)}>
                      删除
                    </Button>
                  ) : null}
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}
