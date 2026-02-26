"""
Health check endpoints for monitoring and load balancers.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        JSON response with service status
    """
    return {
        "status": "healthy",
        "service": "gitlab-backport-bot",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness probe for Kubernetes.
    
    Checks if the service is ready to accept traffic.
    
    Returns:
        200 if ready, 503 if not ready
    """
    settings = get_settings()
    
    # Check required configuration
    if not settings.gitlab_token or settings.gitlab_token == "your_gitlab_token_here":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": "GITLAB_TOKEN not configured",
                "checks": {
                    "gitlab_token": "not_configured",
                    "webhook_secret": "configured" if settings.webhook_secret else "not_configured"
                }
            }
        )
    
    return {
        "status": "ready",
        "gitlab_url": settings.gitlab_url,
        "checks": {
            "gitlab_token": "configured",
            "webhook_secret": "configured" if settings.webhook_secret else "not_configured"
        }
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness probe for Kubernetes.
    
    Returns:
        200 if the service is alive, regardless of readiness
    """
    return {
        "status": "alive",
        "service": "gitlab-backport-bot"
    }
