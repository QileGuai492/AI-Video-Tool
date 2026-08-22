# 生产部署说明

## 快速启动

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env：数据库、Redis、SiliconFlow、OSS 等

# 2. 构建镜像
docker compose build

# 3. 启动基础环境
docker compose up -d

# 4. 执行数据库迁移
docker compose exec api alembic upgrade head
```

## HTTPS + 监控

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

包含：

- Nginx HTTPS
- Certbot 自动续期
- Prometheus（http://localhost:9090）
- Grafana（http://localhost:3001，默认 admin/admin）

## OSS 验证

```bash
python scripts/validate_oss.py
```

## 备份

手动：

```bash
./deploy/backup.sh /data/backups
```

定时任务参考：`deploy/backup.cron`

## 真实 SiliconFlow 验证

```bash
python scripts/validate_real_previs.py
```

注意：需要 SiliconFlow 账户有余额/权限，否则会返回 `402 Payment Required`。
