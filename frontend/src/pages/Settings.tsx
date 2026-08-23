import { useCallback, useEffect, useState } from "react";
import { Button, Card, Form, Input, InputNumber, Select, Typography, message } from "antd";
import client from "../api/client";

const { Title } = Typography;

interface SettingsData {
  default_aspect_ratio?: string | null;
  default_quality?: string | null;
  default_model?: string | null;
  cost_limit?: number | null;
}

export default function Settings() {
  const [form] = Form.useForm<SettingsData>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await client.get("/settings");
      form.setFieldsValue(response.data);
    } catch {
      message.error("加载设置失败");
    } finally {
      setLoading(false);
    }
  }, [form]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async (values: SettingsData) => {
    setSaving(true);
    try {
      await client.put("/settings", values);
      message.success("设置已保存");
    } catch {
      message.error("保存设置失败");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Title level={3}>设置</Title>
      <Card loading={loading} style={{ maxWidth: 560 }}>
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="default_aspect_ratio" label="默认视频比例">
            <Select
              allowClear
              placeholder="选择默认比例"
              options={[
                { value: "16:9", label: "16:9 横屏" },
                { value: "9:16", label: "9:16 竖屏" },
                { value: "1:1", label: "1:1 方形" },
              ]}
            />
          </Form.Item>
          <Form.Item name="default_quality" label="默认质量档位">
            <Select
              allowClear
              placeholder="选择默认质量"
              options={[
                { value: "fast", label: "快速" },
                { value: "standard", label: "标准" },
                { value: "high", label: "高质量" },
              ]}
            />
          </Form.Item>
          <Form.Item name="default_model" label="默认模型">
            <Input placeholder="例如 agnes-video-v2.0" />
          </Form.Item>
          <Form.Item name="cost_limit" label="单次成本上限">
            <InputNumber min={0} max={100000} style={{ width: "100%" }} placeholder="例如 50" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saving}>
            保存设置
          </Button>
        </Form>
      </Card>
    </div>
  );
}
