"""
Resource limits definitions for sandbox containers.
"""

from dataclasses import dataclass
from tools.c_tools.config import SandboxConfig, DEFAULT_CONFIG


@dataclass
class ResourceLimits:
    """Encapsulates execution limits for Docker containers."""

    timeout: int = 10  # Seconds
    memory_limit: str = "256m"  # e.g., 256m, 512m
    cpu_limit: float = 1.0  # e.g., 0.5, 1.0

    @classmethod
    def from_config(cls, config: SandboxConfig = DEFAULT_CONFIG) -> "ResourceLimits":
        """Create ResourceLimits from a SandboxConfig object."""
        return cls(
            timeout=config.timeout,
            memory_limit=config.memory_limit,
            cpu_limit=config.cpu_limit,
        )

    def validate(self) -> None:
        """Validate resource limit boundaries."""
        if self.timeout <= 0:
            raise ValueError("Timeout must be a positive integer.")
        if self.cpu_limit <= 0:
            raise ValueError("CPU limit must be a positive float.")
        if not self.memory_limit or not isinstance(self.memory_limit, str):
            raise ValueError("Memory limit must be a valid memory specifier string (e.g. '256m').")
