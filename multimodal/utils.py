"""
SOVARA Multimodal Intelligence — Utilities

Shared helper functions used across the subsystem:
  - File type detection (is it a PDF? an image?)
  - File validation (exists? readable? within size limit?)
  - Temporary directory management with automatic cleanup
  - Robust JSON extraction from VLM output (which may include markdown)
  - Image-to-base64 encoding for the Ollama REST API
"""

from __future__ import annotations

import base64
import json
import logging
import re
import shutil
import tempfile
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Generator, Optional

from multimodal.config import (
    MAX_FILE_SIZE,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
    TEMP_DIR,
)

# Module logger — all multimodal modules use the "sovara.multimodal" namespace.
logger = logging.getLogger("sovara.multimodal.utils")


# =============================================================================
# File Type Enum
# =============================================================================

class FileType(str, Enum):
    """
    Possible file types the subsystem can handle.

    Used by the pipeline to route files to the correct processor:
      - PDF → pdf_processor
      - IMAGE → image_processor + ocr / vision
      - UNKNOWN → error
    """

    PDF = "pdf"
    IMAGE = "image"
    CSV = "csv"
    UNKNOWN = "unknown"


# =============================================================================
# File Type Detection
# =============================================================================

def detect_file_type(file_path: str | Path) -> FileType:
    """
    Determine whether a file is a PDF, an image, a CSV, or unknown.

    Uses the file extension (case-insensitive). We intentionally avoid
    magic-number sniffing for the prototype because:
      1. Extensions are reliable for our use case (user-supplied documents).
      2. Magic-number detection adds complexity and a dependency (python-magic).

    Args:
        file_path: Path to the file.

    Returns:
        FileType.PDF, FileType.IMAGE, FileType.CSV, or FileType.UNKNOWN.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix in SUPPORTED_PDF_EXTENSIONS:
        return FileType.PDF
    elif suffix in SUPPORTED_IMAGE_EXTENSIONS:
        return FileType.IMAGE
    elif suffix == ".csv":
        return FileType.CSV
    else:
        return FileType.UNKNOWN


# =============================================================================
# File Validation
# =============================================================================

def validate_file(file_path: str | Path) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate that a file exists, is readable, and is within size limits.

    Returns:
        A tuple of (is_valid, error_code, error_message).
        If valid: (True, None, None).
        If invalid: (False, "ERROR_CODE", "Human-readable message").

    The error codes match config.ErrorCode constants so the caller can
    build an ErrorDetail directly from the return values.
    """
    path = Path(file_path)

    # --- Check existence ---
    if not path.exists():
        return (
            False,
            "FILE_NOT_FOUND",
            f"File not found: {path}",
        )

    # --- Check it's a file, not a directory ---
    if not path.is_file():
        return (
            False,
            "FILE_NOT_FOUND",
            f"Path is not a file: {path}",
        )

    # --- Check extension ---
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        return (
            False,
            "UNSUPPORTED_FILE_TYPE",
            f"Unsupported file type '{suffix}'. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    # --- Check file size ---
    try:
        size = path.stat().st_size
    except OSError as exc:
        return (
            False,
            "FILE_CORRUPTED",
            f"Cannot read file metadata: {exc}",
        )

    if size > MAX_FILE_SIZE:
        size_mb = size / (1024 * 1024)
        limit_mb = MAX_FILE_SIZE / (1024 * 1024)
        return (
            False,
            "FILE_TOO_LARGE",
            f"File is {size_mb:.1f} MB, exceeds limit of {limit_mb:.0f} MB",
        )

    if size == 0:
        return (
            False,
            "FILE_CORRUPTED",
            "File is empty (0 bytes)",
        )

    return (True, None, None)


# =============================================================================
# Temporary Directory Management
# =============================================================================

@contextmanager
def temp_dir_context(prefix: str = "sovara_") -> Generator[Path, None, None]:
    """
    Context manager that creates a temporary directory and cleans it up
    when the block exits.

    Usage:
        with temp_dir_context("ocr_") as tmp:
            # tmp is a Path to a temp directory
            rendered_page = tmp / "page_1.png"
            ...
        # Directory and all contents are deleted here

    The temp directory is created under TEMP_DIR (configurable) to keep
    all intermediate files in one known location. Falls back to the
    system default if TEMP_DIR doesn't exist.
    """
    # Ensure the parent temp directory exists.
    try:
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        parent = str(TEMP_DIR)
    except OSError:
        # Fall back to system temp if our configured dir is unusable.
        parent = None

    tmp_path = Path(tempfile.mkdtemp(prefix=prefix, dir=parent))

    try:
        yield tmp_path
    finally:
        # Clean up: remove the temp directory and everything in it.
        try:
            shutil.rmtree(tmp_path, ignore_errors=True)
        except Exception as exc:
            # Log but don't crash — cleanup failure is non-fatal.
            logger.warning("Failed to clean up temp dir %s: %s", tmp_path, exc)


# =============================================================================
# JSON Extraction from VLM Output
# =============================================================================

def safe_json_parse(text: str) -> Optional[dict]:
    """
    Robustly extract a JSON object from VLM output text.

    VLMs often wrap JSON in markdown code blocks like:

        ```json
        {"key": "value"}
        ```

    or include conversational text before/after the JSON. This function
    handles all of those cases:
      1. Try parsing the raw text as JSON.
      2. Try extracting JSON from a markdown code fence.
      3. Try finding a JSON object anywhere in the text (first { to last }).

    Args:
        text: Raw text output from the VLM.

    Returns:
        Parsed dict if successful, None if no valid JSON found.
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # --- Attempt 1: Direct parse ---
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # --- Attempt 2: Extract from markdown code fence ---
    # Matches ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    fence_matches = re.findall(fence_pattern, text, re.DOTALL)
    for match in fence_matches:
        try:
            result = json.loads(match.strip())
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            continue

    # --- Attempt 3: Find first { ... last } ---
    # This is the most aggressive strategy — finds the outermost braces.
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Nothing worked.
    return None


# =============================================================================
# Image Base64 Encoding
# =============================================================================

def encode_image_base64(image_path: str | Path) -> str:
    """
    Read an image file and return its base64-encoded string.

    Ollama's /api/generate endpoint expects images as base64 strings
    in the ``images`` array. This function reads the file bytes and
    encodes them.

    Args:
        image_path: Path to the image file.

    Returns:
        Base64-encoded string of the image bytes.

    Raises:
        FileNotFoundError: If the image file doesn't exist.
        OSError: If the file can't be read.
    """
    path = Path(image_path)
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# =============================================================================
# Text Helpers
# =============================================================================

def truncate_text(text: str, max_length: int = 500) -> str:
    """
    Truncate text to a maximum length, adding '...' if truncated.

    Useful for logging and error messages where we don't want to dump
    the entire extracted text.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
