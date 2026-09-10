"""
SOVARA Multimodal Intelligence — Pipeline

Top-level orchestration layer for the multimodal subsystem.
Provides the public functions that the SOVARA orchestrator calls:

    extract_text(file_path)          → OCRResult
    analyze_image(image_path)        → ImageAnalysisResult
    analyze_document(file_path)      → DocumentAnalysisResult
    analyze_pid(image_path)          → PIDAnalysisResult
    answer_visual_question(image_path, question) → VisualQuestionAnswer
    analyze_documents(file_paths, task)           → MultiDocumentAnalysisResult
    reason_about_evidence(evidence, task)         → ReasoningResult

This module:
  1. Validates input files
  2. Routes to the correct processor based on file type
  3. Wraps all errors into structured responses
  4. Lazily initializes all engines on first use

The SOVARA orchestrator should treat these functions as a black box —
pass a file path, get structured JSON back.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

from multimodal.config import ErrorCode
from multimodal.schemas import (
    ConfidenceInfo,
    DocumentAnalysisResult,
    DocumentPageResult,
    ErrorDetail,
    Evidence,
    ImageAnalysisResult,
    MultiDocumentAnalysisResult,
    OCRPageResult,
    OCRResult,
    PIDAnalysisResult,
    ReasoningResult,
    VisualQuestionAnswer,
)
from multimodal.utils import FileType, detect_file_type, validate_file

logger = logging.getLogger("sovara.multimodal.pipeline")


# =============================================================================
# Lazy Engine Initialization
# =============================================================================
# All engines are created once on first use and reused.
# This avoids loading PaddleOCR models or connecting to Ollama
# until we actually need them.

_ocr_engine = None
_vision_model = None
_pdf_processor = None
_image_preprocessor = None
_document_analyzer = None
_pid_analyzer = None
_reasoning_engine = None


def _get_ocr_engine():
    """Get or create the singleton OCR engine."""
    global _ocr_engine
    if _ocr_engine is None:
        from multimodal.ocr import OCREngine
        _ocr_engine = OCREngine()
    return _ocr_engine


def _get_vision_model():
    """Get or create the singleton VLM wrapper."""
    global _vision_model
    if _vision_model is None:
        from multimodal.vision import VisionModel
        _vision_model = VisionModel()
    return _vision_model


def _get_pdf_processor():
    """Get or create the singleton PDF processor."""
    global _pdf_processor
    if _pdf_processor is None:
        from multimodal.pdf_processor import PDFProcessor
        _pdf_processor = PDFProcessor()
    return _pdf_processor


def _get_image_preprocessor():
    """Get or create the singleton image preprocessor."""
    global _image_preprocessor
    if _image_preprocessor is None:
        from multimodal.image_processor import ImagePreprocessor
        _image_preprocessor = ImagePreprocessor()
    return _image_preprocessor


def _get_document_analyzer():
    """Get or create the singleton document analyzer."""
    global _document_analyzer
    if _document_analyzer is None:
        from multimodal.document_analyzer import DocumentAnalyzer
        _document_analyzer = DocumentAnalyzer(
            pdf_processor=_get_pdf_processor(),
            ocr_engine=_get_ocr_engine(),
            vision_model=_get_vision_model(),
            image_preprocessor=_get_image_preprocessor(),
        )
    return _document_analyzer


def _get_pid_analyzer():
    """Get or create the singleton P&ID analyzer."""
    global _pid_analyzer
    if _pid_analyzer is None:
        from multimodal.pid_analyzer import PIDAnalyzer
        _pid_analyzer = PIDAnalyzer(
            ocr_engine=_get_ocr_engine(),
            vision_model=_get_vision_model(),
            image_preprocessor=_get_image_preprocessor(),
        )
    return _pid_analyzer


def _get_reasoning_engine():
    """Get or create the singleton reasoning engine."""
    global _reasoning_engine
    if _reasoning_engine is None:
        from multimodal.reasoning import ReasoningEngine
        _reasoning_engine = ReasoningEngine()
    return _reasoning_engine


# =============================================================================
# Public API Functions — Original
# =============================================================================

def extract_text(file_path: Union[str, Path]) -> OCRResult:
    """
    Extract text from a document or image using local OCR.

    This is the simplest entry point. It:
      - If the input is an image: runs OCR directly.
      - If the input is a PDF with selectable text: extracts it.
      - If the input is a scanned PDF: renders pages → OCR.

    Args:
        file_path: Path to the input file (PDF or image).

    Returns:
        OCRResult with extracted text, per-page breakdown, and
        confidence scores from PaddleOCR.

    Example:
        result = extract_text("document.pdf")
        if result.success:
            print(result.text)
            for page in result.pages:
                print(f"Page {page.page}: {page.confidence.score}")
    """
    file_path = Path(file_path)

    # --- Validate ---
    is_valid, error_code, error_msg = validate_file(file_path)
    if not is_valid:
        return OCRResult(
            success=False,
            source=file_path.name,
            error=ErrorDetail(code=error_code, message=error_msg),
        )

    file_type = detect_file_type(file_path)

    # --- Image: run OCR directly ---
    if file_type == FileType.IMAGE:
        logger.info("Extracting text from image: %s", file_path.name)
        return _get_ocr_engine().run_ocr(file_path)

    # --- PDF: extract text or OCR ---
    if file_type == FileType.PDF:
        logger.info("Extracting text from PDF: %s", file_path.name)
        pdf = _get_pdf_processor()

        try:
            is_scanned = pdf.is_scanned(file_path)
        except Exception:
            is_scanned = True

        if not is_scanned:
            # PDF has selectable text — extract directly
            try:
                text_pages = pdf.extract_text(file_path)
                pages = []
                all_text = []

                for page_data in text_pages:
                    page_text = page_data["text"]
                    all_text.append(page_text)
                    pages.append(OCRPageResult(
                        page=page_data["page"],
                        text=page_text,
                        # Deterministic extraction — not a probabilistic score.
                        # Confidence is NOT fabricated.
                        confidence=ConfidenceInfo(available=False),
                        word_count=len(page_text.split()),
                        language="extracted",
                    ))

                return OCRResult(
                    success=True,
                    text="\n".join(all_text),
                    pages=pages,
                    source=file_path.name,
                    text_type="printed",
                )
            except Exception as exc:
                logger.warning("Text extraction failed, falling back to OCR: %s", exc)
                is_scanned = True  # Fall through to OCR path

        if is_scanned:
            # Scanned PDF — render pages to images and OCR each one
            try:
                rendered_pages = pdf.render_pages(file_path)
                ocr_engine = _get_ocr_engine()
                preprocessor = _get_image_preprocessor()
                pages = []
                all_text = []

                for page_num, pil_image in enumerate(rendered_pages, start=1):
                    try:
                        preprocessed = preprocessor.preprocess_for_ocr(pil_image)
                        ocr_result = ocr_engine.run_ocr_on_pil_image(preprocessed)
                        ocr_result.page = page_num
                        pages.append(ocr_result)
                        all_text.append(ocr_result.text)
                    except Exception as exc:
                        logger.warning("OCR failed on page %d: %s", page_num, exc)
                        pages.append(OCRPageResult(
                            page=page_num,
                            text="",
                            confidence=ConfidenceInfo(available=False),
                        ))

                return OCRResult(
                    success=True,
                    text="\n".join(all_text),
                    pages=pages,
                    source=file_path.name,
                )
            except Exception as exc:
                return OCRResult(
                    success=False,
                    source=file_path.name,
                    error=ErrorDetail(
                        code=ErrorCode.PDF_CORRUPTED,
                        message=f"Failed to render PDF pages: {exc}",
                    ),
                )

    # --- CSV: Read as text ---
    if file_type == FileType.CSV:
        logger.info("Extracting text from CSV: %s", file_path.name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            return OCRResult(
                success=True,
                text=text,
                pages=[
                    OCRPageResult(
                        page=1,
                        text=text,
                        # Deterministic file read — not probabilistic.
                        confidence=ConfidenceInfo(available=False),
                        word_count=len(text.split()),
                        language="extracted",
                    )
                ],
                source=file_path.name,
                text_type="data",
            )
        except Exception as exc:
            return OCRResult(
                success=False,
                source=file_path.name,
                error=ErrorDetail(
                    code=ErrorCode.FILE_CORRUPTED,
                    message=f"Failed to read CSV file: {exc}",
                ),
            )

    # --- Unknown file type ---
    return OCRResult(
        success=False,
        source=file_path.name,
        error=ErrorDetail(
            code=ErrorCode.UNSUPPORTED_FILE_TYPE,
            message=f"Unsupported file type: {file_path.suffix}",
        ),
    )


def analyze_image(image_path: Union[str, Path]) -> ImageAnalysisResult:
    """
    Analyze an image using the local VLM.

    Sends the image to Qwen2.5-VL via Ollama for visual understanding.
    The model separates observations (directly visible) from inferences
    (interpretations).

    Args:
        image_path: Path to the image file.

    Returns:
        ImageAnalysisResult with description, objects, observations
        (tagged as observed/inferred), text content, and uncertainties.

    Example:
        result = analyze_image("inspection.jpg")
        if result.success:
            for obs in result.observations:
                print(f"[{obs.type}] {obs.content}")
    """
    image_path = Path(image_path)

    # --- Validate ---
    is_valid, error_code, error_msg = validate_file(image_path)
    if not is_valid:
        return ImageAnalysisResult(
            success=False,
            image=image_path.name,
            error=ErrorDetail(code=error_code, message=error_msg),
        )

    file_type = detect_file_type(image_path)
    if file_type != FileType.IMAGE:
        return ImageAnalysisResult(
            success=False,
            image=image_path.name,
            error=ErrorDetail(
                code=ErrorCode.UNSUPPORTED_FILE_TYPE,
                message=f"Expected an image file, got: {image_path.suffix}",
            ),
        )

    logger.info("Analyzing image with VLM: %s", image_path.name)
    return _get_vision_model().analyze_image(image_path)


def analyze_document(file_path: Union[str, Path]) -> DocumentAnalysisResult:
    """
    Perform comprehensive document analysis.

    Combines PDF text extraction, OCR (for scanned pages), and VLM
    analysis (for embedded images) into a unified document representation.

    For images, treats the image as a single-page document and runs
    both OCR and VLM analysis.

    Args:
        file_path: Path to the document (PDF or image).

    Returns:
        DocumentAnalysisResult with per-page text, visual observations,
        tables, and figures.

    Example:
        result = analyze_document("inspection_report.pdf")
        if result.success:
            for page in result.pages:
                print(f"Page {page.page}: {len(page.text)} chars")
                for fig in page.figures:
                    print(f"  Figure: {fig.description}")
    """
    file_path = Path(file_path)

    # --- Validate ---
    is_valid, error_code, error_msg = validate_file(file_path)
    if not is_valid:
        return DocumentAnalysisResult(
            success=False,
            document=file_path.name,
            error=ErrorDetail(code=error_code, message=error_msg),
        )

    logger.info("Analyzing document: %s", file_path.name)
    return _get_document_analyzer().analyze(file_path)


def analyze_pid(image_path: Union[str, Path]) -> PIDAnalysisResult:
    """
    Analyze a P&ID (Piping & Instrumentation Diagram) image.

    Uses a multi-stage pipeline:
      1. Image preprocessing (enhance lines, contrast)
      2. OCR to extract equipment tags and labels
      3. Regex-based tag parsing (P-101, FT-301, etc.)
      4. VLM visual analysis of components and connections
      5. Merge OCR and VLM results
      6. Evidence provenance tracking

    Args:
        image_path: Path to the P&ID image.

    Returns:
        PIDAnalysisResult with equipment, valves, instruments, pipes,
        connections, and explicit uncertainty markers.

    Example:
        result = analyze_pid("process_pid.png")
        if result.success:
            for eq in result.equipment:
                print(f"{eq.tag}: {eq.type} (uncertain={eq.uncertain})")
    """
    image_path = Path(image_path)

    # --- Validate ---
    is_valid, error_code, error_msg = validate_file(image_path)
    if not is_valid:
        return PIDAnalysisResult(
            success=False,
            source=image_path.name,
            error=ErrorDetail(code=error_code, message=error_msg),
        )

    file_type = detect_file_type(image_path)
    if file_type != FileType.IMAGE:
        return PIDAnalysisResult(
            success=False,
            source=image_path.name,
            error=ErrorDetail(
                code=ErrorCode.UNSUPPORTED_FILE_TYPE,
                message=f"Expected an image file, got: {image_path.suffix}",
            ),
        )

    logger.info("Analyzing P&ID: %s", image_path.name)
    return _get_pid_analyzer().analyze(image_path)


# =============================================================================
# Public API Functions — New
# =============================================================================

def answer_visual_question(
    image_path: Union[str, Path],
    question: str,
) -> VisualQuestionAnswer:
    """
    Answer a visual question about an image.

    Uses VLM to visually analyze the image and an optional reasoning
    model to synthesize the answer. Returns structured output with
    evidence, observations, inferences, and explicit uncertainties.

    The answer is grounded only in available visual evidence.
    No information is fabricated.

    Args:
        image_path: Path to the image file.
        question: The question to answer about the image.

    Returns:
        VisualQuestionAnswer with answer, evidence, and uncertainty info.

    Example:
        result = answer_visual_question(
            "pid.png",
            "What equipment appears downstream of P-101?"
        )
        if result.success:
            print(result.answer)
            for obs in result.observations:
                print(f"  Observed: {obs}")
    """
    image_path = Path(image_path)

    # --- Validate ---
    is_valid, error_code, error_msg = validate_file(image_path)
    if not is_valid:
        return VisualQuestionAnswer(
            success=False,
            question=question,
            error=ErrorDetail(code=error_code, message=error_msg),
        )

    file_type = detect_file_type(image_path)
    if file_type != FileType.IMAGE:
        return VisualQuestionAnswer(
            success=False,
            question=question,
            error=ErrorDetail(
                code=ErrorCode.UNSUPPORTED_FILE_TYPE,
                message=f"Expected an image file, got: {image_path.suffix}",
            ),
        )

    logger.info("Visual QA on %s: %s", image_path.name, question[:80])

    vlm = _get_vision_model()

    # --- Step 1: VLM visual question answering ---
    vlm_result = vlm.answer_question(image_path, question)

    # --- Step 2: OCR for text evidence ---
    ocr_text = ""
    try:
        ocr_result = _get_ocr_engine().run_ocr(image_path)
        if ocr_result.success:
            ocr_text = ocr_result.text
    except Exception as exc:
        logger.warning("OCR for VQA failed: %s", exc)

    # --- Build evidence ---
    evidence: list[Evidence] = []

    # OCR evidence
    if ocr_text.strip():
        evidence.append(Evidence(
            source=image_path.name,
            type="ocr",
            text=ocr_text,
            originating_subsystem="paddleocr",
            direct_observation=True,
        ))

    # VLM evidence
    for obs in vlm_result.get("observations", []):
        evidence.append(Evidence(
            source=image_path.name,
            type="vlm",
            visual_description=obs,
            originating_subsystem="ollama_vlm",
            direct_observation=True,
        ))

    # Check for VLM error
    vlm_error = vlm_result.get("error")
    if vlm_error:
        return VisualQuestionAnswer(
            success=False,
            question=question,
            error=vlm_error if isinstance(vlm_error, ErrorDetail) else ErrorDetail(
                code=ErrorCode.VLM_UNAVAILABLE,
                message=str(vlm_error),
            ),
        )

    return VisualQuestionAnswer(
        success=True,
        question=question,
        answer=vlm_result.get("answer", ""),
        evidence=evidence,
        observations=vlm_result.get("observations", []),
        inferences=vlm_result.get("inferences", []),
        uncertainties=vlm_result.get("uncertainties", []),
        confidence=ConfidenceInfo(available=False),
    )


def analyze_documents(
    file_paths: list[Union[str, Path]],
    task: str,
) -> MultiDocumentAnalysisResult:
    """
    Analyze multiple documents together for a given task.

    Processes each document individually, then performs cross-document
    reasoning to identify:
      - Shared entities across sources
      - Recurring observations
      - Contradictions between sources
      - Evidence-grounded findings
      - Cautious hypotheses with explicit uncertainty

    Args:
        file_paths: List of paths to documents/images.
        task: The analytical task or question.

    Returns:
        MultiDocumentAnalysisResult with findings, hypotheses,
        contradictions, and unresolved questions.

    Example:
        result = analyze_documents(
            ["pid.png", "inspection.pdf", "maintenance.pdf"],
            "Identify recurring issues with pump P-101."
        )
    """
    if not file_paths:
        return MultiDocumentAnalysisResult(
            success=False,
            task=task,
            error=ErrorDetail(
                code=ErrorCode.EMPTY_RESULT,
                message="No files provided for analysis",
            ),
        )

    logger.info("Multi-document analysis: %d files, task: %s", len(file_paths), task[:80])

    sources: list[str] = []
    source_evidence: dict[str, list[Evidence]] = {}
    warnings: list[str] = []

    # --- Step 1: Process each document ---
    for fp in file_paths:
        fp = Path(fp)
        source_name = fp.name
        sources.append(source_name)

        file_type = detect_file_type(fp)

        try:
            if file_type == FileType.IMAGE:
                # Image — use VLM analysis
                img_result = _get_vision_model().analyze_image_deep(fp)
                ev_list = []

                if img_result.success:
                    # Observations as evidence
                    for obs in img_result.observations:
                        ev_list.append(Evidence(
                            source=source_name,
                            type="vlm",
                            visual_description=obs.content,
                            originating_subsystem="ollama_vlm",
                            direct_observation=(obs.type == "observed"),
                        ))
                    # Text content from image
                    for text in img_result.text_content:
                        ev_list.append(Evidence(
                            source=source_name,
                            type="vlm",
                            text=text,
                            originating_subsystem="ollama_vlm",
                            direct_observation=True,
                        ))

                # Also OCR the image
                try:
                    ocr_result = _get_ocr_engine().run_ocr(fp)
                    if ocr_result.success and ocr_result.text.strip():
                        ev_list.append(Evidence(
                            source=source_name,
                            type="ocr",
                            text=ocr_result.text,
                            originating_subsystem="paddleocr",
                            direct_observation=True,
                        ))
                except Exception as exc:
                    logger.warning("OCR failed for %s: %s", source_name, exc)

                source_evidence[source_name] = ev_list

            elif file_type == FileType.PDF:
                # PDF — full document analysis
                doc_result = _get_document_analyzer().analyze(fp)
                ev_list = []

                if doc_result.success:
                    for page in doc_result.pages:
                        if page.text.strip():
                            ev_list.append(Evidence(
                                source=source_name,
                                page=page.page,
                                type="text_extraction" if not page.visual_observations else "ocr",
                                text=page.text,
                                originating_subsystem="pymupdf",
                                direct_observation=True,
                            ))
                        for obs in page.visual_observations:
                            ev_list.append(Evidence(
                                source=source_name,
                                page=page.page,
                                type="vlm",
                                visual_description=obs.content,
                                originating_subsystem="ollama_vlm",
                                direct_observation=(obs.type == "observed"),
                            ))

                source_evidence[source_name] = ev_list

            else:
                warnings.append(f"Unsupported file type: {source_name}")
                source_evidence[source_name] = []

        except Exception as exc:
            logger.error("Failed to process %s: %s", source_name, exc)
            warnings.append(f"Failed to process {source_name}: {exc}")
            source_evidence[source_name] = []

    # --- Step 2: Cross-document reasoning ---
    from multimodal.evidence import (
        detect_contradictions,
        group_evidence_by_entity,
        deduplicate_evidence,
    )

    all_evidence = []
    for ev_list in source_evidence.values():
        all_evidence.extend(ev_list)
    all_evidence = deduplicate_evidence(all_evidence)

    # Detect contradictions
    evidence_groups = group_evidence_by_entity(all_evidence)
    contradictions = detect_contradictions(evidence_groups)

    # --- Step 3: Reasoning model for synthesis ---
    reasoning = _get_reasoning_engine()
    findings = []
    hypotheses = []
    unresolved = []

    if reasoning.is_available():
        try:
            reasoning_result = reasoning.reason_across_documents(
                source_evidence, task
            )
            if reasoning_result.success:
                findings = reasoning_result.findings
                hypotheses = reasoning_result.hypotheses
                unresolved = reasoning_result.uncertainties

                # Add reasoning contradictions
                for c in reasoning_result.contradictions:
                    if c not in contradictions:
                        contradictions.append(c)
        except Exception as exc:
            logger.warning("Cross-document reasoning failed: %s", exc)
            warnings.append(f"Reasoning model analysis failed: {exc}")
    else:
        warnings.append(
            "Reasoning model unavailable — returning evidence-only results"
        )

    return MultiDocumentAnalysisResult(
        success=True,
        task=task,
        sources=sources,
        findings=findings,
        hypotheses=hypotheses,
        contradictions=contradictions,
        unresolved_questions=unresolved,
        warnings=warnings,
    )


def reason_about_evidence(
    evidence: list[Evidence],
    task: str,
) -> ReasoningResult:
    """
    Perform analytical reasoning over supplied evidence.

    Takes pre-extracted evidence (from OCR, VLM, documents) and a
    focused analytical task, then returns structured reasoning output
    with observations, inferences, hypotheses, findings, and
    contradictions.

    This function does NOT perform retrieval, planning, or tool execution.
    It receives evidence and returns analysis.

    Args:
        evidence: List of Evidence objects to reason about.
        task: The analytical task or question.

    Returns:
        ReasoningResult with structured analytical output.

    Example:
        result = reason_about_evidence(
            evidence_list,
            "What recurring issues are associated with P-101?"
        )
    """
    logger.info("Reasoning about %d evidence items: %s", len(evidence), task[:80])

    reasoning = _get_reasoning_engine()
    return reasoning.analyze_evidence(evidence, task)


# =============================================================================
# CLI Demo
# =============================================================================

if __name__ == "__main__":
    import json
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python -m multimodal.pipeline <file_path> [--pid] [--vqa <question>]")
        print()
        print("Examples:")
        print("  python -m multimodal.pipeline document.pdf")
        print("  python -m multimodal.pipeline image.png")
        print("  python -m multimodal.pipeline pid_drawing.png --pid")
        print('  python -m multimodal.pipeline image.png --vqa "What equipment is visible?"')
        sys.exit(1)

    file_path = sys.argv[1]
    is_pid = "--pid" in sys.argv

    # Check for VQA mode
    if "--vqa" in sys.argv:
        vqa_idx = sys.argv.index("--vqa")
        if vqa_idx + 1 < len(sys.argv):
            question = sys.argv[vqa_idx + 1]
            result = answer_visual_question(file_path, question)
        else:
            print("Error: --vqa requires a question argument")
            sys.exit(1)
    elif is_pid:
        result = analyze_pid(file_path)
    elif detect_file_type(file_path) == FileType.IMAGE:
        result = analyze_image(file_path)
    else:
        result = analyze_document(file_path)

    # Pretty-print the result as JSON
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
