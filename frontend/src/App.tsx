import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { Layout, Menu } from "antd";
import Workbench from "./pages/Workbench";
import Tasks from "./pages/Tasks";
import Templates from "./pages/Templates";
import Cost from "./pages/Cost";

const { Header, Content } = Layout;

export default function App() {
  return (
    <BrowserRouter>
      <Layout style={{ minHeight: "100vh" }}>
        <Header style={{ display: "flex", alignItems: "center" }}>
          <div style={{ color: "#fff", fontSize: 18, marginRight: 32 }}>
            AI 视频生成工具
          </div>
          <Menu
            theme="dark"
            mode="horizontal"
            defaultSelectedKeys={["workbench"]}
            items={[
              { key: "workbench", label: <Link to="/">工作台</Link> },
              { key: "tasks", label: <Link to="/tasks">任务中心</Link> },
              { key: "templates", label: <Link to="/templates">模板市场</Link> },
              { key: "cost", label: <Link to="/cost">成本中心</Link> },
            ]}
          />
        </Header>
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<Workbench />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/cost" element={<Cost />} />
          </Routes>
        </Content>
      </Layout>
    </BrowserRouter>
  );
}
