"""监控指标接口集成测试。"""


def test_metrics_endpoint(client) -> None:
    """监控指标应返回基础运行数据。"""
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "users" in body
    assert "tasks" in body
    assert "generation_logs" in body
