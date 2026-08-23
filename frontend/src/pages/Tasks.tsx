import { useCallback, useEffect, useState } from "react";
import { Button, Card, Empty, List, Space, Tabs, Tag, Typography, message } from "antd";
import client from "../api/client";

const { Title, Text, Paragraph } = Typography;

interface TaskItem {
  id: number;
  uid: string;
  prompt: string;
  status: string;
  video_url: string | null;
  created_at: string;
}

const statusColor: Record<string, string> = {
  pending: "default",
  optimizing_prompt: "processing",
  generating_first_frame: "processing",
  generating_video: "processing",
  generating_audio: "processing",
  generating_subtitle: "processing",
  post_processing: "processing",
  quality_check: "processing",
  completed: "success",
  failed: "error",
  cancelled: "warning",
};

const statusText: Record<string, string> = {
  pending: "排队中",
  optimizing_prompt: "优化提示词",
  generating_first_frame: "生成首帧",
  generating_video: "生成视频",
  generating_audio: "生成配音",
  generating_subtitle: "生成字幕",
  post_processing: "后期处理",
  quality_check: "质量检查",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

export default function Tasks() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await client.get("/history");
      setTasks(response.data);
    } catch {
      message.error("加载任务失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, 5000);
    return () => window.clearInterval(timer);
  }, [load]);

  const handleDownload = async (taskUid: string) => {
    try {
      const response = await client.get(`/generate/${taskUid}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `task_${taskUid.slice(0, 8)}.mp4`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("下载失败");
    }
  };

  const handleCancel = async (taskUid: string) => {
    try {
      await client.post(`/generate/${taskUid}/cancel`);
      message.success("任务已取消");
      load();
    } catch {
      message.error("取消失败，请确认任务状态");
    }
  };

  const handleRetry = async (taskUid: string) => {
    try {
      await client.post(`/generate/${taskUid}/retry`);
      message.success("任务已重新提交");
      load();
    } catch {
      message.error("重试失败，请确认任务状态");
    }
  };

  const filteredTasks = tasks.filter((task) => {
    if (filter === "all") return true;
    if (filter === "running") {
      return ["pending", "optimizing_prompt", "generating_first_frame", "generating_video", "generating_audio", "generating_subtitle", "post_processing", "quality_check"].includes(task.status);
    }
    return task.status === filter;
  });

  const tabItems = [
    { key: "all", label: `全部 (${tasks.length})` },
    {
      key: "running",
      label: `进行中 (${tasks.filter((task) => ["pending", "optimizing_prompt", "generating_first_frame", "generating_video", "generating_audio", "generating_subtitle", "post_processing", "quality_check"].includes(task.status)).length})`,
    },
    { key: "completed", label: `已完成 (${tasks.filter((task) => task.status === "completed").length})` },
    { key: "failed", label: `失败 (${tasks.filter((task) => task.status === "failed").length})` },
    { key: "cancelled", label: `已取消 (${tasks.filter((task) => task.status === "cancelled").length})` },
  ];

  return (
    <div>
      <Title level={3}>任务中心</Title>
      <Button onClick={load} loading={loading} style={{ marginBottom: 16 }}>
        刷新
      </Button>
      <Card>
        <Tabs activeKey={filter} onChange={setFilter} items={tabItems} />
        {filteredTasks.length === 0 ? (
          <Empty description="暂无任务" />
        ) : (
          <List
            loading={loading}
            grid={{ gutter: 16, xs: 1, sm: 1, md: 2, lg: 2, xl: 3 }}
            dataSource={filteredTasks}
            renderItem={(task) => (
              <List.Item>
                <Card
                  size="small"
                  title={
                    <Space>
                      <Text strong>任务 #{task.id}</Text>
                      <Tag color={statusColor[task.status] ?? "default"}>
                        {statusText[task.status] ?? task.status}
                      </Tag>
                    </Space>
                  }
                  actions={[
                    ["pending", "optimizing_prompt", "generating_first_frame", "generating_video", "generating_audio", "generating_subtitle", "post_processing", "quality_check"].includes(task.status) ? (
                      <Button key="cancel" size="small" danger onClick={() => handleCancel(task.uid)}>
                        取消
                      </Button>
                    ) : null,
                    ["failed", "cancelled"].includes(task.status) ? (
                      <Button key="retry" size="small" onClick={() => handleRetry(task.uid)}>
                        重试
                      </Button>
                    ) : null,
                    task.video_url ? (
                      <Button key="download" size="small" onClick={() => handleDownload(task.uid)}>
                        下载
                      </Button>
                    ) : null,
                  ].filter(Boolean)}
                >
                  <Paragraph ellipsis={{ rows: 2 }} style={{ minHeight: 44, marginBottom: 8 }}>
                    {task.prompt}
                  </Paragraph>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {new Date(task.created_at).toLocaleString()}
                  </Text>
                </Card>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
