"""成本接口集成测试。"""


def test_get_task_cost(client, auth_headers) -> None:
    """查询任务成本应返回明细。"""
    submit_response = client.post(
        "/api/v1/generate/video",
        headers=auth_headers,
        json={"prompt": "成本测试", "duration": 5, "aspect_ratio": "16:9"},
    )
    assert submit_response.status_code == 200
    task_id = submit_response.json()["id"]

    cost_response = client.get(
        f"/api/v1/cost/task/{task_id}",
        headers=auth_headers,
    )
    assert cost_response.status_code == 200
    data = cost_response.json()
    assert data["task_id"] == task_id
    assert "items" in data


def test_get_cost_summary(client, auth_headers) -> None:
    """成本汇总应返回总数。"""
    response = client.get("/api/v1/cost/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_cost" in data
    assert "task_count" in data
    assert "call_count" in data
