"""
SOVARA Multimodal Intelligence — P&ID Analyzer

Multi-stage pipeline for analyzing Piping & Instrumentation Diagrams:

    P&ID Image
       ↓
    1. Image Preprocessing (enhance lines, contrast)
       ↓
    2. OCR Pass (extract all text/tags/labels)
       ↓
    3. Tag Parsing (regex-based equipment tag extraction)
       ↓
    4. VLM Analysis (visual understanding of components)
       ↓
    5. Merge (cross-reference OCR tags with VLM detections)
       ↓
    6. Confidence Assignment (per-component confidence)
       ↓
    7. Structured P&ID JSON

IMPORTANT: P&ID analysis is inherently uncertain. This module explicitly
marks uncertain identifications rather than pretending to be perfect.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from multimodal.config import ErrorCode
from multimodal.schemas import (
    ConfidenceInfo,
    ErrorDetail,
    Evidence,
    Observation,
    PIDAnalysisResult,
    PIDConnection,
    PIDEquipment,
    PIDInstrument,
    PIDPipe,
    PIDValve,
)

logger = logging.getLogger("sovara.multimodal.pid_analyzer")


# =============================================================================
# Equipment Tag Patterns
# =============================================================================
# These regex patterns match common ISA/ISO tag formats found in P&IDs.
# Each pattern captures the tag prefix and number.

TAG_PATTERNS: dict[str, re.Pattern] = {
    # --- Equipment ---
    # P-101 = Pump, V-201 = Vessel, T-301 = Tank/Tower, R-401 = Reactor
    # E-501 = Heat Exchanger, C-601 = Compressor, D-701 = Drum
    "equipment": re.compile(
        r"\b([PVTRECDH])-(\d{2,4}[A-Z]?(?:/[A-Z])?)\b"
    ),

    # --- Valves ---
    # XV-101 = On/Off valve, CV-201 = Control valve, HV-301 = Hand valve
    # BV-401 = Ball valve, GV-501 = Gate valve
    "valve": re.compile(
        r"\b([XCHBG]V)-(\d{2,4}[A-Z]?)\b"
    ),

    # --- Instruments ---
    # FT-101 = Flow Transmitter, LT-201 = Level Transmitter
    # PT-301 = Pressure Transmitter, TT-401 = Temperature Transmitter
    # FI-101 = Flow Indicator, PI-201 = Pressure Indicator
    # FC-301 = Flow Controller, LC-401 = Level Controller
    # FA/LA/PA/TA = Alarms, FSL/FSH = Switches
    "instrument": re.compile(
        r"\b([FLPTAT][ITCASRE](?:[LH])?)-(\d{2,4}[A-Z]?)\b"
    ),

    # --- General catch-all for any tag-like pattern ---
    # Matches things like ABC-1234, which might be missed by specific patterns
    "general": re.compile(
        r"\b([A-Z]{1,4})-(\d{2,4}[A-Z]?)\b"
    ),
}

# Maps the first letter of an instrument tag to what it measures.
INSTRUMENT_VARIABLE_MAP: dict[str, str] = {
    "F": "flow",
    "L": "level",
    "P": "pressure",
    "T": "temperature",
    "A": "analysis",
}

# Maps the second letter of an instrument tag to its function.
INSTRUMENT_FUNCTION_MAP: dict[str, str] = {
    "I": "indicator",
    "T": "transmitter",
    "C": "controller",
    "A": "alarm",
    "S": "switch",
    "R": "recorder",
    "E": "element",
}

# Maps equipment prefix letter to equipment type.
EQUIPMENT_TYPE_MAP: dict[str, str] = {
    "P": "pump",
    "V": "vessel",
    "T": "tank/tower",
    "R": "reactor",
    "E": "heat exchanger",
    "C": "compressor",
    "D": "drum",
    "H": "heater",
}


# =============================================================================
# P&ID Analyzer Class
# =============================================================================

class PIDAnalyzer:
    """
    Multi-stage P&ID analysis pipeline.

    Combines OCR-based tag extraction with VLM-based visual understanding
    to produce a structured representation of a P&ID drawing.

    Usage:
        analyzer = PIDAnalyzer(ocr_engine, vision_model, image_preprocessor)
        result = analyzer.analyze("path/to/pid.png")
    """

    def __init__(self, ocr_engine, vision_model, image_preprocessor):
        """
        Args:
            ocr_engine: An OCREngine instance (from ocr.py).
            vision_model: A VisionModel instance (from vision.py).
            image_preprocessor: An ImagePreprocessor instance (from image_processor.py).
        """
        self.ocr = ocr_engine
        self.vlm = vision_model
        self.preprocessor = image_preprocessor

    def analyze(self, image_path: str | Path) -> PIDAnalysisResult:
        """
        Run the full P&ID analysis pipeline on an image.

        Steps:
            1. Preprocess the image for better OCR and VLM results
            2. Run OCR to extract all visible text
            3. Parse extracted text for equipment/instrument tags
            4. Run VLM for visual understanding
            5. Merge OCR and VLM results
            6. Assign confidence to each component
            7. Return structured PIDAnalysisResult

        Args:
            image_path: Path to the P&ID image file.

        Returns:
            PIDAnalysisResult with all detected components and uncertainties.
        """
        image_path = Path(image_path)
        source_name = image_path.name
        warnings: list[str] = []

        logger.info("Starting P&ID analysis: %s", source_name)

        # -----------------------------------------------------------------
        # Step 1: Preprocess the image
        # -----------------------------------------------------------------
        try:
            from PIL import Image
            pil_image = Image.open(image_path)
            enhanced = self.preprocessor.enhance_engineering_drawing(pil_image)
            logger.info("Image preprocessed for P&ID analysis")
        except Exception as exc:
            logger.error("Image preprocessing failed: %s", exc)
            return PIDAnalysisResult(
                success=False,
                source=source_name,
                error=ErrorDetail(
                    code=ErrorCode.IMAGE_CORRUPTED,
                    message=f"Failed to preprocess image: {exc}",
                ),
            )

        # -----------------------------------------------------------------
        # Step 2: OCR pass — extract all text from the drawing
        # -----------------------------------------------------------------
        ocr_text = ""
        ocr_tags_raw: list[str] = []
        ocr_boxes = None

        try:
            ocr_result = self.ocr.run_ocr_on_pil_image(enhanced)
            ocr_text = ocr_result.text
            ocr_boxes = getattr(ocr_result, "boxes", None)
            logger.info("OCR extracted %d words from P&ID", ocr_result.word_count)
        except Exception as exc:
            logger.warning("OCR pass failed, continuing with VLM only: %s", exc)
            warnings.append(f"OCR failed: {exc}")

        # -----------------------------------------------------------------
        # Step 3: Parse tags from OCR text
        # -----------------------------------------------------------------
        parsed_equipment: list[PIDEquipment] = []
        parsed_valves: list[PIDValve] = []
        parsed_instruments: list[PIDInstrument] = []

        if ocr_text:
            parsed_equipment, parsed_valves, parsed_instruments, ocr_tags_raw = (
                self._parse_tags_from_text(ocr_text, source_name, ocr_boxes)
            )
            logger.info(
                "Parsed tags: %d equipment, %d valves, %d instruments",
                len(parsed_equipment),
                len(parsed_valves),
                len(parsed_instruments),
            )

        # -----------------------------------------------------------------
        # Step 4: VLM analysis — visual understanding of components
        # -----------------------------------------------------------------
        vlm_data: Optional[dict] = None
        vlm_observations: list[Observation] = []
        vlm_uncertainties: list[str] = []

        try:
            if self.vlm.is_available():
                vlm_data = self.vlm.analyze_for_pid(image_path)
                logger.info("VLM P&ID analysis completed")
            else:
                warnings.append(
                    "VLM unavailable — analysis based on OCR tags only"
                )
                logger.warning("VLM unavailable for P&ID analysis")
        except Exception as exc:
            logger.warning("VLM analysis failed: %s", exc)
            warnings.append(f"VLM analysis failed: {exc}")

        # -----------------------------------------------------------------
        # Step 5: Merge OCR and VLM results
        # -----------------------------------------------------------------
        equipment, valves, instruments, pipes, connections, annotations = (
            self._merge_results(
                parsed_equipment,
                parsed_valves,
                parsed_instruments,
                vlm_data,
                source_name,
            )
        )

        # Extract observations and uncertainties from VLM data
        if vlm_data:
            vlm_observations = self._extract_observations(vlm_data)
            vlm_uncertainties = vlm_data.get("uncertainties", [])

        # -----------------------------------------------------------------
        # Step 6: Build final result
        # -----------------------------------------------------------------
        result = PIDAnalysisResult(
            success=True,
            source=source_name,
            equipment=equipment,
            valves=valves,
            instruments=instruments,
            pipes=pipes,
            connections=connections,
            annotations=annotations,
            observations=vlm_observations,
            uncertainties=vlm_uncertainties,
            ocr_tags=ocr_tags_raw,
            warnings=warnings,
        )

        logger.info(
            "P&ID analysis complete: %d equipment, %d valves, "
            "%d instruments, %d pipes, %d connections",
            len(equipment),
            len(valves),
            len(instruments),
            len(pipes),
            len(connections),
        )

        return result

    # =====================================================================
    # Tag Parsing
    # =====================================================================

    def _find_bbox_for_tag(self, tag: str, ocr_boxes: Optional[list]) -> tuple[Optional[list], Optional[list]]:
        if not ocr_boxes:
            return None, None
        for item in ocr_boxes:
            if isinstance(item, dict):
                text = item.get('text', '')
                if tag in text:
                    box = item.get('box') or item.get('bbox')
                    center = item.get('center')
                    if box and not center and len(box) == 4:
                        center = [
                            sum(p[0] for p in box) / 4,
                            sum(p[1] for p in box) / 4
                        ]
                    return box, center
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                # PaddleOCR format: [[p1, p2, p3, p4], (text, score)]
                box = item[0]
                text_info = item[1]
                if isinstance(text_info, (list, tuple)) and len(text_info) >= 1:
                    text = text_info[0]
                    if tag in text:
                        center = [
                            sum(p[0] for p in box) / 4,
                            sum(p[1] for p in box) / 4
                        ]
                        return box, center
        return None, None

    def _parse_tags_from_text(
        self, text: str, source_name: str, ocr_boxes: Optional[list] = None
    ) -> tuple[list[PIDEquipment], list[PIDValve], list[PIDInstrument], list[str]]:
        """
        Parse equipment, valve, and instrument tags from OCR text.

        Uses regex patterns to find ISA-standard tag formats like
        P-101, XV-201, FT-301, etc.

        Args:
            text: Raw OCR text from the P&ID.
            source_name: Name of the source file.
            ocr_boxes: Optional list of OCR bounding boxes.

        Returns:
            Tuple of (equipment_list, valve_list, instrument_list, raw_tags).
        """
        equipment: list[PIDEquipment] = []
        valves: list[PIDValve] = []
        instruments: list[PIDInstrument] = []
        all_tags: list[str] = []
        seen_tags: set[str] = set()  # Avoid duplicates

        # --- Equipment tags ---
        for match in TAG_PATTERNS["equipment"].finditer(text):
            tag = match.group(0)  # Full match, e.g., "P-101"
            prefix = match.group(1)  # Letter prefix, e.g., "P"

            if tag in seen_tags:
                continue
            seen_tags.add(tag)
            all_tags.append(tag)
            
            box, center = self._find_bbox_for_tag(tag, ocr_boxes)

            evidence = [Evidence(
                source=source_name,
                type="ocr",
                text=tag,
                originating_subsystem="paddleocr",
                direct_observation=True,
            )]

            equipment.append(PIDEquipment(
                tag=tag,
                type=EQUIPMENT_TYPE_MAP.get(prefix, "unknown"),
                confidence=ConfidenceInfo(available=False),
                uncertain=False,
                evidence=evidence,
                bbox=box,
                center=center,
            ))

        # --- Valve tags ---
        for match in TAG_PATTERNS["valve"].finditer(text):
            tag = match.group(0)
            prefix = match.group(1)  # e.g., "XV", "CV"

            if tag in seen_tags:
                continue
            seen_tags.add(tag)
            all_tags.append(tag)

            # Map prefix to valve type
            valve_type_map = {
                "XV": "on/off valve",
                "CV": "control valve",
                "HV": "hand valve",
                "BV": "ball valve",
                "GV": "gate valve",
            }

            box, center = self._find_bbox_for_tag(tag, ocr_boxes)

            evidence = [Evidence(
                source=source_name,
                type="ocr",
                text=tag,
                originating_subsystem="paddleocr",
                direct_observation=True,
            )]

            valves.append(PIDValve(
                tag=tag,
                type="valve",
                valve_type=valve_type_map.get(prefix, "unknown"),
                confidence=ConfidenceInfo(available=False),
                uncertain=False,
                evidence=evidence,
                bbox=box,
                center=center,
            ))

        # --- Instrument tags ---
        for match in TAG_PATTERNS["instrument"].finditer(text):
            tag = match.group(0)
            prefix = match.group(1)  # e.g., "FT", "LT"

            if tag in seen_tags:
                continue
            seen_tags.add(tag)
            all_tags.append(tag)

            # Decode the tag: first letter = measured variable, second = function
            measured = INSTRUMENT_VARIABLE_MAP.get(prefix[0], "")
            function = INSTRUMENT_FUNCTION_MAP.get(
                prefix[1] if len(prefix) > 1 else "", ""
            )

            box, center = self._find_bbox_for_tag(tag, ocr_boxes)

            evidence = [Evidence(
                source=source_name,
                type="ocr",
                text=tag,
                originating_subsystem="paddleocr",
                direct_observation=True,
            )]

            instruments.append(PIDInstrument(
                tag=tag,
                type="instrument",
                measured_variable=measured,
                function=function,
                confidence=ConfidenceInfo(available=False),
                uncertain=False,
                evidence=evidence,
                bbox=box,
                center=center,
            ))

        # --- Catch remaining tags that didn't match specific patterns ---
        for match in TAG_PATTERNS["general"].finditer(text):
            tag = match.group(0)
            if tag not in seen_tags:
                seen_tags.add(tag)
                all_tags.append(tag)
                
                box, center = self._find_bbox_for_tag(tag, ocr_boxes)
                
                evidence = [Evidence(
                    source=source_name,
                    type="ocr",
                    text=tag,
                    originating_subsystem="paddleocr",
                    direct_observation=True,
                )]
                
                # We don't know what these are — mark as uncertain equipment
                equipment.append(PIDEquipment(
                    tag=tag,
                    type="unknown",
                    confidence=ConfidenceInfo(available=False),
                    uncertain=True,
                    evidence=evidence,
                    bbox=box,
                    center=center,
                ))

        return equipment, valves, instruments, all_tags

    # =====================================================================
    # VLM Result Processing
    # =====================================================================

    def _extract_observations(self, vlm_data: dict) -> list[Observation]:
        """
        Convert VLM observations into structured Observation objects.

        The VLM is prompted to separate "observations" (directly visible)
        from "uncertainties" (inferred/uncertain).
        """
        observations: list[Observation] = []

        # Direct observations from VLM
        for obs_text in vlm_data.get("observations", []):
            if isinstance(obs_text, str) and obs_text.strip():
                observations.append(Observation(
                    type="observed",
                    content=obs_text.strip(),
                ))

        return observations

    def _merge_results(
        self,
        ocr_equipment: list[PIDEquipment],
        ocr_valves: list[PIDValve],
        ocr_instruments: list[PIDInstrument],
        vlm_data: Optional[dict],
        source_name: str,
    ) -> tuple[
        list[PIDEquipment],
        list[PIDValve],
        list[PIDInstrument],
        list[PIDPipe],
        list[PIDConnection],
        list[str],
    ]:
        """
        Merge OCR-extracted tags with VLM-detected components.

        Strategy:
          - OCR tags are the ground truth for tag NAMES (OCR reads text well).
          - VLM provides component TYPES and DESCRIPTIONS (VLM understands visuals).
          - When both identify the same tag, merge their information.
          - VLM-only detections are added with lower confidence.
          - OCR-only tags keep their regex-derived types.

        Args:
            ocr_equipment: Equipment found by OCR tag parsing.
            ocr_valves: Valves found by OCR tag parsing.
            ocr_instruments: Instruments found by OCR tag parsing.
            vlm_data: Raw dict from VLM P&ID analysis (may be None).
            source_name: Name of the source file.

        Returns:
            Merged (equipment, valves, instruments, pipes, connections, annotations).
        """
        # Start with OCR results as the base
        equipment = list(ocr_equipment)
        valves = list(ocr_valves)
        instruments = list(ocr_instruments)
        pipes: list[PIDPipe] = []
        connections: list[PIDConnection] = []
        annotations: list[str] = []

        if not vlm_data:
            return equipment, valves, instruments, pipes, connections, annotations

        # Collect existing OCR tags for dedup
        existing_tags = {
            comp.tag
            for comp in equipment + valves + instruments  # type: ignore
            if comp.tag
        }

        # Helper to create VLM evidence
        def _create_vlm_evidence(desc: str) -> list[Evidence]:
            return [Evidence(
                source=source_name,
                type="vlm",
                visual_description=desc,
                originating_subsystem="ollama_vlm",
                direct_observation=False,
            )]

        # --- Merge VLM equipment ---
        for vlm_equip in vlm_data.get("equipment", []):
            if not isinstance(vlm_equip, dict):
                continue
            tag = vlm_equip.get("tag", "")
            desc = vlm_equip.get("description", "")
            if tag and tag in existing_tags:
                # Update existing entry's description from VLM
                for eq in equipment:
                    if eq.tag == tag:
                        eq.description = desc
                        if vlm_equip.get("type"):
                            eq.type = vlm_equip["type"]
                        # Add VLM evidence to existing equipment
                        if not hasattr(eq, "evidence") or eq.evidence is None:
                            eq.evidence = []
                        eq.evidence.extend(_create_vlm_evidence(f"VLM detected equipment {tag}: {desc}"))
                        break
            elif tag:
                # New from VLM — add with lower confidence
                equipment.append(PIDEquipment(
                    tag=tag,
                    type=vlm_equip.get("type", "unknown"),
                    description=desc,
                    confidence=ConfidenceInfo(available=False),
                    uncertain=True,
                    evidence=_create_vlm_evidence(f"VLM detected equipment {tag}: {desc}"),
                ))

        # --- Merge VLM valves ---
        for vlm_valve in vlm_data.get("valves", []):
            if not isinstance(vlm_valve, dict):
                continue
            tag = vlm_valve.get("tag", "")
            desc = vlm_valve.get("description", "")
            if tag and tag not in existing_tags:
                valves.append(PIDValve(
                    tag=tag,
                    type="valve",
                    valve_type=vlm_valve.get("type", "unknown"),
                    description=desc,
                    confidence=ConfidenceInfo(available=False),
                    uncertain=True,
                    evidence=_create_vlm_evidence(f"VLM detected valve {tag}: {desc}"),
                ))
            elif tag and tag in existing_tags:
                for v in valves:
                    if v.tag == tag:
                        v.description = desc
                        if vlm_valve.get("type"):
                            v.valve_type = vlm_valve["type"]
                        if not hasattr(v, "evidence") or v.evidence is None:
                            v.evidence = []
                        v.evidence.extend(_create_vlm_evidence(f"VLM detected valve {tag}: {desc}"))
                        break

        # --- Merge VLM instruments ---
        for vlm_inst in vlm_data.get("instruments", []):
            if not isinstance(vlm_inst, dict):
                continue
            tag = vlm_inst.get("tag", "")
            desc = vlm_inst.get("description", "")
            if tag and tag not in existing_tags:
                instruments.append(PIDInstrument(
                    tag=tag,
                    type="instrument",
                    measured_variable=vlm_inst.get("measured_variable", ""),
                    function=vlm_inst.get("function", ""),
                    description=desc,
                    confidence=ConfidenceInfo(available=False),
                    uncertain=True,
                    evidence=_create_vlm_evidence(f"VLM detected instrument {tag}: {desc}"),
                ))
            elif tag and tag in existing_tags:
                for i in instruments:
                    if i.tag == tag:
                        i.description = desc
                        if not hasattr(i, "evidence") or i.evidence is None:
                            i.evidence = []
                        i.evidence.extend(_create_vlm_evidence(f"VLM detected instrument {tag}: {desc}"))
                        break

        # --- Pipes from VLM ---
        for vlm_pipe in vlm_data.get("pipes", []):
            if not isinstance(vlm_pipe, dict):
                continue
            pipes.append(PIDPipe(
                label=vlm_pipe.get("label"),
                from_component=vlm_pipe.get("from", ""),
                to_component=vlm_pipe.get("to", ""),
                confidence=ConfidenceInfo(available=False),
                uncertain=True,
                evidence=_create_vlm_evidence(f"Pipe from {vlm_pipe.get('from', '')} to {vlm_pipe.get('to', '')}"),
            ))

        # --- Connections from VLM ---
        for vlm_conn in vlm_data.get("connections", []):
            if not isinstance(vlm_conn, dict):
                continue
            connections.append(PIDConnection(
                from_tag=vlm_conn.get("from", ""),
                to_tag=vlm_conn.get("to", ""),
                connection_type=vlm_conn.get("type", "pipe"),
                confidence=ConfidenceInfo(available=False),
                uncertain=True,
                evidence=_create_vlm_evidence(f"{vlm_conn.get('from', '')} -> {vlm_conn.get('to', '')}"),
            ))

        # --- Annotations from VLM ---
        annotations = [
            a for a in vlm_data.get("annotations", [])
            if isinstance(a, str) and a.strip()
        ]

        return equipment, valves, instruments, pipes, connections, annotations
