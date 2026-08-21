# 25 - 运维 Runbook

> 状态：待评审  
> 最近更新：2026-01-01  
> 所属文档库：[README](../README.md)

## 1. 目的

提供日常运维和故障排查的实操步骤，覆盖服务启停、日志、备份恢复、密钥轮换和常见问题。

## 2. 服务启停

### 2.1 本地

```bash
# 启动基础服务
docker compose up -d redis postgres

# 启动后端
uvicorn app.main:app --reload

# 启动 Worker
celery -A app.tasks.celery_app worker --loglevel=info

# 停止
# Ctrl+C 停止前端进程；docker compose down 停止容器
```

### 2.2 服务器（ECS）

```bash
# 查看服务状态
docker compose ps

# 启动全部服务
docker compose up -d

# 停止全部服务
docker compose down

# 重启某个服务
docker compose restart api
docker compose restart worker
```

## 3. 日志查看

```bash
# 后端日志
docker compose logs -f api

# Worker 日志
docker compose logs -f worker

# 按任务 ID 过滤
docker compose logs worker | grep "<task_id>"
```

## 4. 数据库备份与恢复

### 4.1 备份

```bash
# PostgreSQL 备份
docker compose exec postgres pg_dump -U ai_video ai_video > backup_$(date +%Y%m%d).sql
```

### 4.2 恢复

```bash
# 恢复
cat backup_20260101.sql | docker compose exec -T postgres psql -U ai_video ai_video
```

## 5. 密钥轮换

1. 在云控制台生成新 Key。
2. 更新服务器 `.env`。
3. 重启相关服务：`docker compose restart api worker`。
4. 在云控制台吊销旧 Key。
5. 更新 `docs/16-外部服务与Key状态.md`。

## 6. 常见问题排查

| 现象 | 可能原因 | 排查步骤 |
| --- | --- | --- |
| 任务一直 pending | Worker 没启动 / Redis 连不上 | 检查 `docker compose ps`、Worker 日志 |
| 外部 API 报 401 | Key 失效 / 未配置 | 检查 `.env`，测试 Key 是否可用 |
| 视频生成超时 | API 排队 / 参数过大 | 查看任务日志，确认超时时间 |
| 成本异常高 | 重试次数过多 / 模型选错 | 查看 `generation_logs` 和 `task_retries` |
| 上传文件失败 | OSS 权限 / 文件过大 | 检查 OSS 配置和文件大小限制 |
| 字幕乱码 | 字体缺失 / 编码问题 | 检查字幕字体文件和编码格式 |

## 7. 紧急处理

### 7.1 API Key 泄露

1. 立即在云控制台吊销 Key。
2. 更换 `.env` 中的 Key。
3. 重启服务。
4. 检查 Git 历史是否误提交，如已提交立即清除并轮换。

### 7.2 服务宕机

1. 查看 `docker compose ps`。
2. 查看日志定位原因。
3. 必要时重启服务。
4. 如果数据库损坏，从最近备份恢复。

### 7.3 成本异常

1. 暂停 Worker：`docker compose stop worker`。
2. 查看 `generation_logs` 定位高额调用。
3. 调整质量档位或 Provider 策略后恢复。

## 8. 定期维护

- [ ] 每周检查 API 免费额度 / 余额。
- [ ] 每周查看任务成功率。
- [ ] 每月检查数据库备份。
- [ ] 每月检查日志大小并清理。
- [ ] 每季度轮换一次敏感 Key。
