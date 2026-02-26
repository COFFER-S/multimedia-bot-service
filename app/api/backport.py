"""
Backport API endpoints for manual backport operations.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from app.services.backport_service import BackportService, BackportResult
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


class BackportRequest(BaseModel):
    """Request model for backport operation."""
    project_path: str = Field(
        ...,
        description="GitLab project path with namespace (e.g., 'group/project')",
        example="adf/multimedia/esp-gmf"
    )
    source_branch: str = Field(
        ...,
        description="Source branch name",
        example="feature/awesome-feature"
    )
    target_branch: str = Field(
        ...,
        description="Target branch name for backport",
        example="release/v1.0"
    )
    mr_iid: Optional[int] = Field(
        None,
        description="Specific MR IID to backport (auto-detected if not provided)"
    )
    continue_on_conflict: bool = Field(
        False,
        description="Continue with successful commits when conflicts occur"
    )


class BackportResponse(BaseModel):
    """Response model for backport operation."""
    success: bool
    project_path: str
    source_branch: str
    target_branch: str
    backport_branch: str
    mr_url: Optional[str] = None
    mr_iid: Optional[int] = None
    total_commits: int
    successful_commits: int
    conflict_commits: List[dict]
    failed_commits: List[dict]
    error: Optional[str] = None
    duration_seconds: float


@router.post("/backport", response_model=BackportResponse)
async def create_backport(
    request: BackportRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute a backport operation manually.
    
    This endpoint allows you to manually trigger a backport from one branch to another.
    
    Args:
        request: Backport configuration
        
    Returns:
        Backport operation result with MR details
    """
    logger.info(
        f"Received backport request",
        project=request.project_path,
        source=request.source_branch,
        target=request.target_branch
    )
    
    try:
        # Initialize backport service
        backport_service = BackportService()
        
        # Execute backport
        result = await backport_service.execute_backport(
            project_path=request.project_path,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
            mr_iid=request.mr_iid,
            continue_on_conflict=request.continue_on_conflict
        )
        
        # Convert to response model
        return BackportResponse(
            success=result.success,
            project_path=result.project_path,
            source_branch=result.source_branch,
            target_branch=result.target_branch,
            backport_branch=result.backport_branch,
            mr_url=result.mr_url,
            mr_iid=result.mr_iid,
            total_commits=result.total_commits,
            successful_commits=result.successful_commits,
            conflict_commits=[
                {"sha": c.commit_sha, "title": c.commit_title, "error": c.error}
                for c in result.conflict_commits
            ],
            failed_commits=[
                {"sha": c.commit_sha, "title": c.commit_title, "error": c.error}
                for c in result.failed_commits
            ],
            error=result.error,
            duration_seconds=result.duration_seconds()
        )
        
    except Exception as e:
        logger.error(f"Backport failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backport operation failed: {str(e)}"
        )


@router.get("/backport/{project_path:path}/status")
async def get_backport_status(
    project_path: str,
    source_branch: str,
    target_branch: str
):
    """
    Get the status of a backport operation.
    
    Args:
        project_path: GitLab project path
        source_branch: Source branch
        target_branch: Target branch
        
    Returns:
        Status information about the backport
    """
    # This could be extended to query actual backport status from database
    return {
        "project_path": project_path,
        "source_branch": source_branch,
        "target_branch": target_branch,
        "status": "unknown",
        "message": "Backport status tracking not implemented yet"
    }
