"""
SOVARA Multimodal Intelligence - OCR Engine

EasyOCR wrapper that provides local, GPU-free text extraction
from images and rendered PDF pages.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union
import contextlib

import numpy as np
from pydantic import BaseModel, Field

from multimodal import config
from multimodal.schemas import (
    ConfidenceInfo,
    ErrorDetail,
    OCRPageResult,
    OCRResult,
)

logger = logging.getLogger("sovara.multimodal.ocr")

class OCRLine(BaseModel):
    """A single line of OCR output with position data."""
    text: str = Field(default="", description="Extracted text")
    confidence: float = Field(default=0.0, description="OCR confidence 0-1")
    bbox: Optional[list[float]] = Field(default=None, description="Bounding box [x1,y1,x2,y2]")

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    from PIL import Image
except ImportError:
    Image = None


class OCREngine:
    def __init__(self) -> None:
        self._engines: dict[str, object] = {}

    def _get_engine(self, lang: str) -> "easyocr.Reader":
        if easyocr is None:
            raise RuntimeError("EasyOCR is not installed.")

        if lang not in self._engines:
            logger.info("Initializing EasyOCR engine for language: %s", lang)
            # map lang to easyocr supported language codes if needed
            
            with open(os.devnull, "w", encoding="utf-8") as f, contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
                self._engines[lang] = easyocr.Reader([lang], gpu=False)
                
            logger.info("EasyOCR engine ready for: %s", lang)

        return self._engines[lang]

    def _run_single_ocr(
        self, image_input: Union[str, np.ndarray], lang: str
    ) -> tuple[str, float, int, list[OCRLine]]:
        engine = self._get_engine(lang)

        try:
            results = engine.readtext(image_input)
        except Exception as exc:
            logger.error("EasyOCR engine error (%s): %s", lang, exc)
            return "", 0.0, 0, []

        if not results:
            return "", 0.0, 0, []

        texts: list[str] = []
        confidences: list[float] = []
        ocr_lines: list[OCRLine] = []

        for line in results:
            try:
                box_coords = line[0]
                text_str = line[1]
                conf_float = float(line[2])
                
                if text_str.strip():
                    texts.append(text_str)
                    confidences.append(conf_float)
                    ocr_lines.append(OCRLine(
                        text=text_str,
                        confidence=conf_float,
                        bbox=[float(box_coords[0][0]), float(box_coords[0][1]), float(box_coords[2][0]), float(box_coords[2][1])]
                    ))
            except Exception as e:
                logger.warning(f"Error parsing OCR line: {e}")

        if not texts:
            return "", 0.0, 0, []

        extracted_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        word_count = len(extracted_text.split())

        return extracted_text, avg_confidence, word_count, ocr_lines

    def run_ocr_on_pil_image(
        self, image: "Image.Image", lang: Optional[str] = None
    ) -> OCRPageResult:
        target_lang = lang or config.OCR_LANG
        try:
            img_array = np.array(image.convert("RGB"))
            text, avg_conf, word_count, _ = self._run_single_ocr(img_array, target_lang)
            if word_count > 0:
                confidence = ConfidenceInfo(available=True, score=round(avg_conf, 4))
            else:
                confidence = ConfidenceInfo(available=False)
            return OCRPageResult(text=text, confidence=confidence, word_count=word_count, language=target_lang)
        except Exception as exc:
            logger.error("OCR on PIL image failed: %s", exc)
            return OCRPageResult(text="", confidence=ConfidenceInfo(available=False), word_count=0, language=target_lang)

    def run_ocr_with_boxes(self, image_input: Union[str, np.ndarray, "Image.Image"], lang: Optional[str] = None) -> tuple[OCRPageResult, list[OCRLine]]:
        target_lang = lang or config.OCR_LANG
        try:
            if Image and isinstance(image_input, Image.Image):
                img_input = np.array(image_input.convert("RGB"))
            else:
                img_input = image_input
                
            text, avg_conf, word_count, ocr_lines = self._run_single_ocr(img_input, target_lang)
            if word_count > 0:
                confidence = ConfidenceInfo(available=True, score=round(avg_conf, 4))
            else:
                confidence = ConfidenceInfo(available=False)
            page_result = OCRPageResult(text=text, confidence=confidence, word_count=word_count, language=target_lang)
            return page_result, ocr_lines
        except Exception as exc:
            logger.error("OCR with boxes failed: %s", exc)
            return OCRPageResult(text="", confidence=ConfidenceInfo(available=False), word_count=0, language=target_lang), []

    def run_ocr(self, image_path: Union[str, Path]) -> OCRResult:
        img_path = Path(image_path)
        if not img_path.exists():
            return OCRResult(
                success=False,
                source=img_path.name,
                error=ErrorDetail(code=config.ErrorCode.FILE_NOT_FOUND, message=f"Image file not found: {img_path}")
            )

        path_str = str(img_path)
        primary_lang = config.OCR_LANG
        pages: list[OCRPageResult] = []
        warnings: list[str] = []

        try:
            text, avg_conf, word_count, _ = self._run_single_ocr(path_str, primary_lang)
            if word_count > 0:
                confidence = ConfidenceInfo(available=True, score=round(avg_conf, 4))
            else:
                confidence = ConfidenceInfo(available=False)
            pages.append(OCRPageResult(page=1, text=text, confidence=confidence, word_count=word_count, language=primary_lang))
        except RuntimeError as exc:
            return OCRResult(success=False, source=img_path.name, error=ErrorDetail(code=config.ErrorCode.OCR_ENGINE_UNAVAILABLE, message=str(exc)))
        except Exception as exc:
            logger.error("Primary OCR failed: %s", exc)
            warnings.append(f"Primary OCR ({primary_lang}) failed: {exc}")

        additional_langs_str = config.OCR_ADDITIONAL_LANGS
        if additional_langs_str:
            additional_langs = [lang.strip() for lang in additional_langs_str.split(",") if lang.strip() and lang.strip() != primary_lang]
            for lang in additional_langs:
                try:
                    alt_text, alt_conf, alt_wc, _ = self._run_single_ocr(path_str, lang)
                    if alt_wc > 0:
                        pages.append(OCRPageResult(page=1, text=alt_text, confidence=ConfidenceInfo(available=True, score=round(alt_conf, 4)), word_count=alt_wc, language=lang))
                except Exception as exc:
                    logger.warning("Additional OCR (%s) failed: %s", lang, exc)
                    warnings.append(f"OCR for '{lang}' failed: {exc}")

        all_texts = [p.text for p in pages if p.text.strip()]
        merged_text = "\n".join(all_texts)
        avg_scores = [p.confidence.score for p in pages if p.confidence.available and p.confidence.score is not None]
        overall_avg = (sum(avg_scores) / len(avg_scores) if avg_scores else 0.0)
        if overall_avg < 0.4:
            text_type = "handwritten"
        elif overall_avg < 0.6:
            text_type = "mixed"
        else:
            text_type = "printed"

        return OCRResult(
            success=True,
            text=merged_text,
            pages=pages,
            source=img_path.name,
            text_type=text_type,
            warnings=warnings
        )
