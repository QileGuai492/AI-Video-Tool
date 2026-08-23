import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Button, Layout, Menu, Space } from "antd";
import Login from "./pages/Login";
import Workbench from "./pages/Workbench";
import Tasks from "./pages/Tasks";
import Templates from "./pages/Templates";
import Cost from "./pages/Cost";
import Characters from "./pages/Characters";
import Settings from "./pages/Settings";
import { useAuthStore } from "./stores/authStore";

const { Header, Content } = Layout;

export default function App() {
  const token = useAuthStore((state) => state.token);
  const username = useAuthStore((state) => state.username);
  const logout = useAuthStore((state) => state.logout);

  if (!token) {
    return (
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
  }

  return (
    <BrowserRouter>
      <Layout style={{ minHeight: "100vh" }}>
        <Header style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center" }}>
            <div style={{ color: "#fff", fontSize: 18, marginRight: 32 }}>AI 视频生成工具</div>
            <Menu
              theme="dark"
              mode="horizontal"
              defaultSelectedKeys={["workbench"]}
              items={[
                { key: "workbench", label: <Link to="/">工作台</Link> },
                { key: "characters", label: <Link to="/characters">角色库</Link> },
                { key: "tasks", label: <Link to="/tasks">任务中心</Link> },
                { key: "templates", label: <Link to="/templates">模板市场</Link> },
                { key: "cost", label: <Link to="/cost">成本中心</Link> },
                { key: "settings", label: <Link to="/settings">设置</Link> },
              ]}
            />
          </div>
          <Space>
            <span style={{ color: "#fff" }}>{username}</span>
            <Button size="small" onClick={logout}>
              退出
            </Button>
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<Workbench />} />
            <Route path="/characters" element={<Characters />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/cost" element={<Cost />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
      </Layout>
    </BrowserRouter>
  );
}
