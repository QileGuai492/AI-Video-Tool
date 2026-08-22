import { useCallback, useEffect, useState } from "react";
import { Button, Card, List, Space, Tag, Typography, message } from "antd";
import client from "../api/client";

const { Title, Text } = Typography;

interface TaskItem {
  id: number;
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

export default function Tasks() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(false);

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

  const handleDownload = async (taskId: number) => {
    try {
      const response = await client.get(`/generate/${taskId}/download`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `task_${taskId}.mp4`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("下载失败");
    }
  };

  return (
    <div>
      <Title level={3}>任务中心</Title>
      <Button onClick={load} loading={loading} style={{ marginBottom: 16 }}>
        刷新
      </Button>
      <Card>
        {tasks.length === 0 ? (
          <Text type="secondary">暂无任务</Text>
        ) : (
          <List
            dataSource={tasks}
            renderItem={(task) => (
              <List.Item
                actions={[
                  task.video_url ? (
                    <Button size="small" onClick={() => handleDownload(task.id)}>
                      下载
                    </Button>
                  ) : null,
                ]}
              >
                <List.Item.Meta
                  title={`任务 #${task.id}`}
                  description={
                    <Space direction="vertical">
                      <Text>{task.prompt}</Text>
                      <Text type="secondary">{new Date(task.created_at).toLocaleString()}</Text>
                    </Space>
                  }
                />
                <Tag color={statusColor[task.status] ?? "default"}>{task.status}</Tag>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
