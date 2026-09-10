"""
SOVARA Multimodal Intelligence — Evidence Engine

Manages evidence provenance, normalization, and cross-document analysis.

This module:
  - Converts OCR results, VLM observations, and text extractions into
    standardized Evidence objects with full provenance.
  - Performs cross-document entity resolution (name matching).
  - Detects contradictions between evidence items.
  - Deduplicates evidence while preserving all sources.
  - Builds findings and hypotheses from aggregated evidence.

The Evidence model is the universal provenance token throughout the
system. Every claim can be traced back to its source via Evidence.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from multimodal.schemas import (
    Contradiction,
    Evidence,
    Finding,
    Hypothesis,
    Observation,
    ConfidenceInfo,
)

logger = logging.getLogger("sovara.multimodal.evidence")


# =============================================================================
# Evidence Construction Helpers
# =============================================================================

def evidence_from_ocr(
    source: str,
    text: str,
    page: Optional[int] = None,
    bbox: Optional[list[float]] = None,
    confidence: Optional[float] = None,
) -> Evidence:
    """
    Create an Evidence object from OCR extraction.

    Args:
        source: Source file name.
        text: Extracted text.
        page: Page number (1-indexed).
        bbox: Bounding box [x1, y1, x2, y2] if available.
        confidence: OCR confidence score if available.

    Returns:
        Evidence with type='ocr' and direct_observation=True.
    """
    return Evidence(
        source=source,
        page=page,
        type="ocr",
        text=text,
        bbox=bbox,
        originating_subsystem="paddleocr",
        direct_observation=True,
    )


def evidence_from_vlm(
    source: str,
    visual_description: str,
    page: Optional[int] = None,
    image_id: Optional[str] = None,
    direct: bool = True,
) -> Evidence:
    """
    Create an Evidence object from VLM analysis.

    Args:
        source: Source file name.
        visual_description: VLM's description.
        page: Page number if from a document.
        image_id: Identifier for the image.
        direct: Whether this is a direct observation (True) or inference (False).

    Returns:
        Evidence with type='vlm'.
    """
    return Evidence(
        source=source,
        page=page,
        image_id=image_id,
        type="vlm",
        visual_description=visual_description,
        originating_subsystem="ollama_vlm",
        direct_observation=direct,
    )


def evidence_from_text_extraction(
    source: str,
    text: str,
    page: Optional[int] = None,
) -> Evidence:
    """
    Create an Evidence object from selectable PDF text extraction.

    This is deterministic extraction — no model involved.

    Args:
        source: Source file name.
        text: Extracted text.
        page: Page number.

    Returns:
        Evidence with type='text_extraction' and direct_observation=True.
    """
    return Evidence(
        source=source,
        page=page,
        type="text_extraction",
        text=text,
        originating_subsystem="pymupdf",
        direct_observation=True,
    )


def evidence_from_reasoning(
    source: str,
    text: str,
    page: Optional[int] = None,
) -> Evidence:
    """
    Create an Evidence object from reasoning model output.

    Reasoning outputs are NEVER direct observations.

    Args:
        source: Source file name.
        text: Reasoning output text.
        page: Page number if applicable.

    Returns:
        Evidence with type='reasoning' and direct_observation=False.
    """
    return Evidence(
        source=source,
        page=page,
        type="reasoning",
        text=text,
        originating_subsystem="ollama_reasoning",
        direct_observation=False,
    )


# =============================================================================
# Entity Extraction (Simple)
# =============================================================================

# Common industrial entity patterns
ENTITY_PATTERNS = {
    "equipment_tag": re.compile(r"\b([PVTRECDH])-(\d{2,4}[A-Z]?)\b"),
    "valve_tag": re.compile(r"\b([XCHBG]V)-(\d{2,4}[A-Z]?)\b"),
    "instrument_tag": re.compile(r"\b([FLPTAT][ITCASRE](?:[LH])?)-(\d{2,4}[A-Z]?)\b"),
}


def extract_entities_from_text(text: str) -> list[str]:
    """
    Extract named entities (equipment tags, valve tags, instrument tags)
    from text using regex patterns.

    This is a lightweight extraction — the reasoning model does deeper
    entity extraction. This function catches the obvious ISA-standard tags.

    Args:
        text: Input text.

    Returns:
        List of unique entity strings found.
    """
    entities: set[str] = set()
    for pattern in ENTITY_PATTERNS.values():
        for match in pattern.finditer(text):
            entities.add(match.group(0))
    return sorted(entities)


# =============================================================================
# Cross-Document Entity Resolution
# =============================================================================

def find_shared_entities(
    source_entities: dict[str, list[str]],
) -> dict[str, list[str]]:
    """
    Find entities that appear across multiple sources.

    Args:
        source_entities: Mapping of source filename → list of entities.

    Returns:
        Mapping of entity → list of sources where it appears.
        Only entities appearing in 2+ sources are included.
    """
    entity_sources: dict[str, list[str]] = {}

    for source, entities in source_entities.items():
        for entity in entities:
            normalized = entity.upper().strip()
            if normalized not in entity_sources:
                entity_sources[normalized] = []
            if source not in entity_sources[normalized]:
                entity_sources[normalized].append(source)

    # Only keep entities appearing in multiple sources
    return {
        entity: sources
        for entity, sources in entity_sources.items()
        if len(sources) > 1
    }


# =============================================================================
# Evidence Deduplication
# =============================================================================

def deduplicate_evidence(evidence_list: list[Evidence]) -> list[Evidence]:
    """
    Remove duplicate evidence items while preserving order and all sources.

    Two evidence items are considered duplicates if they have the same
    source, page, type, and text content.

    Args:
        evidence_list: List of Evidence objects.

    Returns:
        Deduplicated list.
    """
    seen: set[tuple] = set()
    result: list[Evidence] = []

    for ev in evidence_list:
        key = (
            ev.source,
            ev.page,
            ev.type,
            (ev.text or "").strip().lower(),
            (ev.visual_description or "").strip().lower(),
        )
        if key not in seen:
            seen.add(key)
            result.append(ev)

    return result


# =============================================================================
# Contradiction Detection
# =============================================================================

def detect_contradictions(
    evidence_groups: dict[str, list[Evidence]],
) -> list[Contradiction]:
    """
    Detect potential contradictions in evidence grouped by topic/entity.

    Simple heuristic: if two evidence items about the same entity contain
    opposing sentiment keywords (e.g., "operational" vs "failed",
    "normal" vs "abnormal"), flag as a potential contradiction.

    Args:
        evidence_groups: Mapping of topic/entity → list of evidence items.

    Returns:
        List of Contradiction objects.
    """
    contradictions: list[Contradiction] = []

    # Opposing term pairs commonly found in industrial contexts
    opposing_pairs = [
        ({"operational", "operating", "normal", "good", "passed", "satisfactory"},
         {"failed", "failure", "abnormal", "defective", "rejected", "unsatisfactory"}),
        ({"intact", "undamaged", "no damage"},
         {"damaged", "corroded", "corrosion", "cracked", "worn", "degraded"}),
        ({"open"},
         {"closed"}),
        ({"increasing", "rising"},
         {"decreasing", "falling", "declining"}),
    ]

    for topic, evidence_list in evidence_groups.items():
        if len(evidence_list) < 2:
            continue

        for i, ev_a in enumerate(evidence_list):
            text_a = _evidence_text(ev_a).lower()
            for ev_b in evidence_list[i + 1:]:
                text_b = _evidence_text(ev_b).lower()

                # Check if they come from different sources
                if ev_a.source == ev_b.source and ev_a.page == ev_b.page:
                    continue

                for pos_terms, neg_terms in opposing_pairs:
                    a_has_pos = any(t in text_a for t in pos_terms)
                    a_has_neg = any(t in text_a for t in neg_terms)
                    b_has_pos = any(t in text_b for t in pos_terms)
                    b_has_neg = any(t in text_b for t in neg_terms)

                    if (a_has_pos and b_has_neg) or (a_has_neg and b_has_pos):
                        contradictions.append(Contradiction(
                            topic=topic,
                            evidence_a=[ev_a],
                            evidence_b=[ev_b],
                            resolution=None,
                        ))
                        break  # One contradiction per pair is enough

    return contradictions


def _evidence_text(ev: Evidence) -> str:
    """Extract displayable text from an evidence item."""
    parts = []
    if ev.text:
        parts.append(ev.text)
    if ev.visual_description:
        parts.append(ev.visual_description)
    return " ".join(parts)


# =============================================================================
# Evidence Aggregation
# =============================================================================

def group_evidence_by_entity(
    evidence_list: list[Evidence],
) -> dict[str, list[Evidence]]:
    """
    Group evidence items by the entities they mention.

    Args:
        evidence_list: Flat list of evidence.

    Returns:
        Mapping of entity → list of evidence mentioning that entity.
    """
    groups: dict[str, list[Evidence]] = {}

    for ev in evidence_list:
        text = _evidence_text(ev)
        entities = extract_entities_from_text(text)

        if not entities:
            # If no structured entities found, group by source
            key = f"source:{ev.source}"
            if key not in groups:
                groups[key] = []
            groups[key].append(ev)
        else:
            for entity in entities:
                if entity not in groups:
                    groups[entity] = []
                groups[entity].append(ev)

    return groups


def build_finding(
    statement: str,
    evidence: list[Evidence],
) -> Finding:
    """
    Build a Finding with evidence and honest confidence.

    Confidence is always marked unavailable because findings are
    synthesized from multiple sources — there is no single calibrated
    score that applies.

    Args:
        statement: The finding statement.
        evidence: Supporting evidence list.

    Returns:
        Finding with unavailable confidence.
    """
    return Finding(
        statement=statement,
        evidence=evidence,
        confidence=ConfidenceInfo(available=False),
    )


def build_hypothesis(
    statement: str,
    supporting: list[Evidence],
    contradicting: Optional[list[Evidence]] = None,
    uncertainties: Optional[list[str]] = None,
) -> Hypothesis:
    """
    Build a Hypothesis with supporting/contradicting evidence.

    Args:
        statement: The hypothesis statement.
        supporting: Supporting evidence.
        contradicting: Contradicting evidence (if any).
        uncertainties: List of uncertainty descriptions.

    Returns:
        Hypothesis object.
    """
    return Hypothesis(
        statement=statement,
        supporting_evidence=supporting,
        contradicting_evidence=contradicting or [],
        uncertainties=uncertainties or [],
    )
