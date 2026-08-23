import { useCallback, useEffect, useState } from "react";
import {
  Avatar,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import client from "../api/client";

const { Title, Text } = Typography;

interface SettingsData {
  default_aspect_ratio?: string | null;
  default_quality?: string | null;
  default_model?: string | null;
  cost_limit?: number | null;
}

interface UserMeta {
  id?: number;
  createdAt?: string;
}

export default function Settings() {
  const [form] = Form.useForm<SettingsData>();
  const [userForm] = Form.useForm<{ username: string; email?: string; password?: string }>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [userLoading, setUserLoading] = useState(false);
  const [userSaving, setUserSaving] = useState(false);
  const [userMeta, setUserMeta] = useState<UserMeta>({});

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
      setUserMeta({
        id: userResponse.data.id,
        createdAt: userResponse.data.created_at,
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

  const watchedUsername = Form.useWatch("username", userForm) as string | undefined;
  const username = watchedUsername;
  const avatarText = username?.slice(0, 1).toUpperCase() || "U";

  return (
    <div>
      <Title level={3}>设置</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="用户信息" loading={userLoading}>
            <Space align="center" style={{ marginBottom: 16 }}>
              <Avatar size={48} style={{ backgroundColor: "#1677ff" }}>
                {avatarText}
              </Avatar>
              <Space direction="vertical" size={0}>
                <Text strong>{username || "未登录"}</Text>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {userMeta.id ? `用户 ID：${userMeta.id}` : ""}
                  {userMeta.createdAt
                    ? ` ｜ 注册时间：${new Date(userMeta.createdAt).toLocaleDateString()}`
                    : ""}
                </Text>
              </Space>
            </Space>
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
              <Text type="secondary" style={{ display: "block", marginBottom: 12, fontSize: 12 }}>
                密码要求：至少 8 位，且包含字母和数字。
              </Text>
              <Button type="primary" htmlType="submit" loading={userSaving}>
                保存用户信息
              </Button>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="生成默认设置" loading={loading}>
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
                    { value: "fast", label: <Space><Tag color="blue">快速</Tag> 适合预览</Space> },
                    { value: "standard", label: <Space><Tag color="green">标准</Tag> 推荐</Space> },
                    { value: "high", label: <Space><Tag color="orange">高质量</Tag> 更精细</Space> },
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
        </Col>
      </Row>
    </div>
  );
}
