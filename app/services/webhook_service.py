"""
Webhook service for processing GitLab webhook events.
"""

import re
from typing import Dict, Any, Optional, List

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
    
    # Comment patterns that trigger backport
    BACKPORT_COMMENT_PATTERNS = [
        r"@bot\s+backport\s+to\s+(\S+)",
        r"@backport-bot\s+(\S+)",
        r"/backport\s+(\S+)",
    ]
    
    def __init__(self):
        """Initialize webhook service."""
        self.backport_service = BackportService()
    
    async def handle_note_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle GitLab note (comment) webhook event.
        
        This is triggered when someone comments on an MR.
        Supports commands like: @bot backport to develop
        
        Args:
            payload: GitLab webhook payload for note events
            
        Returns:
            Processing result
        """
        object_attributes = payload.get("object_attributes", {})
        merge_request = payload.get("merge_request", {})
        project = payload.get("project", {})
        
        # Check if this is an MR comment
        noteable_type = object_attributes.get("noteable_type", "").lower()
        if noteable_type != "mergerequest":
            logger.debug("Note is not on an MR, ignoring")
            return {
                "action": "ignored",
                "reason": "Note is not on a merge request",
                "noteable_type": noteable_type
            }
        
        # Get comment text
        note_text = object_attributes.get("note", "")
        logger.info(f"Processing MR comment: {note_text[:50]}...")
        
        # Check for backport command
        target_branch = self._extract_target_branch_from_comment(note_text)
        
        if not target_branch:
            logger.debug("No backport command found in comment")
            return {
                "action": "ignored",
                "reason": "No backport command found in comment",
                "comment_preview": note_text[:100]
            }
        
        logger.info(f"Backport command detected: target={target_branch}")
        
        # Extract MR information from payload
        source_branch = merge_request.get("source_branch")
        mr_iid = merge_request.get("iid")
        project_path = project.get("path_with_namespace")
        
        if not source_branch:
            logger.error("Source branch not found in MR payload")
            return {
                "action": "failed",
                "reason": "Source branch not found in MR payload",
                "mr_iid": mr_iid
            }
        
        logger.info(
            f"Executing backport",
            project=project_path,
            source=source_branch,
            target=target_branch,
            mr_iid=mr_iid
        )
        
        # Execute backport
        try:
            result = await self.backport_service.execute_backport(
                project_path=project_path,
                source_branch=source_branch,
                target_branch=target_branch,
                mr_iid=mr_iid,
                continue_on_conflict=True
            )
            
            return {
                "action": "backport_executed",
                "mr_iid": mr_iid,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "success": result.success,
                "mr_url": result.mr_url,
                "mr_iid": result.mr_iid,
                "commits": {
                    "total": result.total_commits,
                    "successful": result.successful_commits,
                    "conflicts": len(result.conflict_commits),
                    "failed": len(result.failed_commits)
                }
            }
            
        except Exception as e:
            logger.error(f"Backport execution failed: {e}", exc_info=True)
            return {
                "action": "failed",
                "reason": str(e),
                "mr_iid": mr_iid,
                "source_branch": source_branch,
                "target_branch": target_branch
            }
    
    def _extract_target_branch_from_comment(self, comment: str) -> Optional[str]:
        """
        Extract target branch from comment text.
        
        Supports patterns like:
        - @bot backport to develop
        - @backport-bot release/v1.0
        - /backport main
        
        Args:
            comment: Comment text
            
        Returns:
            Target branch name or None if not found
        """
        for pattern in self.BACKPORT_COMMENT_PATTERNS:
            match = re.search(pattern, comment, re.IGNORECASE)
            if match:
                target = match.group(1).strip()
                # Remove any trailing punctuation
                target = target.rstrip(".,;:!?")
                return sanitize_branch_name(target)
        
        return None
    
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
        
        # Only process merged MRs with backport labels
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
