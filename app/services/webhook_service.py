"""
Webhook service for processing GitLab webhook events.
"""

from typing import Dict, Any, Optional, List
import re

from app.services.backport_service import BackportService, BackportResult
from app.utils.logger import get_logger
from app.utils.helpers import sanitize_branch_name

logger = get_logger(__name__)


class WebhookService:
    """Service for handling GitLab webhook events."""
    
    # Label patterns that trigger backport
    BACKPORT_LABEL_PATTERNS = [
        r"backport[\-_]to[\-_](.+)",
        r"backport[\-](.+)",
    ]
    
    def __init__(self):
        """Initialize webhook service."""
        self.backport_service = BackportService()
    
    async def handle_merge_request_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GitLab merge request webhook event.
        
        Args:
            payload: GitLab webhook payload
            
        Returns:
            Processing result
        """
        object_attributes = payload.get("object_attributes", {})
        project = payload.get("project", {})
        
        # Extract information
        mr_state = object_attributes.get("state")
        mr_action = object_attributes.get("action")
        source_branch = object_attributes.get("source_branch")
        target_branch = object_attributes.get("target_branch")
        project_path = project.get("path_with_namespace")
        mr_iid = object_attributes.get("iid")
        labels = object_attributes.get("labels", [])
        
        logger.info(
            f"Processing MR event",
            mr_iid=mr_iid,
            action=mr_action,
            state=mr_state,
            source=source_branch,
            target=target_branch
        )
        
        # Only process merged MRs
        if mr_state != "merged":
            logger.info(f"MR !{mr_iid} is not merged (state={mr_state}), skipping")
            return {
                "action": "ignored",
                "reason": f"MR state is '{mr_state}', not 'merged'",
                "mr_iid": mr_iid
            }
        
        # Check for backport labels
        backport_targets = self._extract_backport_targets(labels)
        
        if not backport_targets:
            logger.info(f"No backport labels found for MR !{mr_iid}")
            return {
                "action": "ignored",
                "reason": "No backport labels found",
                "mr_iid": mr_iid,
                "labels": labels
            }
        
        # Execute backports
        results = []
        for target in backport_targets:
            logger.info(f"Starting backport to {target}")
            
            try:
                backport_result = await self.backport_service.execute_backport(
                    project_path=project_path,
                    source_branch=source_branch,
                    target_branch=target,
                    mr_iid=mr_iid,
                    continue_on_conflict=True
                )
                
                results.append({
                    "target_branch": target,
                    "success": backport_result.success,
                    "mr_url": backport_result.mr_url,
                    "mr_iid": backport_result.mr_iid,
                    "commits": {
                        "total": backport_result.total_commits,
                        "successful": backport_result.successful_commits,
                        "conflicts": len(backport_result.conflict_commits),
                        "failed": len(backport_result.failed_commits)
                    },
                    "error": backport_result.error
                })
                
            except Exception as e:
                logger.error(f"Backport to {target} failed: {e}")
                results.append({
                    "target_branch": target,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "action": "backport_executed",
            "mr_iid": mr_iid,
            "source_branch": source_branch,
            "results": results
        }
    
    async def handle_push_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GitLab push webhook event.
        
        Args:
            payload: GitLab webhook payload
            
        Returns:
            Processing result
        """
        ref = payload.get("ref", "")
        project = payload.get("project", {})
        project_path = project.get("path_with_namespace")
        
        branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref
        
        logger.info(f"Push event received", project=project_path, branch=branch)
        
        # Push events don't trigger backports automatically
        # But could be used for validation or cleanup
        
        return {
            "action": "ignored",
            "reason": "Push events do not trigger backports",
            "project": project_path,
            "branch": branch
        }
    
    async def handle_pipeline_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GitLab pipeline webhook event.
        
        Args:
            payload: GitLab webhook payload
            
        Returns:
            Processing result
        """
        object_attributes = payload.get("object_attributes", {})
        project = payload.get("project", {})
        project_path = project.get("path_with_namespace")
        
        status = object_attributes.get("status")
        ref = object_attributes.get("ref")
        
        logger.info(
            f"Pipeline event received",
            project=project_path,
            ref=ref,
            status=status
        )
        
        # Pipeline events could trigger backports on success
        # but currently we rely on MR merge events
        
        return {
            "action": "ignored",
            "reason": "Pipeline events do not trigger backports (use MR merge instead)",
            "project": project_path,
            "ref": ref,
            "status": status
        }
    
    def _extract_backport_targets(self, labels: List[Dict[str, Any]]) -> List[str]:
        """
        Extract backport target branches from MR labels.
        
        Args:
            labels: List of label dictionaries
            
        Returns:
            List of target branch names
        """
        targets = []
        
        for label in labels:
            label_title = label.get("title", "")
            
            for pattern in self.BACKPORT_LABEL_PATTERNS:
                match = re.search(pattern, label_title, re.IGNORECASE)
                if match:
                    target = match.group(1)
                    # Sanitize target branch name
                    target = sanitize_branch_name(target)
                    if target and target not in targets:
                        targets.append(target)
                    break
        
        return targets
