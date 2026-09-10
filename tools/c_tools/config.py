"""
Configuration management for SOVARA Tools Subsystem.
Centralizes resource limits, Docker image configurations, workspace roots, and environment overrides.
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxConfig:
    """Configuration settings for Python Docker Sandbox execution and File Operations."""

    timeout: int = 10  # Seconds
    memory_limit: str = "256m"  # Megabytes / Bytes specification (e.g. 256m, 512m, 1g)
    cpu_limit: float = 1.0  # CPU core limit (e.g. 0.5, 1.0, 2.0)
    docker_image: str = "python:3.11-slim"  # Base Docker image for sandbox

    # Phase 2: File Operations & Workspace settings
    workspace_root: str = "."  # Workspace boundary root directory
    max_file_read_bytes: int = 1_048_576  # Default max read limit (1 MB)

    @classmethod
    def from_env(cls) -> "SandboxConfig":
        """Load configuration from environment variables with safe defaults."""
        timeout_val = int(os.getenv("SOVARA_SANDBOX_TIMEOUT", "10"))
        memory_val = os.getenv("SOVARA_SANDBOX_MEMORY", "256m")
        cpu_val = float(os.getenv("SOVARA_SANDBOX_CPU", "1.0"))
        image_val = os.getenv("SOVARA_DOCKER_IMAGE", "python:3.11-slim")
        workspace_val = os.getenv("SOVARA_WORKSPACE_ROOT", ".")
        max_bytes_val = int(os.getenv("SOVARA_MAX_FILE_READ_BYTES", "1048576"))

        return cls(
            timeout=timeout_val,
            memory_limit=memory_val,
            cpu_limit=cpu_val,
            docker_image=image_val,
            workspace_root=workspace_val,
            max_file_read_bytes=max_bytes_val,
        )


# Global default configuration instance
DEFAULT_CONFIG = SandboxConfig()
