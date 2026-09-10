"""
SOVARA Multimodal Intelligence — Document Analyzer

Combined document analysis that merges:
  - PDF text extraction (selectable text)
  - OCR (for scanned pages)
  - VLM image analysis (for embedded images / visual content)

Pipeline for PDF documents:
    1. Open PDF
    2. Check if scanned or text-based
    3. Extract selectable text (if available)
    4. If scanned: render pages → OCR
    5. Extract embedded images → VLM analysis
    6. Combine everything into DocumentAnalysisResult

Pipeline for images:
    1. Preprocess image
    2. OCR for text extraction
    3. VLM for visual understanding
    4. Combine into DocumentAnalysisResult (single "page")
"""

from __future__ import annotations

import logging
from pathlib import Path

from multimodal.config import ErrorCode
from typing import Optional

from multimodal.evidence import extract_entities_from_text
from multimodal.schemas import (
    ConfidenceInfo,
    DocumentAnalysisResult,
    DocumentPageResult,
    ErrorDetail,
    FigureInfo,
    Observation,
    TableInfo,
)
from multimodal.utils import FileType, detect_file_type

logger = logging.getLogger("sovara.multimodal.document_analyzer")


class DocumentAnalyzer:
    """
    Combines PDF processing, OCR, and VLM analysis into a unified
    document analysis pipeline.

    This is the "brain" that orchestrates the individual engines
    (pdf_processor, ocr, vision, image_processor) to produce
    a comprehensive analysis of any document.

    Usage:
        analyzer = DocumentAnalyzer(pdf_processor, ocr_engine, vision_model, image_preprocessor)
        result = analyzer.analyze("path/to/document.pdf")
    """

    def __init__(self, pdf_processor, ocr_engine, vision_model, image_preprocessor):
        """
        Args:
            pdf_processor: PDFProcessor instance (from pdf_processor.py).
            ocr_engine: OCREngine instance (from ocr.py).
            vision_model: VisionModel instance (from vision.py).
            image_preprocessor: ImagePreprocessor instance (from image_processor.py).
        """
        self.pdf = pdf_processor
        self.ocr = ocr_engine
        self.vlm = vision_model
        self.preprocessor = image_preprocessor

    def analyze(self, file_path: str | Path) -> DocumentAnalysisResult:
        """
        Analyze a document (PDF or image) and return structured results.

        Automatically detects whether the input is a PDF or image and
        routes to the appropriate analysis pipeline.

        Args:
            file_path: Path to the document.

        Returns:
            DocumentAnalysisResult with per-page text, observations,
            tables, and figures.
        """
        file_path = Path(file_path)
        source_name = file_path.name
        file_type = detect_file_type(file_path)

        logger.info("Analyzing document: %s (type: %s)", source_name, file_type)

        if file_type == FileType.PDF:
            return self._analyze_pdf(file_path, source_name)
        elif file_type == FileType.IMAGE:
            return self._analyze_image_as_document(file_path, source_name)
        elif file_type == FileType.CSV:
            return self._analyze_csv(file_path, source_name)
        else:
            return DocumentAnalysisResult(
                success=False,
                document=source_name,
                error=ErrorDetail(
                    code=ErrorCode.UNSUPPORTED_FILE_TYPE,
                    message=f"Cannot analyze file type: {file_path.suffix}",
                ),
            )

    # =====================================================================
    # CSV Analysis
    # =====================================================================

    def _analyze_csv(self, csv_path: Path, source_name: str) -> DocumentAnalysisResult:
        """
        Analyze a CSV file.
        Treats the CSV as a single page document containing data text.
        """
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            page_result = DocumentPageResult(
                page=1,
                text=text,
                tables=[],
                figures=[],
            )
            
            return DocumentAnalysisResult(
                success=True,
                document=source_name,
                pages=[page_result],
            )
        except Exception as exc:
            return DocumentAnalysisResult(
                success=False,
                document=source_name,
                error=ErrorDetail(
                    code=ErrorCode.FILE_CORRUPTED,
                    message=f"Cannot read CSV file: {exc}",
                ),
            )

    # =====================================================================
    # PDF Analysis
    # =====================================================================

    def _analyze_pdf(
        self, pdf_path: Path, source_name: str
    ) -> DocumentAnalysisResult:
        """
        Full analysis pipeline for PDF documents.

        1. Get page count
        2. Check if scanned
        3. Extract text or OCR each page
        4. Extract embedded images
        5. Optionally analyze images with VLM
        """
        warnings: list[str] = []

        # --- Get page count ---
        try:
            page_count = self.pdf.get_page_count(pdf_path)
        except Exception as exc:
            return DocumentAnalysisResult(
                success=False,
                document=source_name,
                error=ErrorDetail(
                    code=ErrorCode.PDF_CORRUPTED,
                    message=f"Cannot open PDF: {exc}",
                ),
            )

        logger.info("PDF has %d pages", page_count)

        # --- Determine if scanned ---
        try:
            is_scanned = self.pdf.is_scanned(pdf_path)
        except Exception:
            is_scanned = True  # Assume scanned if detection fails
            warnings.append("Could not determine if PDF is scanned — assuming scanned")

        if is_scanned:
            logger.info("PDF appears to be scanned — will use OCR")
        else:
            logger.info("PDF has selectable text")

        # --- Extract text (selectable or OCR) ---
        pages: list[DocumentPageResult] = []

        if not is_scanned:
            # --- Text-based PDF: extract selectable text ---
            try:
                text_pages = self.pdf.extract_text(pdf_path)
                for page_data in text_pages:
                    pages.append(DocumentPageResult(
                        page=page_data["page"],
                        text=page_data["text"],
                        confidence=ConfidenceInfo(available=False),
                    ))
            except Exception as exc:
                logger.warning("Text extraction failed, falling back to OCR: %s", exc)
                is_scanned = True  # Fall back to OCR
                warnings.append(f"Text extraction failed: {exc}")

        if is_scanned:
            # --- Scanned PDF: render pages and OCR each one ---
            try:
                rendered_pages = self.pdf.render_pages(pdf_path)
                for page_num, pil_image in enumerate(rendered_pages, start=1):
                    try:
                        # Preprocess for better OCR
                        preprocessed = self.preprocessor.preprocess_for_ocr(pil_image)
                        ocr_page = self.ocr.run_ocr_on_pil_image(preprocessed)

                        pages.append(DocumentPageResult(
                            page=page_num,
                            text=ocr_page.text,
                            confidence=ocr_page.confidence,
                        ))
                    except Exception as exc:
                        logger.warning("OCR failed on page %d: %s", page_num, exc)
                        pages.append(DocumentPageResult(
                            page=page_num,
                            text="",
                            confidence=ConfidenceInfo(available=False),
                        ))
                        warnings.append(f"OCR failed on page {page_num}: {exc}")
            except Exception as exc:
                logger.error("Failed to render PDF pages: %s", exc)
                warnings.append(f"Page rendering failed: {exc}")

        # --- Extract and analyze embedded images ---
        try:
            embedded_images = self.pdf.extract_images(pdf_path)
            for img_info in embedded_images:
                page_num = img_info["page"]
                pil_image = img_info["image"]

                # Try to get VLM description of the figure
                description = ""
                if self.vlm.is_available():
                    try:
                        description = self.vlm.describe_figure_from_pil(pil_image)
                    except Exception as exc:
                        logger.debug("VLM figure description failed: %s", exc)

                figure = FigureInfo(
                    page=page_num,
                    index=img_info["index"],
                    description=description,
                    width=img_info.get("width", 0),
                    height=img_info.get("height", 0),
                )

                # Add figure to the correct page
                for page_result in pages:
                    if page_result.page == page_num:
                        page_result.figures.append(figure)
                        break
                else:
                    # Page not in our results yet (shouldn't happen normally)
                    if page_num <= page_count:
                        pages.append(DocumentPageResult(
                            page=page_num,
                            figures=[figure],
                        ))

        except Exception as exc:
            logger.warning("Image extraction from PDF failed: %s", exc)
            warnings.append(f"Could not extract embedded images: {exc}")

        # --- Post-process pages ---
        for page_result in pages:
            if not hasattr(page_result, 'tables') or page_result.tables is None:
                page_result.tables = []
            if not hasattr(page_result, 'figures') or page_result.figures is None:
                page_result.figures = []
            if not hasattr(page_result, 'entities') or page_result.entities is None:
                page_result.entities = []

            if page_result.text:
                page_result.tables = self._detect_tables(page_result.text, page_result.page)
                page_result.entities = extract_entities_from_text(page_result.text)

            page_result.has_tables = len(page_result.tables) > 0
            page_result.has_images = len(page_result.figures) > 0

            # Content type detection per page
            if page_result.text and page_result.figures:
                page_result.content_type = 'mixed'
            elif is_scanned:
                page_result.content_type = 'scanned'
            else:
                page_result.content_type = 'text'

        # --- Sort pages by page number ---
        pages.sort(key=lambda p: p.page)

        return DocumentAnalysisResult(
            success=True,
            document=source_name,
            page_count=page_count,
            pages=pages,
            warnings=warnings,
        )

    # =====================================================================
    # Image-as-Document Analysis
    # =====================================================================

    def _analyze_image_as_document(
        self, image_path: Path, source_name: str
    ) -> DocumentAnalysisResult:
        """
        Analyze a standalone image as a single-page "document".

        Runs both OCR and VLM analysis, combining their results
        into a single DocumentPageResult.
        """
        warnings: list[str] = []
        text = ""
        confidence = ConfidenceInfo(available=False)
        observations: list[Observation] = []

        # --- OCR pass ---
        try:
            from PIL import Image
            pil_image = Image.open(image_path)
            preprocessed = self.preprocessor.preprocess_for_ocr(pil_image)
            ocr_result = self.ocr.run_ocr_on_pil_image(preprocessed)
            text = ocr_result.text
            confidence = ocr_result.confidence
        except Exception as exc:
            logger.warning("OCR on image failed: %s", exc)
            warnings.append(f"OCR failed: {exc}")

        # --- VLM pass ---
        if self.vlm.is_available():
            try:
                vlm_result = self.vlm.analyze_image(image_path)
                if vlm_result.success:
                    observations = vlm_result.observations
            except Exception as exc:
                logger.warning("VLM analysis failed: %s", exc)
                warnings.append(f"VLM analysis failed: {exc}")

        page = DocumentPageResult(
            page=1,
            text=text,
            visual_observations=observations,
            confidence=confidence,
        )

        return DocumentAnalysisResult(
            success=True,
            document=source_name,
            page_count=1,
            pages=[page],
            warnings=warnings,
        )

    def _detect_tables(self, text: str, page_num: int) -> list[TableInfo]:
        """Detect and extract tables from page text.
        
        Uses simple heuristics to identify tabular data:
        - Lines with consistent delimiter patterns (|, tabs)
        - Lines with consistent column-like spacing
        
        This is a basic implementation. Complex table structures
        may not be accurately recovered.
        """
        tables = []
        if not text:
            return tables
            
        lines = text.strip().split('\n')
        
        # Try pipe-delimited tables
        table_lines = []
        for line in lines:
            if '|' in line and line.count('|') >= 2:
                table_lines.append(line)
            elif table_lines and len(table_lines) >= 2:
                table = self._parse_pipe_table(table_lines, page_num)
                if table:
                    tables.append(table)
                table_lines = []
            else:
                table_lines = []
        
        if table_lines and len(table_lines) >= 2:
            table = self._parse_pipe_table(table_lines, page_num)
            if table:
                tables.append(table)
        
        # Try tab-delimited tables
        tab_lines = []
        for line in lines:
            if '\t' in line and line.count('\t') >= 1:
                tab_lines.append(line)
            elif tab_lines and len(tab_lines) >= 2:
                table = self._parse_tab_table(tab_lines, page_num)
                if table:
                    tables.append(table)
                tab_lines = []
            else:
                tab_lines = []
        
        if tab_lines and len(tab_lines) >= 2:
            table = self._parse_tab_table(tab_lines, page_num)
            if table:
                tables.append(table)
        
        return tables
    
    def _parse_pipe_table(self, lines: list[str], page_num: int) -> Optional[TableInfo]:
        """Parse pipe-delimited table lines."""
        try:
            rows = []
            for line in lines:
                cells = [c.strip() for c in line.split('|') if c.strip()]
                if cells:
                    rows.append(cells)
            
            if len(rows) < 2:
                return None
            
            # Check if second row is a separator (---)
            headers = rows[0]
            data_start = 1
            if rows[1] and all(set(c.strip()).issubset({'-', ':', ' '}) for c in rows[1]):
                data_start = 2
            
            data_rows = rows[data_start:]
            
            return TableInfo(
                page=page_num,
                content='\n'.join(lines),
                headers=headers,
                rows=data_rows,
                structured=True,
                confidence=ConfidenceInfo(available=False),
            )
        except Exception:
            return TableInfo(
                page=page_num,
                content='\n'.join(lines),
                structured=False,
                confidence=ConfidenceInfo(available=False),
            )
    
    def _parse_tab_table(self, lines: list[str], page_num: int) -> Optional[TableInfo]:
        """Parse tab-delimited table lines."""
        try:
            rows = []
            for line in lines:
                cells = [c.strip() for c in line.split('\t') if c.strip()]
                if cells:
                    rows.append(cells)
            
            if len(rows) < 2:
                return None
            
            headers = rows[0]
            data_rows = rows[1:]
            
            return TableInfo(
                page=page_num,
                content='\n'.join(lines),
                headers=headers,
                rows=data_rows,
                structured=True,
                confidence=ConfidenceInfo(available=False),
            )
        except Exception:
            return TableInfo(
                page=page_num,
                content='\n'.join(lines),
                structured=False,
                confidence=ConfidenceInfo(available=False),
            )
