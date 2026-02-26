"""
Webhook handling endpoints for GitLab events.
"""

import json
from typing import Optional

from fastapi import APIRouter, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.utils.logger import get_logger
from app.utils.helpers import verify_webhook_signature, mask_sensitive_data
from app.services.webhook_service import WebhookService

router = APIRouter()
logger = get_logger(__name__)


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: Optional[str] = Header(None, alias="X-Gitlab-Token"),
    x_gitlab_event: Optional[str] = Header(None, alias="X-Gitlab-Event"),
    x_gitlab_instance: Optional[str] = Header(None, alias="X-Gitlab-Instance"),
):
    """
    Receive and process GitLab webhook events.
    
    Supports:
    - Merge Request events
    - Push events
    - Pipeline events
    
    Headers:
    - X-Gitlab-Token: Webhook secret token
    - X-Gitlab-Event: Event type (Merge Request Hook, Push Hook, etc.)
    
    Returns:
        JSON response with processing result
    """
    settings = get_settings()
    
    # Read raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature if secret is configured
    if not verify_webhook_signature(body, x_gitlab_token, settings.webhook_secret or ""):
        logger.warning("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse JSON body
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Log masked payload for debugging
    masked_payload = mask_sensitive_data(payload)
    logger.debug(f"Received webhook: {x_gitlab_event}", payload=masked_payload)
    
    # Process webhook based on event type
    event_type = x_gitlab_event or payload.get("object_kind", "unknown")
    
    try:
        webhook_service = WebhookService()
        
        if event_type == "merge_request" or event_type == "Merge Request Hook":
            result = await webhook_service.handle_merge_request_event(payload)
        elif event_type == "push" or event_type == "Push Hook":
            result = await webhook_service.handle_push_event(payload)
        elif event_type == "pipeline" or event_type == "Pipeline Hook":
            result = await webhook_service.handle_pipeline_event(payload)
        else:
            logger.warning(f"Unhandled event type: {event_type}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "status": "ignored",
                    "reason": f"Unhandled event type: {event_type}"
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "event_type": event_type,
                "result": result
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/gitlab")
async def gitlab_webhook_info():
    """
    Get information about the GitLab webhook endpoint.
    
    Returns:
        JSON with webhook configuration information
    """
    settings = get_settings()
    
    return {
        "webhook_url": f"http://your-domain/webhook/gitlab",
        "supported_events": [
            "Merge Request Hook",
            "Push Hook",
            "Pipeline Hook"
        ],
        "required_headers": [
            "X-Gitlab-Event",
            "X-Gitlab-Token (if configured)"
        ],
        "configuration": {
            "webhook_secret_configured": bool(settings.webhook_secret),
            "gitlab_url": settings.gitlab_url
        }
    }
