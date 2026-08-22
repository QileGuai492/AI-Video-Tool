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


def test_prometheus_metrics_endpoint(client) -> None:
    """Prometheus 指标接口应返回文本格式。"""
    response = client.get("/api/v1/metrics/prometheus")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "ai_video_users" in response.text
    assert "ai_video_tasks_total" in response.text
