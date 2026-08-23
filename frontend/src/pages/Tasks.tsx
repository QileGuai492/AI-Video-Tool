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

  const handleCancel = async (taskId: number) => {
    try {
      await client.post(`/generate/${taskId}/cancel`);
      message.success(`任务 #${taskId} 已取消`);
      load();
    } catch {
      message.error("取消失败，请确认任务状态");
    }
  };

  const handleRetry = async (taskId: number) => {
    try {
      await client.post(`/generate/${taskId}/retry`);
      message.success(`任务 #${taskId} 已重新提交`);
      load();
    } catch {
      message.error("重试失败，请确认任务状态");
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
                  ["pending", "optimizing_prompt", "generating_first_frame", "generating_video", "generating_audio", "generating_subtitle", "post_processing", "quality_check"].includes(task.status) ? (
                    <Button size="small" danger onClick={() => handleCancel(task.id)}>
                      取消
                    </Button>
                  ) : null,
                  ["failed", "cancelled"].includes(task.status) ? (
                    <Button size="small" onClick={() => handleRetry(task.id)}>
                      重试
                    </Button>
                  ) : null,
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
                <Tag color={statusColor[task.status] ?? "default"}>
                  {statusText[task.status] ?? task.status}
                </Tag>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
