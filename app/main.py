"""
Main entry point for the GitLab Backport Bot Service.
"""

import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.utils.logger import setup_logger, get_logger

# Setup logger before anything else
setup_logger()
logger = get_logger(__name__)


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan handler."""
        logger.info("🚀 Starting GitLab Backport Bot Service")
        logger.info(f"📡 GitLab URL: {settings.gitlab_url}")
        logger.info(f"🌐 Server: http://{settings.host}:{settings.port}")
        yield
        logger.info("🛑 Shutting down GitLab Backport Bot Service")
    
    app = FastAPI(
        title="GitLab Backport Bot Service",
        description="A webhook-based service for automated GitLab backport operations",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Include API routers
    from app.api.webhook import router as webhook_router
    from app.api.backport import router as backport_router
    from app.api.health import router as health_router
    
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(webhook_router, prefix="/webhook", tags=["Webhook"])
    app.include_router(backport_router, prefix="/api", tags=["Backport"])
    
    # Exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc),
                "type": type(exc).__name__
            }
        )
    
    return app


def main():
    """Main entry point."""
    settings = get_settings()
    
    # Validate required settings
    if not settings.gitlab_token or settings.gitlab_token == "your_gitlab_token_here":
        logger.error("❌ GITLAB_TOKEN is not configured!")
        logger.error("Please set GITLAB_TOKEN environment variable or edit .env file")
        sys.exit(1)
    
    # Start server
    uvicorn.run(
        "app.main:create_application",
        host=settings.host,
        port=settings.port,
        reload=False,
        factory=True,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
