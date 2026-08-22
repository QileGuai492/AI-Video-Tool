import { Button, Card, Form, Input, Tabs, Typography, message } from "antd";
import { useAuthStore } from "../stores/authStore";

const { Title } = Typography;

export default function Login() {
  const login = useAuthStore((state) => state.login);
  const register = useAuthStore((state) => state.register);

  const handleLogin = async (values: { username: string; password: string }) => {
    try {
      await login(values.username, values.password);
      message.success("登录成功");
    } catch {
      message.error("登录失败，请检查用户名或密码");
    }
  };

  const handleRegister = async (values: { username: string; password: string; email?: string }) => {
    try {
      await register(values.username, values.password, values.email);
      message.success("注册成功");
    } catch {
      message.error("注册失败");
    }
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "80vh" }}>
      <Card style={{ width: 420 }}>
        <Title level={3} style={{ textAlign: "center" }}>
          AI 视频生成工具
        </Title>
        <Tabs
          items={[
            {
              key: "login",
              label: "登录",
              children: (
                <Form onFinish={handleLogin} layout="vertical">
                  <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true }]}>
                    <Input.Password />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block>
                    登录
                  </Button>
                </Form>
              ),
            },
            {
              key: "register",
              label: "注册",
              children: (
                <Form onFinish={handleRegister} layout="vertical">
                  <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
                    <Input.Password />
                  </Form.Item>
                  <Form.Item name="email" label="邮箱（选填）">
                    <Input />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block>
                    注册
                  </Button>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}
