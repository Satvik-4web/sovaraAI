"""
SOVARA Multimodal Intelligence — Network Security

Enforces local-only network policy. All HTTP calls must target
localhost or explicitly configured trusted-local endpoints.

This is critical for air-gapped deployments where no data
should leave the organization's network.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from multimodal.config import ALLOWED_HOSTS

logger = logging.getLogger("sovara.multimodal.security")


def validate_url(url: str) -> bool:
    """
    Validate that a URL targets only allowed local hosts.
    
    Args:
        url: URL to validate.
        
    Returns:
        True if the URL targets an allowed host.
        
    Raises:
        ValueError: If the URL targets a disallowed host.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        
        if hostname not in ALLOWED_HOSTS:
            raise ValueError(
                f"Network security violation: URL '{url}' targets "
                f"disallowed host '{hostname}'. "
                f"Allowed hosts: {sorted(ALLOWED_HOSTS)}. "
                f"SOVARA is configured for local-only operation."
            )
        return True
    except ValueError:
        raise
    except Exception as exc:
        logger.error("URL validation failed for '%s': %s", url, exc)
        raise ValueError(f"Invalid URL '{url}': {exc}")


def is_local_url(url: str) -> bool:
    """
    Check if a URL targets a local host without raising exceptions.
    
    Args:
        url: URL to check.
        
    Returns:
        True if local, False otherwise.
    """
    try:
        validate_url(url)
        return True
    except ValueError:
        return False
