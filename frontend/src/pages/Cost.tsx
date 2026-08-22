import { useCallback, useEffect, useState } from "react";
import { Button, Card, Col, Descriptions, Input, Row, Space, Statistic, message } from "antd";
import client from "../api/client";

interface CostSummary {
  total_cost: number;
  task_count: number;
  call_count: number;
}

export default function Cost() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [taskId, setTaskId] = useState<number | undefined>();
  const [taskDetail, setTaskDetail] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await client.get("/cost/summary");
      setSummary(response.data);
    } catch {
      // 忽略
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleQueryTask = async () => {
    if (!taskId) return;
    try {
      const response = await client.get(`/cost/task/${taskId}`);
      setTaskDetail(response.data);
    } catch {
      setTaskDetail(null);
    }
  };

  return (
    <div>
      <Card title="成本汇总" style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={8}>
            <Statistic title="总成本（元）" value={summary?.total_cost ?? 0} precision={2} />
          </Col>
          <Col span={8}>
            <Statistic title="任务数" value={summary?.task_count ?? 0} />
          </Col>
          <Col span={8}>
            <Statistic title="调用次数" value={summary?.call_count ?? 0} />
          </Col>
        </Row>
      </Card>
      <Card title="任务成本明细">
        <Space>
          <Input
            type="number"
            placeholder="任务 ID"
            value={taskId}
            onChange={(event) => setTaskId(Number(event.target.value))}
          />
          <Button onClick={handleQueryTask}>查询</Button>
        </Space>
        {taskDetail && (
          <Descriptions column={1} style={{ marginTop: 16 }}>
            <Descriptions.Item label="任务 ID">
              {(taskDetail as { task_id?: number }).task_id}
            </Descriptions.Item>
            <Descriptions.Item label="总成本">
              {(taskDetail as { total_cost?: number }).total_cost} 元
            </Descriptions.Item>
            <Descriptions.Item label="明细">
              <pre>{JSON.stringify((taskDetail as { items?: unknown }).items ?? [], null, 2)}</pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>
    </div>
  );
}
