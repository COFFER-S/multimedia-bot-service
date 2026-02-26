"""
Helper functions for the GitLab Backport Bot Service.
"""

import re
import hmac
import hashlib
from typing import Optional, Dict, Any
from urllib.parse import urlparse


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify GitLab webhook signature.
    
    Args:
        payload: Raw request body
        signature: X-Gitlab-Token header value
        secret: Webhook secret for verification
        
    Returns:
        True if signature is valid or no secret configured
    """
    if not secret:
        return True
    
    if not signature:
        return False
    
    # GitLab uses simple token comparison for X-Gitlab-Token
    return hmac.compare_digest(signature, secret)


def sanitize_branch_name(branch_name: str) -> str:
    """
    Sanitize branch name by removing illegal characters.
    
    Args:
        branch_name: Original branch name
        
    Returns:
        Sanitized branch name safe for GitLab API
    """
    # Replace illegal characters with underscore
    illegal_chars = [' ', '~', '^', ':', '?', '*', '[', '\\', '@{', '..']
    result = branch_name
    for char in illegal_chars:
        result = result.replace(char, '_')
    
    # Remove leading/trailing dots and slashes
    result = result.strip('./')
    
    # Ensure not empty
    if not result:
        result = "backport-branch"
    
    return result


def extract_project_info(gitlab_url: str, project_path: str) -> Dict[str, Any]:
    """
    Extract project information from GitLab URL and project path.
    
    Args:
        gitlab_url: GitLab instance URL
        project_path: Project path with namespace
        
    Returns:
        Dictionary with extracted information
    """
    parsed = urlparse(gitlab_url)
    
    return {
        "base_url": f"{parsed.scheme}://{parsed.netloc}",
        "api_url": f"{parsed.scheme}://{parsed.netloc}/api/v4",
        "project_path": project_path,
        "web_url": f"{gitlab_url}/{project_path}",
    }


def format_backport_branch_name(source_branch: str, suffix: str = "backport") -> str:
    """
    Format a backport branch name from source branch.
    
    Args:
        source_branch: Original source branch name
        suffix: Suffix to append
        
    Returns:
        Formatted backport branch name
    """
    sanitized = sanitize_branch_name(source_branch)
    return f"{sanitized}_{suffix}"


def truncate_commit_message(message: str, max_length: int = 72) -> str:
    """
    Truncate commit message to fit in standard git limits.
    
    Args:
        message: Original commit message
        max_length: Maximum allowed length
        
    Returns:
        Truncated message
    """
    lines = message.split('\n')
    first_line = lines[0]
    
    if len(first_line) > max_length:
        first_line = first_line[:max_length - 3] + "..."
    
    if len(lines) > 1:
        return first_line + '\n' + '\n'.join(lines[1:])
    
    return first_line


def mask_sensitive_data(data: Dict[str, Any], sensitive_keys: list = None) -> Dict[str, Any]:
    """
    Mask sensitive data in dictionary for logging.
    
    Args:
        data: Dictionary containing data
        sensitive_keys: List of keys to mask
        
    Returns:
        Dictionary with sensitive data masked
    """
    if sensitive_keys is None:
        sensitive_keys = ['token', 'password', 'secret', 'key', 'auth']
    
    result = {}
    for key, value in data.items():
        if any(s in key.lower() for s in sensitive_keys):
            if isinstance(value, str) and len(value) > 8:
                result[key] = value[:4] + "****" + value[-4:]
            else:
                result[key] = "****"
        elif isinstance(value, dict):
            result[key] = mask_sensitive_data(value, sensitive_keys)
        else:
            result[key] = value
    
    return result
