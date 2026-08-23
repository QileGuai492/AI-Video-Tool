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
  const [userForm] = Form.useForm<{ username: string; email?: string; password?: string }>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [userLoading, setUserLoading] = useState(false);
  const [userSaving, setUserSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setUserLoading(true);
    try {
      const [userResponse, settingsResponse] = await Promise.all([
        client.get("/auth/me"),
        client.get("/settings"),
      ]);
      userForm.setFieldsValue({
        username: userResponse.data.username,
        email: userResponse.data.email ?? "",
      });
      form.setFieldsValue(settingsResponse.data);
    } catch {
      message.error("加载设置失败");
    } finally {
      setLoading(false);
      setUserLoading(false);
    }
  }, [form, userForm]);

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

  const handleSaveUser = async (values: { username: string; email?: string; password?: string }) => {
    setUserSaving(true);
    try {
      const payload: { email?: string; password?: string } = {};
      if (values.email !== undefined) payload.email = values.email;
      if (values.password) payload.password = values.password;
      await client.put("/auth/me", payload);
      message.success("用户信息已保存");
      userForm.setFieldsValue({ password: "" });
    } catch {
      message.error("保存用户信息失败");
    } finally {
      setUserSaving(false);
    }
  };

  return (
    <div>
      <Title level={3}>设置</Title>
      <Card title="用户信息" loading={userLoading} style={{ maxWidth: 560, marginBottom: 16 }}>
        <Form form={userForm} layout="vertical" onFinish={handleSaveUser}>
          <Form.Item name="username" label="用户名">
            <Input disabled />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[{ type: "email", message: "请输入正确的邮箱格式" }]}
          >
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item
            name="password"
            label="新密码（留空则不修改）"
            rules={[
              { min: 8, message: "密码至少 8 位" },
              { pattern: /^(?=.*[A-Za-z])(?=.*\d).+$/, message: "密码必须包含字母和数字" },
            ]}
          >
            <Input.Password placeholder="请输入新密码" />
          </Form.Item>
          <Form.Item
            name="confirmPassword"
            label="确认新密码"
            dependencies={["password"]}
            rules={[
              ({ getFieldValue }) => ({
                validator(_, value) {
                  const password = getFieldValue("password");
                  if (!password || !value || password === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error("两次输入的密码不一致"));
                },
              }),
            ]}
          >
            <Input.Password placeholder="请再次输入新密码" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={userSaving}>
            保存用户信息
          </Button>
        </Form>
      </Card>
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
