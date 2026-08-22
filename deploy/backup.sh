#!/usr/bin/env bash
# 数据库与上传文件备份脚本
# 用法：./deploy/backup.sh /path/to/backup/dir

set -euo pipefail

BACKUP_DIR="${1:-./backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "备份 PostgreSQL 数据库..."
docker compose exec -T postgres pg_dump -U ai_video ai_video > "$BACKUP_DIR/ai_video_$TIMESTAMP.sql"

echo "备份上传文件..."
tar -czf "$BACKUP_DIR/uploads_$TIMESTAMP.tar.gz" uploads 2>/dev/null || true

echo "备份完成：$BACKUP_DIR"
