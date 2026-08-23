import { useCallback, useEffect, useState } from "react";
import { Button, Card, Col, Descriptions, Empty, Input, Row, Space, Statistic, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import client from "../api/client";

const { Title, Text } = Typography;

interface CostSummary {
  total_cost: number;
  task_count: number;
  call_count: number;
}

interface CostItem {
  provider?: string;
  call_type?: string;
  model?: string;
  cost?: number;
  created_at?: string;
}

export default function Cost() {
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [taskId, setTaskId] = useState<number | undefined>();
  const [taskDetail, setTaskDetail] = useState<{ task_id?: number; total_cost?: number; items?: CostItem[] } | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setSummaryLoading(true);
    try {
      const response = await client.get("/cost/summary");
      setSummary(response.data);
    } catch {
      // 忽略
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleQueryTask = async () => {
    if (!taskId) return;
    setDetailLoading(true);
    try {
      const response = await client.get(`/cost/task/${taskId}`);
      setTaskDetail(response.data);
    } catch {
      setTaskDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const columns: ColumnsType<CostItem> = [
    { title: "Provider", dataIndex: "provider", key: "provider" },
    { title: "类型", dataIndex: "call_type", key: "call_type" },
    { title: "模型", dataIndex: "model", key: "model" },
    {
      title: "成本（元）",
      dataIndex: "cost",
      key: "cost",
      render: (value: number | undefined) => (value ?? 0).toFixed(4),
    },
    { title: "时间", dataIndex: "created_at", key: "created_at" },
  ];

  return (
    <div>
      <Title level={3}>成本中心</Title>
      <Card title="成本汇总" style={{ marginBottom: 16 }} loading={summaryLoading}>
        <Row gutter={16}>
          <Col xs={24} sm={8}>
            <Statistic title="总成本（元）" value={summary?.total_cost ?? 0} precision={2} />
          </Col>
          <Col xs={24} sm={8}>
            <Statistic title="任务数" value={summary?.task_count ?? 0} />
          </Col>
          <Col xs={24} sm={8}>
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
            style={{ width: 200 }}
          />
          <Button onClick={handleQueryTask} loading={detailLoading}>
            查询
          </Button>
        </Space>
        {taskDetail ? (
          <div style={{ marginTop: 16 }}>
            <Descriptions column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="任务 ID">{taskDetail.task_id ?? ""}</Descriptions.Item>
              <Descriptions.Item label="总成本">{taskDetail.total_cost ?? 0} 元</Descriptions.Item>
            </Descriptions>
            {taskDetail.items && taskDetail.items.length > 0 ? (
              <Table
                rowKey={(_, index) => String(index ?? 0)}
                columns={columns}
                dataSource={taskDetail.items}
                pagination={false}
                size="small"
              />
            ) : (
              <Empty description="暂无明细" />
            )}
          </div>
        ) : (
          <Text type="secondary" style={{ display: "block", marginTop: 16 }}>
            输入任务 ID 查询成本明细
          </Text>
        )}
      </Card>
    </div>
  );
}
