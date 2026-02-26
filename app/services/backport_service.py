"""
Backport service - core logic for cherry-picking and merge request creation.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from app.services.gitlab_service import GitLabService
from app.utils.logger import get_logger
from app.utils.helpers import (
    format_backport_branch_name,
    sanitize_branch_name,
    truncate_commit_message
)

logger = get_logger(__name__)


@dataclass
class CherryPickResult:
    """Result of a cherry-pick operation."""
    success: bool
    commit_sha: str
    commit_title: str
    error: Optional[str] = None
    conflict: bool = False


@dataclass
class BackportResult:
    """Result of a complete backport operation."""
    success: bool
    project_path: str
    source_branch: str
    target_branch: str
    backport_branch: str
    mr_url: Optional[str] = None
    mr_iid: Optional[int] = None
    total_commits: int = 0
    successful_commits: int = 0
    conflict_commits: List[CherryPickResult] = field(default_factory=list)
    failed_commits: List[CherryPickResult] = field(default_factory=list)
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def duration_seconds(self) -> float:
        """Calculate operation duration in seconds."""
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "project_path": self.project_path,
            "source_branch": self.source_branch,
            "target_branch": self.target_branch,
            "backport_branch": self.backport_branch,
            "mr_url": self.mr_url,
            "mr_iid": self.mr_iid,
            "total_commits": self.total_commits,
            "successful_commits": self.successful_commits,
            "conflict_commits": [
                {"sha": c.commit_sha, "title": c.commit_title, "error": c.error}
                for c in self.conflict_commits
            ],
            "failed_commits": [
                {"sha": c.commit_sha, "title": c.commit_title, "error": c.error}
                for c in self.failed_commits
            ],
            "error": self.error,
            "duration_seconds": self.duration_seconds(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class BackportService:
    """Service for handling backport operations."""
    
    def __init__(self, gitlab_service: Optional[GitLabService] = None):
        """
        Initialize backport service.
        
        Args:
            gitlab_service: GitLab service instance (creates new if not provided)
        """
        self.gitlab = gitlab_service or GitLabService()
    
    async def execute_backport(
        self,
        project_path: str,
        source_branch: str,
        target_branch: str,
        mr_iid: Optional[int] = None,
        continue_on_conflict: bool = False
    ) -> BackportResult:
        """
        Execute backport from source branch to target branch.
        
        Args:
            project_path: GitLab project path with namespace
            source_branch: Source branch name (from MR)
            target_branch: Target branch name
            mr_iid: Optional specific MR IID to backport
            continue_on_conflict: Whether to continue on cherry-pick conflicts
            
        Returns:
            BackportResult with operation details
        """
        logger.info(f"🚀 Starting backport: {source_branch} → {target_branch}")
        logger.info(f"📁 Project: {project_path}")
        
        result = BackportResult(
            success=False,
            project_path=project_path,
            source_branch=source_branch,
            target_branch=target_branch,
            backport_branch=""
        )
        
        try:
            # Get project
            project = self.gitlab.get_project(project_path)
            
            # Verify target branch exists
            target_branch_info = self.gitlab.get_branch(project, target_branch)
            if not target_branch_info:
                raise ValueError(f"Target branch '{target_branch}' not found")
            
            # Get source MR - either from provided IID or find by source branch
            source_mr = None
            if mr_iid:
                source_mr = self.gitlab.get_merge_request(project, mr_iid)
            else:
                # Find MR from source branch (could be merged or not, we just need the commits)
                mrs = project.mergerequests.list(
                    state='all',  # Get all MRs, not just merged
                    source_branch=source_branch,
                    per_page=1
                )
                if mrs:
                    source_mr = mrs[0]
            
            if not source_mr:
                raise ValueError(f"No MR found for source branch '{source_branch}'")
            
            logger.info(f"✅ Found MR: !{source_mr.iid} - {source_mr.title}")
            
            # Create backport branch
            backport_branch = format_backport_branch_name(source_branch, f"backport-to-{target_branch.replace('/', '-')}")
            
            try:
                self.gitlab.create_branch(project, backport_branch, target_branch)
            except Exception as e:
                if "already exists" in str(e):
                    logger.warning(f"Branch {backport_branch} already exists")
                else:
                    raise
            
            result.backport_branch = backport_branch
            
            # Get commits from MR
            commits = source_mr.commits()
            if not commits:
                raise ValueError(f"No commits found in MR !{source_mr.iid}")
            
            # Sort commits chronologically
            commits_sorted = sorted(commits, key=lambda c: c.committed_date)
            result.total_commits = len(commits_sorted)
            
            logger.info(f"📋 Found {len(commits_sorted)} commits to cherry-pick")
            
            # Cherry-pick each commit
            for i, commit in enumerate(commits_sorted, 1):
                logger.info(f"[{i}/{len(commits_sorted)}] {commit.id[:8]} | {commit.title}")
                
                cherry_pick_result = self._cherry_pick_commit(
                    project.id,
                    commit.id,
                    backport_branch,
                    commit.title
                )
                
                if cherry_pick_result.success:
                    result.successful_commits += 1
                    logger.info(f" ✅ Cherry-picked successfully")
                elif cherry_pick_result.conflict:
                    result.conflict_commits.append(cherry_pick_result)
                    logger.warning(f" ⚠️ Cherry-pick conflict")
                    if not continue_on_conflict:
                        break
                else:
                    result.failed_commits.append(cherry_pick_result)
                    logger.error(f" ❌ Cherry-pick failed: {cherry_pick_result.error}")
            
            # Create MR if we have at least one successful commit
            if result.successful_commits > 0:
                mr = self._create_backport_mr(
                    project,
                    backport_branch,
                    target_branch,
                    source_mr,
                    result
                )
                result.mr_iid = mr.iid
                result.mr_url = mr.web_url
                result.success = True
            else:
                result.error = "No commits were successfully cherry-picked"
            
        except Exception as e:
            logger.error(f"Backport failed: {e}", exc_info=True)
            result.error = str(e)
        finally:
            from datetime import datetime
            result.completed_at = datetime.utcnow()
            duration = result.duration_seconds()
            logger.info(f"⏱️ Backport completed in {duration:.2f}s")
        
        return result
    
    def _cherry_pick_commit(
        self,
        project_id: int,
        commit_sha: str,
        target_branch: str,
        message: str
    ) -> CherryPickResult:
        """
        Cherry-pick a single commit.
        
        Args:
            project_id: GitLab project ID
            commit_sha: Commit SHA to cherry-pick
            target_branch: Target branch
            message: Commit message
            
        Returns:
            CherryPickResult with operation status
        """
        result = self.gitlab.cherry_pick_commit(
            project_id,
            commit_sha,
            target_branch,
            message
        )
        
        if result.get("success"):
            return CherryPickResult(
                success=True,
                commit_sha=commit_sha,
                commit_title=message
            )
        elif result.get("conflict"):
            return CherryPickResult(
                success=False,
                commit_sha=commit_sha,
                commit_title=message,
                conflict=True,
                error=result.get("error", "Cherry-pick conflict")
            )
        else:
            return CherryPickResult(
                success=False,
                commit_sha=commit_sha,
                commit_title=message,
                error=result.get("error", "Cherry-pick failed")
            )
    
    def _create_backport_mr(
        self,
        project: Any,
        backport_branch: str,
        target_branch: str,
        source_mr: Any,
        result: BackportResult
    ) -> Any:
        """
        Create backport merge request.
        
        Args:
            project: GitLab project
            backport_branch: Backport branch name
            target_branch: Target branch name
            source_mr: Original source MR
            result: Backport result
            
        Returns:
            Created merge request
        """
        # Build MR title
        title = f"[Backport] from {result.source_branch}"
        
        # Build MR description
        desc_lines = [
            f"## 🤖 Automated Backport",
            f"",
            f"- **Source Branch:** `{result.source_branch}`",
            f"- **Target Branch:** `{result.target_branch}`",
            f"- **Original MR:** !{source_mr.iid}",
            f"- **Commits Cherry-picked:** ✅ {result.successful_commits}/{result.total_commits}",
            f""
        ]
        
        # Add conflict information
        if result.conflict_commits:
            desc_lines.extend([
                f"## ❌ Cherry-pick Conflicts",
                f"",
                f"The following {len(result.conflict_commits)} commits had conflicts:",
                f""
            ])
            for commit in result.conflict_commits:
                desc_lines.append(f"- ❌ `{commit.commit_sha[:8]}` - {commit.commit_title}")
            desc_lines.extend([
                f"",
                f"**Action Required:** Manual cherry-pick needed",
                f""
            ])
        
        # Add failure information
        if result.failed_commits:
            desc_lines.extend([
                f"## ❌ Cherry-pick Failures",
                f"",
                f"The following {len(result.failed_commits)} commits failed:",
                f""
            ])
            for commit in result.failed_commits:
                desc_lines.append(f"- ❌ `{commit.commit_sha[:8]}` - {commit.commit_title}")
            desc_lines.append(f"")
        
        # Add notes
        desc_lines.extend([
            f"## ⚠️ Important Notes",
            f"",
            f"- This is an automated backport",
            f"- **Review all changes carefully**",
            f"- 🔴 **Verify build and tests before merging**",
            f""
        ])
        
        if result.conflict_commits or result.failed_commits:
            desc_lines.append(f"- 🟡 **Manual intervention required**")
        
        description = "\n".join(desc_lines)
        
        # Create MR
        mr = self.gitlab.create_merge_request(
            project,
            backport_branch,
            target_branch,
            title,
            description,
            remove_source_branch=True
        )
        
        logger.info(f"Created backport MR: !{mr.iid}")
        return mr
