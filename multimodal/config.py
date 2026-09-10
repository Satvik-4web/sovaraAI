"""
SOVARA Multimodal Intelligence — Configuration

Central configuration for all multimodal subsystem components.
Every setting can be overridden via an environment variable, making
it easy to adapt to different hardware without changing code.

Environment variable prefix: SOVARA_
"""

import os
from pathlib import Path


# =============================================================================
# Ollama / VLM Configuration
# =============================================================================

# Ollama REST API base URL — local only, no external network calls.
# Ollama runs as a local server on this address.
OLLAMA_BASE_URL: str = os.getenv("SOVARA_OLLAMA_URL", "http://localhost:11434")

# Vision-Language Model to use via Ollama.
# Qwen2.5-VL-3B with Q4_K_M quantization fits comfortably in 6GB VRAM (RTX 3050).
# Change this if you pull a different model into Ollama.
VLM_MODEL: str = os.getenv("SOVARA_VLM_MODEL", "qwen2.5vl:3b")

# Request timeout for Ollama API calls (seconds).
# VLM inference on images can take 30–90s on consumer GPUs, so 120s is safe.
VLM_TIMEOUT: int = int(os.getenv("SOVARA_VLM_TIMEOUT", "120"))

# Maximum tokens the VLM should generate in its response.
# Larger values allow more detailed analysis but use more VRAM for KV cache.
VLM_MAX_TOKENS: int = int(os.getenv("SOVARA_VLM_MAX_TOKENS", "2048"))

# Number of context tokens for Ollama (controls KV cache size).
# Lower = less VRAM. 4096 is a good balance for 6GB cards.
VLM_NUM_CTX: int = int(os.getenv("SOVARA_VLM_NUM_CTX", "4096"))

# The system uses a single Ollama model for both VLM and reasoning.
# qwen3:4b is used for text-based reasoning tasks.
REASONING_MODEL: str = os.getenv("SOVARA_REASONING_MODEL", "qwen3:4b")
REASONING_TIMEOUT: int = int(os.getenv("SOVARA_REASONING_TIMEOUT", "120"))
REASONING_MAX_TOKENS: int = int(os.getenv("SOVARA_REASONING_MAX_TOKENS", "4096"))
REASONING_NUM_CTX: int = int(os.getenv("SOVARA_REASONING_NUM_CTX", "8192"))


# =============================================================================
# Network Security
# =============================================================================

ALLOWED_HOSTS: set[str] = {"localhost", "127.0.0.1", "::1"}


# =============================================================================
# PaddleOCR Configuration
# =============================================================================

# Primary OCR language. PaddleOCR uses language-specific models.
# "en" = English, "hi" = Hindi (Devanagari script).
OCR_LANG: str = os.getenv("SOVARA_OCR_LANG", "en")

# Additional OCR languages to run as a second pass.
# Set to "hi" for Hindi support alongside English.
# Set to "" to disable additional language passes.
OCR_ADDITIONAL_LANGS: str = os.getenv("SOVARA_OCR_ADDITIONAL_LANGS", "hi")

# Whether to use GPU for PaddleOCR.
# Disabled by default — PaddleOCR runs fine on CPU, and this keeps VRAM free
# for the VLM which needs it more.
OCR_USE_GPU: bool = os.getenv("SOVARA_OCR_USE_GPU", "false").lower() == "true"

# Whether to show PaddleOCR's internal logs.
# These are very noisy so they're off by default.
OCR_SHOW_LOG: bool = os.getenv("SOVARA_OCR_SHOW_LOG", "false").lower() == "true"


# =============================================================================
# Image Processing Limits
# =============================================================================

# Maximum image dimension (longest side in pixels) before we resize.
# Larger images eat more VRAM when sent to the VLM and more RAM during OCR.
# 1920px is a good balance between detail and resource usage.
IMAGE_MAX_DIMENSION: int = int(os.getenv("SOVARA_IMAGE_MAX_DIM", "1920"))

# DPI for rendering PDF pages into images (for OCR on scanned PDFs).
# 200 DPI gives good OCR accuracy without creating huge images.
# 150 DPI is faster but less accurate; 300 DPI is more accurate but slower.
PDF_RENDER_DPI: int = int(os.getenv("SOVARA_PDF_RENDER_DPI", "200"))

# Maximum file size we'll accept for processing (bytes).
# Default: 100 MB. Prevents accidentally loading huge files into memory.
MAX_FILE_SIZE: int = int(os.getenv("SOVARA_MAX_FILE_SIZE", str(100 * 1024 * 1024)))

MAX_PAGES: int = int(os.getenv("SOVARA_MAX_PAGES", "200"))


# =============================================================================
# Supported File Extensions
# =============================================================================

# Image formats we can process.
SUPPORTED_IMAGE_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp",
}

# Document formats we can process.
SUPPORTED_PDF_EXTENSIONS: set[str] = {".pdf"}

# Data formats we can process.
SUPPORTED_CSV_EXTENSIONS: set[str] = {".csv"}

# Everything combined.
SUPPORTED_EXTENSIONS: set[str] = (
    SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_PDF_EXTENSIONS | SUPPORTED_CSV_EXTENSIONS
)


# =============================================================================
# Error Codes
# =============================================================================

class ErrorCode:
    """
    Machine-readable error codes for the multimodal subsystem.

    These codes are returned in ErrorDetail.code so the SOVARA orchestrator
    can programmatically handle different failure modes.
    """

    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    OCR_FAILED = "OCR_FAILED"
    OCR_ENGINE_UNAVAILABLE = "OCR_ENGINE_UNAVAILABLE"
    VLM_UNAVAILABLE = "VLM_UNAVAILABLE"
    VLM_TIMEOUT = "VLM_TIMEOUT"
    VLM_RESPONSE_PARSE_ERROR = "VLM_RESPONSE_PARSE_ERROR"
    PDF_CORRUPTED = "PDF_CORRUPTED"
    PDF_PASSWORD_PROTECTED = "PDF_PASSWORD_PROTECTED"
    IMAGE_CORRUPTED = "IMAGE_CORRUPTED"
    GPU_UNAVAILABLE = "GPU_UNAVAILABLE"
    EMPTY_RESULT = "EMPTY_RESULT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


# =============================================================================
# Temporary File Storage
# =============================================================================

# Directory for intermediate files (rendered PDF pages, preprocessed images).
# These are cleaned up after processing completes.
TEMP_DIR: Path = Path(
    os.getenv("SOVARA_TEMP_DIR", "")
) or (Path.home() / ".sovara" / "tmp")
