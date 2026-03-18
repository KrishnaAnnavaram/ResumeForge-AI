"""CareerOS FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from careeros.config import get_settings
from careeros.core.logging import configure_logging, get_logger
from careeros.core.exceptions import (
    CareerOSError, VaultTooThinError, JDParseError,
    AuthenticationError, AuthorizationError, LanguageNotSupportedError,
    SessionNotFoundError, MaxIterationsError,
)
from careeros.api.router import api_router

settings = get_settings()
configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("careeros.startup", env=settings.app_env, version="1.0.0")
    yield
    log.info("careeros.shutdown")


app = FastAPI(
    title="CareerOS API",
    description="Production-Grade AI Career Operating System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API router
app.include_router(api_router)


# Global exception handlers
@app.exception_handler(VaultTooThinError)
async def vault_too_thin_handler(request: Request, exc: VaultTooThinError):
    return JSONResponse(
        status_code=422,
        content={"error": "VAULT_TOO_THIN", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(JDParseError)
async def jd_parse_error_handler(request: Request, exc: JDParseError):
    return JSONResponse(
        status_code=422,
        content={"error": "JD_PARSE_ERROR", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={"error": "AUTHENTICATION_ERROR", "message": exc.message, "details": {}},
    )


@app.exception_handler(LanguageNotSupportedError)
async def language_error_handler(request: Request, exc: LanguageNotSupportedError):
    return JSONResponse(
        status_code=422,
        content={"error": "LANGUAGE_NOT_SUPPORTED", "message": exc.message, "details": {}},
    )


@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "SESSION_NOT_FOUND", "message": exc.message, "details": {}},
    )


@app.exception_handler(CareerOSError)
async def careeros_error_handler(request: Request, exc: CareerOSError):
    return JSONResponse(
        status_code=500,
        content={"error": "CAREEROS_ERROR", "message": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", error=str(exc), error_type=type(exc).__name__, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": {}},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "env": settings.app_env}
