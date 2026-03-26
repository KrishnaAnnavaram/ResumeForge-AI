"""
main.py — FastAPI application entrypoint.

Startup sequence:
  1. Validate config (fail-fast on missing env vars)
  2. Init Supabase async client
  3. Init MCP registry
  4. Compile LangGraph
  5. Register middleware (CORS, Security, Logging)
  6. Register routes
  7. Register global exception handler

Never import API keys directly — always use get_settings().
"""

import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase._async.client import create_client

from backend.agents.graph import build_graph
from backend.api.routes import router
from backend.core.config import get_settings
from backend.core.exceptions import AppError
from backend.core.logger import get_logger
from backend.middleware.logging_middleware import RequestLoggingMiddleware
from backend.middleware.security_middleware import SecurityHeadersMiddleware
from backend.mcp_servers.mcp_registry import MCPRegistry

logger = get_logger(__name__)
settings = get_settings()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared resources on startup; clean up on shutdown."""
    logger.info(
        "ResumeForge AI starting up",
        environment=settings.environment,
        backend_url=str(settings.backend_url),
    )

    # 1. Supabase async client (service role — never exposed to frontend)
    supabase = await create_client(
        str(settings.supabase_url),
        settings.supabase_service_role_key,
    )
    app.state.supabase = supabase
    logger.info("Supabase client initialised")

    # 2. MCP registry
    mcp = MCPRegistry(supabase)
    app.state.mcp = mcp
    logger.info("MCP registry initialised")

    # 3. LangGraph — compile once and cache
    graph_app = await build_graph(mcp)
    app.state.graph = graph_app
    logger.info("LangGraph compiled and ready")

    yield  # ← app is running

    # Shutdown
    logger.info("ResumeForge AI shutting down")
    try:
        await supabase.auth.sign_out()
    except Exception:
        pass


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="ResumeForge AI",
        version="1.0.0",
        description="Multi-LLM ATS-optimised resume generation API",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── Middleware stack (outermost → innermost) ──────────────────────────
    # Note: Starlette applies middleware in reverse-addition order, so
    # the last added is the outermost wrapper.

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # ── Routes ────────────────────────────────────────────────────────────
    app.include_router(router)

    # ── Health / metrics endpoints ────────────────────────────────────────
    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.get("/metrics", tags=["ops"])
    async def metrics():
        """Basic metrics — extend with Prometheus in production."""
        return {
            "status": "ok",
            "environment": settings.environment,
        }

    # ── Global exception handler ──────────────────────────────────────────
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "AppError",
            status=exc.http_status,
            code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_config=None,  # Use our custom JSON logger
        workers=1 if settings.is_development else 4,
    )
