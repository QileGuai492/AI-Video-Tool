# 后端 / Worker 共用镜像
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120

# 安装 FFmpeg（视频拼接依赖）
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖清单，利用 Docker 缓存
COPY pyproject.toml README.md ./

# 复制应用代码
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

# 预先安装构建依赖，避免每次构建时下载
RUN pip install --no-cache-dir setuptools wheel

# 安装项目（禁用构建隔离，减少网络依赖）
RUN pip install --no-cache-dir --no-build-isolation .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
