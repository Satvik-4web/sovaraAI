"""
SOVARA Multimodal Intelligence — Schemas

Pydantic models defining every input/output contract for the subsystem.
The SOVARA orchestrator depends ONLY on these schemas — internal
implementation details are hidden behind them.

Design principles:
  - Every function returns a Pydantic model (never raw dicts or strings).
  - Confidence is explicitly tracked: either available with a score, or
    marked as unavailable. We never fabricate confidence values.
  - Observations are separated into "observed" (directly visible) and
    "inferred" (model's interpretation) to avoid presenting guesses as facts.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Confidence Tracking
# =============================================================================

class ConfidenceInfo(BaseModel):
    """
    Explicit confidence representation.

    When the underlying engine (e.g., PaddleOCR) provides a calibrated
    confidence score, ``available`` is True and ``score`` holds the value
    in the range 0.0–1.0.

    When confidence cannot be measured (e.g., free-form VLM text output),
    ``available`` is False and ``score`` is None. This is HONEST — we
    never invent numbers.
    """

    available: bool = Field(
        description="Whether a calibrated confidence score is available"
    )
    score: Optional[float] = Field(
        default=None,
        description="Confidence score 0.0–1.0 if available, else None",
        ge=0.0,
        le=1.0,
    )


# =============================================================================
# Error Schema
# =============================================================================

class ErrorDetail(BaseModel):
    """
    Structured error information returned when ``success`` is False.

    ``code`` is a machine-readable constant from ``config.ErrorCode``
    so the orchestrator can switch on it programmatically.
    ``message`` is a human-readable explanation for logging/debugging.
    """

    code: str = Field(description="Machine-readable error code (see config.ErrorCode)")
    message: str = Field(description="Human-readable error description")


# =============================================================================
# Evidence & Core Reasoning Schemas
# =============================================================================

class Evidence(BaseModel):
    """
    Reusable provenance structure indicating where information came from.
    """
    source: str = Field(description="Source file name")
    page: Optional[int] = Field(default=None, description="Page number")
    image_id: Optional[str] = Field(default=None)
    type: str = Field(description="'ocr', 'vlm', 'text_extraction', 'reasoning'")
    text: Optional[str] = Field(default=None, description="Extracted text")
    visual_description: Optional[str] = Field(default=None)
    bbox: Optional[list[float]] = Field(default=None, description="[x1,y1,x2,y2]")
    originating_subsystem: str
    direct_observation: bool = Field(default=True)

class Inference(BaseModel):
    """A model inference."""
    content: str
    confidence: ConfidenceInfo
    supporting_evidence: list[Evidence] = Field(default_factory=list)

class Hypothesis(BaseModel):
    """A hypothesis requiring verification."""
    statement: str
    supporting_evidence: list[Evidence] = Field(default_factory=list)
    contradicting_evidence: list[Evidence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)

class Finding(BaseModel):
    """An evidence-grounded finding."""
    statement: str
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: ConfidenceInfo

class Contradiction(BaseModel):
    """Conflicting evidence."""
    topic: str
    evidence_a: list[Evidence] = Field(default_factory=list)
    evidence_b: list[Evidence] = Field(default_factory=list)
    resolution: Optional[str] = Field(default=None)


# =============================================================================
# OCR Schemas
# =============================================================================

class OCRPageResult(BaseModel):
    """
    OCR result for a single page or image.

    ``confidence`` comes directly from PaddleOCR's per-line confidence
    scores, averaged across the page. If OCR did not produce scores,
    confidence is marked unavailable.
    """

    page: int = Field(default=1, description="Page number (1-indexed)")
    text: str = Field(default="", description="Extracted text content")
    confidence: ConfidenceInfo = Field(
        description="OCR confidence for this page"
    )
    word_count: int = Field(default=0, description="Number of words extracted")
    language: str = Field(
        default="en", description="Language used for this OCR pass"
    )


class OCRResult(BaseModel):
    """
    Complete OCR extraction result — the return type of ``extract_text()``.

    Contains combined text from all pages plus per-page breakdowns.
    ``text_type`` indicates whether the content appears to be printed,
    handwritten, or mixed (heuristic-based, not guaranteed).
    """

    success: bool = Field(description="Whether extraction succeeded")
    text: str = Field(default="", description="Combined text from all pages")
    pages: list[OCRPageResult] = Field(
        default_factory=list, description="Per-page OCR results"
    )
    source: str = Field(default="", description="Source file name")
    text_type: str = Field(
        default="printed",
        description="Detected text type: 'printed', 'handwritten', or 'mixed'",
    )
    warnings: list[str] = Field(
        default_factory=list, description="Non-fatal warnings"
    )
    error: Optional[ErrorDetail] = Field(
        default=None, description="Error details if success is False"
    )


# =============================================================================
# Vision / Image Analysis Schemas
# =============================================================================

class Observation(BaseModel):
    """
    A single observation from visual analysis.

    The ``type`` field is critical: it separates what the model can
    directly SEE ("observed") from what it THINKS ("inferred").
    This prevents the dangerous pattern of presenting AI guesses
    as factual observations.
    """

    type: str = Field(
        description="'observed' for direct visual observations, "
        "'inferred' for the model's interpretations"
    )
    content: str = Field(description="The observation or inference text")
    confidence: ConfidenceInfo = Field(
        default_factory=lambda: ConfidenceInfo(available=False),
    )


class ImageAnalysisResult(BaseModel):
    """
    Result of VLM image analysis — the return type of ``analyze_image()``.

    ``observations`` is the most important field: each entry is tagged
    as "observed" or "inferred" so downstream consumers know what's
    actually visible vs. what's the model's interpretation.
    """

    success: bool
    image: str = Field(default="", description="Source image file name")
    description: str = Field(
        default="", description="Overall image description from the VLM"
    )
    objects: list[str] = Field(
        default_factory=list, description="Objects detected in the image"
    )
    entities: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    spatial_info: list[str] = Field(default_factory=list)
    technical_observations: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    observations: list[Observation] = Field(
        default_factory=list,
        description="Observations split into observed/inferred",
    )
    text_content: list[str] = Field(
        default_factory=list, description="Any text visible in the image"
    )
    uncertainties: list[str] = Field(
        default_factory=list,
        description="Things the model is uncertain about",
    )
    confidence: ConfidenceInfo = Field(
        default_factory=lambda: ConfidenceInfo(available=False),
        description="Overall analysis confidence (typically unavailable for VLM)",
    )
    warnings: list[str] = Field(default_factory=list)
    error: Optional[ErrorDetail] = Field(default=None)


class VisualQuestionAnswer(BaseModel):
    """VQA result."""
    success: bool
    question: str = Field(default='')
    answer: str = Field(default='')
    evidence: list[Evidence] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    inferences: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    confidence: ConfidenceInfo = Field(default_factory=lambda: ConfidenceInfo(available=False))
    warnings: list[str] = Field(default_factory=list)
    error: Optional[ErrorDetail] = Field(default=None)


# =============================================================================
# Document Analysis Schemas
# =============================================================================

class FigureInfo(BaseModel):
    """Metadata about a figure/image extracted from a document page."""

    page: int = Field(description="Page number where the figure was found")
    index: int = Field(description="Figure index on that page (0-based)")
    description: str = Field(
        default="", description="VLM description of the figure"
    )
    width: int = Field(default=0, description="Figure width in pixels")
    height: int = Field(default=0, description="Figure height in pixels")


class TableInfo(BaseModel):
    """Information about a table detected on a document page."""

    page: int
    content: str = Field(
        default="", description="Extracted table content (text representation)"
    )
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    structured: bool = Field(default=False)
    confidence: ConfidenceInfo = Field(
        default_factory=lambda: ConfidenceInfo(available=False),
    )


class DocumentPageResult(BaseModel):
    """
    Analysis result for a single document page.

    Combines OCR text, visual observations, detected tables, and figures
    into one unified per-page view.
    """

    page: int
    text: str = Field(default="", description="Text content of this page")
    content_type: str = Field(default="text", description="text, scanned, mixed")
    has_images: bool = Field(default=False)
    has_tables: bool = Field(default=False)
    entities: list[str] = Field(default_factory=list)
    visual_observations: list[Observation] = Field(default_factory=list)
    tables: list[TableInfo] = Field(default_factory=list)
    figures: list[FigureInfo] = Field(default_factory=list)
    confidence: ConfidenceInfo = Field(
        default_factory=lambda: ConfidenceInfo(available=False),
    )


class DocumentAnalysisResult(BaseModel):
    """
    Complete document analysis — the return type of ``analyze_document()``.

    Merges text extraction, OCR, and visual analysis into a unified
    document representation.
    """

    success: bool
    document: str = Field(default="", description="Source document file name")
    page_count: int = Field(default=0)
    pages: list[DocumentPageResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: Optional[ErrorDetail] = Field(default=None)


class MultiDocumentAnalysisResult(BaseModel):
    """Multi-document analysis."""
    success: bool
    task: str = Field(default='')
    sources: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: Optional[ErrorDetail] = Field(default=None)


class ReasoningResult(BaseModel):
    """Result of reason_about_evidence."""
    success: bool
    task: str = Field(default='')
    observations: list[str] = Field(default_factory=list)
    inferences: list[Inference] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: Optional[ErrorDetail] = Field(default=None)


# =============================================================================
# P&ID Analysis Schemas
# =============================================================================

class PIDComponent(BaseModel):
    """
    Base schema for any component found in a P&ID drawing.

    ``uncertain`` is True when the system could not confidently identify
    the component. In that case, ``tag`` may be None and ``confidence``
    will be low or unavailable. This is by design — P&ID interpretation
    is hard, and honesty about uncertainty is more valuable than false
    confidence.
    """

    tag: Optional[str] = Field(
        default=None, description="Component tag, e.g. 'P-101', 'FT-301'"
    )
    type: str = Field(
        default="unknown", description="Component type, e.g. 'centrifugal pump'"
    )
    description: str = Field(default="")
    location: str = Field(
        default="", description="Approximate location in the drawing"
    )
    bbox: Optional[list[float]] = Field(default=None)
    center: Optional[list[float]] = Field(default=None)
    region: str = Field(default="")
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: ConfidenceInfo = Field(
        default_factory=lambda: ConfidenceInfo(available=False),
    )
    uncertain: bool = Field(
        default=False,
        description="True if identification is uncertain",
    )


class PIDEquipment(PIDComponent):
    """A piece of equipment (pump, vessel, tank, reactor, etc.)."""

    pass


class PIDValve(PIDComponent):
    """A valve in the P&ID."""

    valve_type: str = Field(
        default="unknown",
        description="Valve subtype: gate, globe, ball, check, control, etc.",
    )


class PIDInstrument(PIDComponent):
    """An instrument or sensor in the P&ID."""

    measured_variable: str = Field(
        default="",
        description="What it measures: flow, level, pressure, temperature, etc.",
    )
    function: str = Field(
        default="",
        description="Function: indicator, transmitter, controller, alarm, etc.",
    )


class PIDPipe(BaseModel):
    """A pipe or line connecting components in the P&ID."""

    label: Optional[str] = Field(
        default=None, description="Pipe label or line number"
    )
    from_component: str = Field(
        default="", description="Source component tag"
    )
    to_component: str = Field(
        default="", description="Destination component tag"
    )
    uncertain: bool = Field(default=False)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: ConfidenceInfo = Field(
        default_factory=lambda: ConfidenceInfo(available=False),
    )


class PIDConnection(BaseModel):
    """A connection (pipe, signal line, etc.) between two components."""

    from_tag: str = Field(default="")
    to_tag: str = Field(default="")
    connection_type: str = Field(
        default="pipe", description="Type: 'pipe', 'signal', 'electrical', etc."
    )
    uncertain: bool = Field(default=False)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: ConfidenceInfo = Field(
        default_factory=lambda: ConfidenceInfo(available=False),
    )


class PIDAnalysisResult(BaseModel):
    """
    Complete P&ID analysis — the return type of ``analyze_pid()``.

    This is the most complex output schema. It attempts to capture the
    structure of a P&ID drawing: equipment, valves, instruments, piping,
    and their interconnections.

    IMPORTANT: P&ID analysis is inherently uncertain. The ``uncertainties``
    list and per-component ``uncertain`` flags must be checked by the
    SOVARA orchestrator before presenting results as facts.
    """

    success: bool
    document_type: str = Field(default="P&ID")
    source: str = Field(default="", description="Source file name")
    equipment: list[PIDEquipment] = Field(default_factory=list)
    valves: list[PIDValve] = Field(default_factory=list)
    instruments: list[PIDInstrument] = Field(default_factory=list)
    pipes: list[PIDPipe] = Field(default_factory=list)
    connections: list[PIDConnection] = Field(default_factory=list)
    annotations: list[str] = Field(
        default_factory=list,
        description="Visible text annotations in the drawing",
    )
    observations: list[Observation] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    ocr_tags: list[str] = Field(
        default_factory=list,
        description="Raw equipment/instrument tags found by OCR",
    )
    warnings: list[str] = Field(default_factory=list)
    error: Optional[ErrorDetail] = Field(default=None)
