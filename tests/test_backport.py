"""
Tests for backport functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.backport_service import (
    BackportService,
    BackportResult,
    CherryPickResult
)
from app.services.gitlab_service import GitLabService


@pytest.fixture
def mock_gitlab_service():
    """Create mock GitLab service."""
    service = Mock(spec=GitLabService)
    return service


@pytest.fixture
def mock_project():
    """Create mock GitLab project."""
    project = Mock()
    project.id = 123
    project.name = "Test Project"
    project.path_with_namespace = "test-group/test-project"
    return project


@pytest.fixture
def mock_mr():
    """Create mock merge request."""
    mr = Mock()
    mr.iid = 10
    mr.title = "Test MR"
    mr.source_branch = "feature/test"
    mr.target_branch = "main"
    mr.state = "merged"
    return mr


class TestBackportService:
    """Tests for BackportService."""
    
    def test_init(self):
        """Test service initialization."""
        service = BackportService()
        assert service.gitlab is not None
        assert isinstance(service.gitlab, GitLabService)
    
    @pytest.mark.asyncio
    async def test_execute_backport_success(
        self,
        mock_gitlab_service,
        mock_project,
        mock_mr
    ):
        """Test successful backport execution."""
        # Setup mocks
        mock_gitlab_service.get_project.return_value = mock_project
        mock_gitlab_service.get_branch.return_value = Mock()
        mock_gitlab_service.get_merge_request.return_value = mock_mr
        
        # Mock MR commits
        mock_commit = Mock()
        mock_commit.id = "abc123def456"
        mock_commit.title = "Test commit"
        mock_commit.committed_date = "2024-01-01T00:00:00Z"
        mock_mr.commits.return_value = [mock_commit]
        
        # Mock cherry-pick success
        mock_gitlab_service.cherry_pick_commit.return_value = {
            "success": True,
            "data": {"id": "newcommit123"}
        }
        
        # Mock MR creation
        mock_new_mr = Mock()
        mock_new_mr.iid = 20
        mock_new_mr.web_url = "https://gitlab.example.com/test/-/merge_requests/20"
        mock_gitlab_service.create_merge_request.return_value = mock_new_mr
        
        # Execute backport
        service = BackportService(mock_gitlab_service)
        result = await service.execute_backport(
            project_path="test-group/test-project",
            source_branch="feature/test",
            target_branch="release/v1.0",
            mr_iid=10
        )
        
        # Assertions
        assert result.success is True
        assert result.mr_iid == 20
        assert result.mr_url == "https://gitlab.example.com/test/-/merge_requests/20"
        assert result.successful_commits == 1
        assert result.total_commits == 1
    
    def test_cherry_pick_commit_success(
        self,
        mock_gitlab_service
    ):
        """Test successful cherry-pick."""
        mock_gitlab_service.cherry_pick_commit.return_value = {
            "success": True,
            "data": {"id": "newcommit123"}
        }
        
        service = BackportService(mock_gitlab_service)
        result = service._cherry_pick_commit(
            project_id=123,
            commit_sha="abc123",
            target_branch="release/v1.0",
            message="Test commit"
        )
        
        assert result.success is True
        assert result.commit_sha == "abc123"
        assert result.commit_title == "Test commit"
    
    def test_cherry_pick_commit_conflict(
        self,
        mock_gitlab_service
    ):
        """Test cherry-pick with conflict."""
        mock_gitlab_service.cherry_pick_commit.return_value = {
            "success": False,
            "conflict": True,
            "error": "Cherry-pick conflict"
        }
        
        service = BackportService(mock_gitlab_service)
        result = service._cherry_pick_commit(
            project_id=123,
            commit_sha="abc123",
            target_branch="release/v1.0",
            message="Test commit"
        )
        
        assert result.success is False
        assert result.conflict is True
        assert result.error == "Cherry-pick conflict"


class TestBackportResult:
    """Tests for BackportResult dataclass."""
    
    def test_duration_calculation(self):
        """Test duration calculation."""
        from datetime import datetime, timedelta
        
        result = BackportResult(
            success=True,
            project_path="test/project",
            source_branch="feature/test",
            target_branch="release/v1.0",
            backport_branch="feature/test_backport",
            started_at=datetime.utcnow() - timedelta(seconds=10),
            completed_at=datetime.utcnow()
        )
        
        duration = result.duration_seconds()
        assert 9.5 <= duration <= 10.5  # Allow some tolerance
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = BackportResult(
            success=True,
            project_path="test/project",
            source_branch="feature/test",
            target_branch="release/v1.0",
            backport_branch="feature/test_backport",
            mr_url="https://gitlab.example.com/test/-/merge_requests/10",
            mr_iid=10,
            total_commits=3,
            successful_commits=2
        )
        
        data = result.to_dict()
        
        assert data["success"] is True
        assert data["project_path"] == "test/project"
        assert data["mr_iid"] == 10
        assert data["total_commits"] == 3
        assert "duration_seconds" in data
