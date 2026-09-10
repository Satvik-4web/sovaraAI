"""
Path security module enforcing strict workspace root isolation.
Prevents path traversal attacks (e.g. '../', absolute system paths).
"""

import os
from pathlib import Path
from typing import Optional
from tools.c_tools.config import DEFAULT_CONFIG


def validate_workspace_path(path: str, workspace_root: Optional[str] = None) -> Path:
    """
    Validates that a given file path remains strictly within the workspace root.

    Args:
        path: Target file or directory path string.
        workspace_root: Base workspace root directory. Defaults to SandboxConfig.workspace_root or current working dir.

    Returns:
        Absolute Path object if valid.

    Raises:
        ValueError: If path escapes the workspace root boundary (path traversal attempt).
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Path must be a non-empty string.")

    root_str = workspace_root or DEFAULT_CONFIG.workspace_root or "."
    resolved_root = Path(root_str).resolve()

    # Expand user/home directory references if any
    target_path = Path(os.path.expanduser(path))

    if target_path.is_absolute():
        resolved_target = target_path.resolve()
    else:
        resolved_target = (resolved_root / target_path).resolve()

    # Check relative hierarchy to enforce boundary
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        raise ValueError(
            f"Path traversal attempt blocked: '{path}' resolves to '{resolved_target}', "
            f"which is outside the workspace root '{resolved_root}'."
        )

    return resolved_target
