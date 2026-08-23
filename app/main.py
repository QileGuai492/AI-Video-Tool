"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.models import (  # noqa: F401  确保模型注册到 Base.metadata
    AudioTrack,
    BgmLibrary,
    Character,
    CharacterMultiView,
    GenerationLog,
    PrevisProject,
    PrevisTemplate,
    Setting,
    TaskConfigSnapshot,
    TaskError,
    TaskRetry,
    Template,
    User,
    VideoSegment,
    VideoTask,
)
from app.services.previs_service import seed_builtin_previs_templates

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """本地开发自动建表；生产环境应使用 Alembic 迁移。"""
    setup_logging()
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
        seed_builtin_previs_templates(engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS：本地开发允许所有来源，生产环境需收紧
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """统一 HTTP 异常响应。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}},
    )


def _translate_validation_error(error: dict) -> str:
    """将 Pydantic 校验错误翻译为中文提示。"""
    error_type = error.get("type", "")
    context = error.get("ctx", {}) or {}
    location = ".".join(str(part) for part in error.get("loc", []))

    messages = {
        "missing": "缺少必填字段",
        "string_too_short": f"至少需要 {context.get('min_length', 1)} 个字符",
        "string_too_long": f"不能超过 {context.get('max_length', 999)} 个字符",
        "string_pattern_mismatch": "格式不正确",
        "int_parsing": "必须为整数",
        "int_type": "必须为整数",
        "float_parsing": "必须为数字",
        "float_type": "必须为数字",
        "bool_parsing": "必须为布尔值",
        "bool_type": "必须为布尔值",
        "value_error": "参数值不合法",
        "json_invalid": "JSON 格式不正确",
    }

    message = messages.get(error_type, error.get("msg", "参数错误"))
    return f"{location}: {message}" if location else message


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """统一参数校验错误响应。"""
    errors = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", []))
        errors.append(
            {
                "location": location,
                "message": _translate_validation_error(error),
                "type": error.get("type", ""),
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "参数校验失败",
            "details": errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """统一未捕获异常响应。"""
    return JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": "服务器内部错误", "details": {}},
    )


app.include_router(api_router)

# 本地上传文件访问（生产环境应由 Nginx / OSS 提供）
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
def health_check() -> dict:
    """健康检查。"""
    return {"status": "ok"}
