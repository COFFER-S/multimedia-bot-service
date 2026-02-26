"""
Configuration management for the GitLab Backport Bot Service.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # GitLab Configuration
    gitlab_url: str = Field(
        default="https://gitlab.espressif.cn:6688",
        alias="GITLAB_URL",
        description="GitLab instance URL"
    )
    gitlab_token: str = Field(
        alias="GITLAB_TOKEN",
        description="GitLab personal access token"
    )
    
    # Webhook Configuration
    webhook_secret: Optional[str] = Field(
        default=None,
        alias="WEBHOOK_SECRET",
        description="Webhook signature verification secret"
    )
    
    # Server Configuration
    host: str = Field(
        default="0.0.0.0",
        alias="HOST",
        description="Server bind address"
    )
    port: int = Field(
        default=8080,
        alias="PORT",
        description="Server port"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    # Backport Configuration
    default_continue_on_conflict: bool = Field(
        default=False,
        alias="DEFAULT_CONTINUE_ON_CONFLICT",
        description="Default behavior for continuing on conflicts"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"


def get_settings() -> Settings:
    """Get application settings instance."""
    return Settings()
