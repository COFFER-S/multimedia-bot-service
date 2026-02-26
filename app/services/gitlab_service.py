"""
GitLab API service for interacting with GitLab instances.
"""

from typing import Optional, List, Dict, Any, Tuple
import requests
import gitlab
from gitlab.exceptions import GitlabGetError, GitlabCreateError, GitlabError

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GitLabService:
    """Service for GitLab API operations."""
    
    def __init__(self, gitlab_url: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize GitLab service.
        
        Args:
            gitlab_url: GitLab instance URL
            token: GitLab access token
        """
        settings = get_settings()
        self.gitlab_url = gitlab_url or settings.gitlab_url
        self.token = token or settings.gitlab_token
        self._client: Optional[gitlab.Gitlab] = None
    
    @property
    def client(self) -> gitlab.Gitlab:
        """Get or create GitLab client."""
        if self._client is None:
            if not self.token:
                raise ValueError("GitLab token is not configured")
            
            self._client = gitlab.Gitlab(
                self.gitlab_url,
                private_token=self.token,
                ssl_verify=False  # Disable SSL verification if needed
            )
            
            try:
                self._client.auth()
                logger.info(f"Connected to GitLab as {self._client.user.username}")
            except GitlabError as e:
                logger.error(f"Failed to authenticate with GitLab: {e}")
                raise
        
        return self._client
    
    def get_project(self, project_path: str) -> gitlab.v4.objects.Project:
        """
        Get GitLab project by path.
        
        Args:
            project_path: Project path with namespace (e.g., "group/project")
            
        Returns:
            GitLab project object
        """
        try:
            project = self.client.projects.get(project_path)
            logger.debug(f"Found project: {project.name}")
            return project
        except GitlabGetError as e:
            logger.error(f"Project not found: {project_path}")
            raise
    
    def get_merge_request(
        self, 
        project: gitlab.v4.objects.Project, 
        mr_iid: int
    ) -> gitlab.v4.objects.ProjectMergeRequest:
        """
        Get merge request by IID.
        
        Args:
            project: GitLab project
            mr_iid: Merge request internal ID
            
        Returns:
            Merge request object
        """
        try:
            mr = project.mergerequests.get(mr_iid)
            logger.debug(f"Found MR: !{mr_iid} - {mr.title}")
            return mr
        except GitlabGetError as e:
            logger.error(f"Merge request not found: !{mr_iid}")
            raise
    
    def get_branch(
        self, 
        project: gitlab.v4.objects.Project, 
        branch_name: str
    ) -> Optional[gitlab.v4.objects.ProjectBranch]:
        """
        Get branch by name.
        
        Args:
            project: GitLab project
            branch_name: Branch name
            
        Returns:
            Branch object or None if not found
        """
        try:
            branch = project.branches.get(branch_name)
            return branch
        except GitlabGetError:
            return None
    
    def create_branch(
        self, 
        project: gitlab.v4.objects.Project, 
        branch_name: str, 
        ref: str
    ) -> gitlab.v4.objects.ProjectBranch:
        """
        Create a new branch.
        
        Args:
            project: GitLab project
            branch_name: New branch name
            ref: Source reference (branch name or commit SHA)
            
        Returns:
            Created branch object
        """
        try:
            branch = project.branches.create({
                'branch': branch_name,
                'ref': ref
            })
            logger.info(f"Created branch: {branch_name} from {ref}")
            return branch
        except GitlabCreateError as e:
            if "already exists" in str(e):
                logger.warning(f"Branch {branch_name} already exists")
                return project.branches.get(branch_name)
            raise
    
    def cherry_pick_commit(
        self, 
        project_id: int, 
        commit_sha: str, 
        target_branch: str, 
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cherry-pick a commit using GitLab's native API.
        
        Args:
            project_id: GitLab project ID
            commit_sha: Commit SHA to cherry-pick
            target_branch: Target branch name
            message: Optional custom commit message
            
        Returns:
            Cherry-pick result or error information
        """
        url = f"{self.gitlab_url}/api/v4/projects/{project_id}/repository/commits/{commit_sha}/cherry_pick"
        headers = {
            "PRIVATE-TOKEN": self.token,
            "Content-Type": "application/json"
        }
        data = {"branch": target_branch}
        if message:
            data["message"] = message
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Cherry-picked {commit_sha[:8]} to {target_branch}")
            return {"success": True, "data": result}
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('message', error_msg)
                    error_code = error_data.get('error_code', '')
                    
                    if 'conflict' in error_code.lower():
                        logger.warning(f"Cherry-pick conflict: {commit_sha[:8]}")
                        return {"success": False, "conflict": True, "error": error_msg}
                except:
                    pass
            
            logger.error(f"Cherry-pick failed: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def create_merge_request(
        self, 
        project: gitlab.v4.objects.Project, 
        source_branch: str, 
        target_branch: str, 
        title: str, 
        description: str,
        remove_source_branch: bool = True
    ) -> gitlab.v4.objects.ProjectMergeRequest:
        """
        Create a new merge request.
        
        Args:
            project: GitLab project
            source_branch: Source branch name
            target_branch: Target branch name
            title: MR title
            description: MR description
            remove_source_branch: Whether to delete source branch after merge
            
        Returns:
            Created merge request object
        """
        try:
            mr = project.mergerequests.create({
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title,
                'description': description,
                'remove_source_branch': remove_source_branch
            })
            logger.info(f"Created MR: !{mr.iid} - {title}")
            return mr
        except GitlabCreateError as e:
            logger.error(f"Failed to create MR: {e}")
            raise
