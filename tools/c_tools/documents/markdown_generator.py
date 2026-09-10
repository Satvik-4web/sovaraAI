"""
Markdown Document Generator module.
Generates structured Markdown (.md) documents with metadata frontmatter and GitHub-flavored formatting.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional

from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.file_ops.path_security import validate_workspace_path


def generate_markdown(
    filename: str,
    title: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a structured Markdown (.md) document with frontmatter and body text.

    Args:
        filename: Target output filename (e.g., 'summary.md').
        title: Main document title.
        content: Markdown body text string.
        metadata: Optional metadata dictionary formatted as YAML frontmatter.
        workspace_root: Optional workspace root directory override.

    Returns:
        Structured ExecutionResult dictionary.
    """
    start_time = time.perf_counter()

    if not filename.endswith(".md"):
        filename += ".md"

    try:
        validated_path = validate_workspace_path(filename, workspace_root)
    except ValueError as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(code=ErrorCode.PATH_TRAVERSAL_ATTEMPT, message=str(e)),
        ).to_dict()

    validated_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    if metadata:
        lines.append("---")
        lines.append(f"title: \"{title}\"")
        for k, v in metadata.items():
            lines.append(f"{k}: \"{v}\"")
        lines.append("---\n")

    lines.append(f"# {title}\n")
    lines.append(content)

    full_md = "\n".join(lines)

    try:
        with open(validated_path, "w", encoding="utf-8") as f:
            f.write(full_md)

        exec_time = time.perf_counter() - start_time
        file_size = validated_path.stat().st_size

        return ExecutionResult(
            success=True,
            result={
                "filename": validated_path.name,
                "path": str(validated_path),
                "size_bytes": file_size,
                "lines_count": len(full_md.splitlines()),
            },
            execution_time=exec_time,
        ).to_dict()

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.DOCUMENT_GENERATION_ERROR,
                message=f"Failed to generate Markdown document '{filename}': {str(e)}",
            ),
        ).to_dict()
