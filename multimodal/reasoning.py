"""
SOVARA Multimodal Intelligence — Reasoning Engine

Local LLM-powered reasoning for semantic analysis, entity extraction,
relationship analysis, and evidence-grounded analytical reasoning.

Uses Ollama's REST API to communicate with a local reasoning model
(qwen3:4b by default). All calls go to localhost only.

Key principles:
  - The reasoning model receives pre-extracted evidence (from OCR, VLM)
    and performs higher-order analysis on it.
  - All outputs distinguish OBSERVATION, INFERENCE, and HYPOTHESIS.
  - The reasoning model is treated as untrusted — its outputs are parsed,
    validated, and normalized before being returned.
  - Confidence is NEVER fabricated. Reasoning outputs always have
    confidence marked as unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import requests

from multimodal.config import (
    OLLAMA_BASE_URL,
    REASONING_MODEL,
    REASONING_MAX_TOKENS,
    REASONING_NUM_CTX,
    REASONING_TIMEOUT,
    ErrorCode,
)
from multimodal.schemas import (
    ConfidenceInfo,
    Contradiction,
    ErrorDetail,
    Evidence,
    Finding,
    Hypothesis,
    Inference,
    ReasoningResult,
)
from multimodal.security import validate_url
from multimodal.utils import safe_json_parse

logger = logging.getLogger("sovara.multimodal.reasoning")


# =============================================================================
# Prompts
# =============================================================================

ENTITY_EXTRACTION_PROMPT = """\
Analyze the following text extracted from a document. Extract all named entities.

TEXT:
{text}

Respond ONLY with a JSON object (no other text):
{{
    "entities": ["list of entities found"],
    "relationships": ["entity_a is connected to entity_b"],
    "observations": ["things directly stated in the text"],
    "inferences": ["things you interpret from the text"],
    "uncertainties": ["things that are unclear"]
}}"""

SEMANTIC_ANALYSIS_PROMPT = """\
You are analyzing evidence from industrial documents and images. \
Your task is to perform semantic analysis of the following evidence.

TASK: {task}

EVIDENCE:
{evidence_text}

CRITICAL RULES:
- Separate what the evidence DIRECTLY STATES (observations) from what you INTERPRET (inferences).
- Generate hypotheses only when evidence supports them. Never fabricate evidence.
- Use cautious language: "may indicate", "appears consistent with", "possible explanation".
- If evidence is insufficient, say so explicitly.

Respond ONLY with a JSON object:
{{
    "observations": ["things the evidence directly states or shows"],
    "inferences": ["your interpretations of what the evidence means"],
    "hypotheses": [
        {{
            "statement": "a possible explanation",
            "supporting_points": ["evidence that supports this"],
            "uncertainties": ["what remains unclear"]
        }}
    ],
    "findings": [
        {{
            "statement": "an evidence-grounded finding",
            "evidence_refs": ["which evidence supports this"]
        }}
    ],
    "contradictions": [
        {{
            "topic": "what they disagree about",
            "side_a": "what one source says",
            "side_b": "what another says"
        }}
    ],
    "unresolved_questions": ["questions that cannot be answered from available evidence"]
}}"""

VQA_REASONING_PROMPT = """\
You are answering a question about an image or document based on available evidence.

QUESTION: {question}

AVAILABLE EVIDENCE:
{evidence_text}

CRITICAL RULES:
- Answer ONLY using the available evidence. Do not fabricate information.
- If the evidence is insufficient to answer, say so.
- Separate observations from inferences.

Respond ONLY with a JSON object:
{{
    "answer": "your answer based on the evidence",
    "observations": ["things directly visible or stated"],
    "inferences": ["your interpretations"],
    "uncertainties": ["things you cannot determine"]
}}"""

MULTI_DOC_REASONING_PROMPT = """\
You are analyzing evidence gathered from multiple documents and images \
for an industrial analysis task.

TASK: {task}

SOURCES AND EVIDENCE:
{evidence_text}

CRITICAL RULES:
- Cross-reference information across sources.
- Identify recurring patterns, themes, and observations.
- Flag contradictions between sources explicitly.
- Generate findings only when supported by evidence from the sources.
- Generate hypotheses cautiously, with explicit uncertainty.
- Never present correlation as causation.
- Use language such as "may indicate", "appears consistent with", \
"evidence suggests".

Respond ONLY with a JSON object:
{{
    "findings": [
        {{
            "statement": "an evidence-grounded finding",
            "source_refs": ["which sources support this"]
        }}
    ],
    "hypotheses": [
        {{
            "statement": "a possible explanation",
            "supporting_points": ["evidence that supports this"],
            "contradicting_points": [],
            "uncertainties": ["what remains unclear"]
        }}
    ],
    "contradictions": [
        {{
            "topic": "what they disagree about",
            "source_a": "source and what it says",
            "source_b": "source and what it says"
        }}
    ],
    "unresolved_questions": ["questions that cannot be answered"],
    "observations": ["cross-source observations"],
    "inferences": ["cross-source interpretations"]
}}"""


class ReasoningEngine:
    """
    Local LLM reasoning engine using Ollama.

    Performs text-based analytical reasoning on pre-extracted evidence.
    This is NOT the VLM — it's a separate text model for higher-order
    analysis.

    Usage:
        engine = ReasoningEngine()
        if engine.is_available():
            result = engine.analyze_evidence(evidence_list, "Find issues with P-101")
    """

    def __init__(self) -> None:
        """Initialize with settings from config."""
        self.base_url = OLLAMA_BASE_URL
        self.model = REASONING_MODEL
        self.timeout = REASONING_TIMEOUT

        # Validate the URL at initialization
        try:
            validate_url(self.base_url)
        except ValueError as exc:
            logger.error("Reasoning engine URL validation failed: %s", exc)
            raise

    # =================================================================
    # Availability Check
    # =================================================================

    def is_available(self) -> bool:
        """
        Check if Ollama is running and the reasoning model is available.

        Returns:
            True if the reasoning model is ready for inference.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            available = any(self.model in name for name in model_names)
            if not available:
                logger.warning(
                    "Reasoning model '%s' not found in Ollama. Available: %s",
                    self.model,
                    model_names,
                )
            return available

        except requests.ConnectionError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            return False
        except requests.RequestException as exc:
            logger.error("Reasoning availability check failed: %s", exc)
            return False

    # =================================================================
    # Core Ollama Communication
    # =================================================================

    def _call_ollama(self, prompt: str) -> tuple[str, Optional[ErrorDetail]]:
        """
        Call Ollama's /api/generate endpoint with a text prompt.

        Args:
            prompt: The text prompt.

        Returns:
            Tuple of (response_text, error).
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": REASONING_NUM_CTX,
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", ""), None

        except requests.Timeout:
            logger.error("Reasoning request timed out after %ds", self.timeout)
            return "", ErrorDetail(
                code=ErrorCode.VLM_TIMEOUT,
                message=f"Reasoning request timed out after {self.timeout}s",
            )
        except requests.ConnectionError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            return "", ErrorDetail(
                code=ErrorCode.VLM_UNAVAILABLE,
                message=f"Cannot connect to Ollama at {self.base_url}",
            )
        except requests.RequestException as exc:
            logger.error("Reasoning request failed: %s", exc)
            return "", ErrorDetail(
                code=ErrorCode.VLM_UNAVAILABLE,
                message=f"Reasoning request failed: {exc}",
            )

    # =================================================================
    # Evidence Formatting
    # =================================================================

    @staticmethod
    def _format_evidence(evidence_list: list[Evidence]) -> str:
        """Format evidence items into readable text for the reasoning model."""
        parts = []
        for i, ev in enumerate(evidence_list, 1):
            lines = [f"[Evidence {i}]"]
            lines.append(f"  Source: {ev.source}")
            if ev.page is not None:
                lines.append(f"  Page: {ev.page}")
            lines.append(f"  Type: {ev.type}")
            if ev.text:
                lines.append(f"  Text: {ev.text}")
            if ev.visual_description:
                lines.append(f"  Visual: {ev.visual_description}")
            lines.append(
                f"  Direct observation: {ev.direct_observation}"
            )
            parts.append("\n".join(lines))
        return "\n\n".join(parts) if parts else "(no evidence provided)"

    @staticmethod
    def _format_source_evidence(
        source_evidence: dict[str, list[Evidence]],
    ) -> str:
        """Format evidence grouped by source for multi-document analysis."""
        parts = []
        for source, evidence_list in source_evidence.items():
            parts.append(f"=== Source: {source} ===")
            for ev in evidence_list:
                if ev.text:
                    parts.append(f"  [{ev.type}] {ev.text}")
                if ev.visual_description:
                    parts.append(f"  [visual] {ev.visual_description}")
            parts.append("")
        return "\n".join(parts) if parts else "(no evidence provided)"

    # =================================================================
    # Semantic Analysis
    # =================================================================

    def analyze_evidence(
        self,
        evidence: list[Evidence],
        task: str,
    ) -> ReasoningResult:
        """
        Perform semantic analysis on provided evidence for a given task.

        Args:
            evidence: List of Evidence objects to analyze.
            task: The analytical task/question.

        Returns:
            ReasoningResult with observations, inferences, hypotheses,
            findings, and contradictions.
        """
        if not self.is_available():
            return ReasoningResult(
                success=False,
                task=task,
                error=ErrorDetail(
                    code=ErrorCode.VLM_UNAVAILABLE,
                    message="Reasoning model is not available",
                ),
            )

        evidence_text = self._format_evidence(evidence)
        prompt = SEMANTIC_ANALYSIS_PROMPT.format(
            task=task,
            evidence_text=evidence_text,
        )

        response_text, error = self._call_ollama(prompt)
        if error:
            return ReasoningResult(
                success=False,
                task=task,
                error=error,
            )

        parsed = safe_json_parse(response_text)
        if not parsed:
            logger.warning(
                "Reasoning response was not valid JSON, returning raw"
            )
            return ReasoningResult(
                success=True,
                task=task,
                observations=[response_text.strip()] if response_text.strip() else [],
                warnings=["Reasoning response was not structured JSON"],
            )

        return self._build_reasoning_result(parsed, task, evidence)

    # =================================================================
    # Visual Question Answering Support
    # =================================================================

    def answer_question_with_evidence(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> dict[str, Any]:
        """
        Answer a question using provided evidence.

        Used by the VQA pipeline after OCR and VLM have extracted
        evidence from the image.

        Args:
            question: The question to answer.
            evidence: Available evidence.

        Returns:
            Dict with answer, observations, inferences, uncertainties.
        """
        evidence_text = self._format_evidence(evidence)
        prompt = VQA_REASONING_PROMPT.format(
            question=question,
            evidence_text=evidence_text,
        )

        response_text, error = self._call_ollama(prompt)
        if error:
            return {
                "answer": "",
                "observations": [],
                "inferences": [],
                "uncertainties": ["Reasoning model was unavailable"],
                "error": error,
            }

        parsed = safe_json_parse(response_text)
        if not parsed:
            return {
                "answer": response_text.strip() if response_text else "",
                "observations": [],
                "inferences": [],
                "uncertainties": [],
            }

        return {
            "answer": parsed.get("answer", ""),
            "observations": _safe_str_list(parsed.get("observations", [])),
            "inferences": _safe_str_list(parsed.get("inferences", [])),
            "uncertainties": _safe_str_list(parsed.get("uncertainties", [])),
        }

    # =================================================================
    # Multi-Document Reasoning
    # =================================================================

    def reason_across_documents(
        self,
        source_evidence: dict[str, list[Evidence]],
        task: str,
    ) -> ReasoningResult:
        """
        Perform cross-document reasoning.

        Args:
            source_evidence: Mapping of source filename → evidence list.
            task: The analytical task.

        Returns:
            ReasoningResult with cross-document findings, hypotheses,
            and contradictions.
        """
        if not self.is_available():
            return ReasoningResult(
                success=False,
                task=task,
                error=ErrorDetail(
                    code=ErrorCode.VLM_UNAVAILABLE,
                    message="Reasoning model is not available",
                ),
            )

        evidence_text = self._format_source_evidence(source_evidence)
        prompt = MULTI_DOC_REASONING_PROMPT.format(
            task=task,
            evidence_text=evidence_text,
        )

        response_text, error = self._call_ollama(prompt)
        if error:
            return ReasoningResult(
                success=False,
                task=task,
                error=error,
            )

        # Flatten all evidence for provenance
        all_evidence = []
        for ev_list in source_evidence.values():
            all_evidence.extend(ev_list)

        parsed = safe_json_parse(response_text)
        if not parsed:
            return ReasoningResult(
                success=True,
                task=task,
                observations=[response_text.strip()] if response_text.strip() else [],
                warnings=["Reasoning response was not structured JSON"],
            )

        return self._build_reasoning_result(parsed, task, all_evidence)

    # =================================================================
    # Entity Extraction via LLM
    # =================================================================

    def extract_entities(self, text: str) -> dict[str, Any]:
        """
        Extract entities and relationships from text using the reasoning model.

        Falls back to empty results if the model is unavailable.

        Args:
            text: Input text to analyze.

        Returns:
            Dict with entities, relationships, observations, inferences.
        """
        if not self.is_available():
            return {"entities": [], "relationships": [], "observations": [], "inferences": []}

        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text[:4000])
        response_text, error = self._call_ollama(prompt)

        if error:
            return {"entities": [], "relationships": [], "observations": [], "inferences": []}

        parsed = safe_json_parse(response_text)
        if not parsed:
            return {"entities": [], "relationships": [], "observations": [], "inferences": []}

        return {
            "entities": _safe_str_list(parsed.get("entities", [])),
            "relationships": _safe_str_list(parsed.get("relationships", [])),
            "observations": _safe_str_list(parsed.get("observations", [])),
            "inferences": _safe_str_list(parsed.get("inferences", [])),
        }

    # =================================================================
    # Result Building
    # =================================================================

    def _build_reasoning_result(
        self,
        parsed: dict[str, Any],
        task: str,
        source_evidence: list[Evidence],
    ) -> ReasoningResult:
        """
        Build a ReasoningResult from parsed LLM output.

        Treats LLM output as untrusted — validates types and normalizes.
        """
        # Build inferences
        inferences = []
        for inf_text in _safe_str_list(parsed.get("inferences", [])):
            inferences.append(Inference(
                content=inf_text,
                confidence=ConfidenceInfo(available=False),
                supporting_evidence=[],
            ))

        # Build hypotheses
        hypotheses = []
        for hyp in parsed.get("hypotheses", []):
            if isinstance(hyp, dict):
                hypotheses.append(Hypothesis(
                    statement=str(hyp.get("statement", "")),
                    supporting_evidence=[],
                    contradicting_evidence=[],
                    uncertainties=_safe_str_list(
                        hyp.get("uncertainties", [])
                    ),
                ))
            elif isinstance(hyp, str):
                hypotheses.append(Hypothesis(
                    statement=hyp,
                ))

        # Build findings
        findings = []
        for f in parsed.get("findings", []):
            if isinstance(f, dict):
                findings.append(Finding(
                    statement=str(f.get("statement", "")),
                    evidence=[],
                    confidence=ConfidenceInfo(available=False),
                ))
            elif isinstance(f, str):
                findings.append(Finding(
                    statement=f,
                    evidence=[],
                    confidence=ConfidenceInfo(available=False),
                ))

        # Build contradictions
        contradictions = []
        for c in parsed.get("contradictions", []):
            if isinstance(c, dict):
                contradictions.append(Contradiction(
                    topic=str(c.get("topic", "")),
                    evidence_a=[],
                    evidence_b=[],
                    resolution=None,
                ))

        return ReasoningResult(
            success=True,
            task=task,
            observations=_safe_str_list(parsed.get("observations", [])),
            inferences=inferences,
            hypotheses=hypotheses,
            findings=findings,
            contradictions=contradictions,
            uncertainties=_safe_str_list(
                parsed.get("unresolved_questions", [])
            ),
        )


# =============================================================================
# Helpers
# =============================================================================

def _safe_str_list(items: Any) -> list[str]:
    """
    Safely convert a potentially malformed list to a list of strings.

    VLM/LLM outputs can contain non-string items or not be a list at all.
    """
    if not isinstance(items, list):
        if isinstance(items, str) and items.strip():
            return [items]
        return []
    return [str(item).strip() for item in items if item and str(item).strip()]
