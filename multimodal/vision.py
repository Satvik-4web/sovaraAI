"""
SOVARA Multimodal Intelligence — Vision Model

Communicates with Ollama's REST API at localhost to run the
Qwen2.5-VL-3B vision-language model for image analysis.

Key design decisions:
  - Uses Ollama's /api/generate endpoint (not /api/chat) for simplicity.
  - Sends images as base64-encoded strings in the request body.
  - Structured prompting instructs the model to return JSON with
    OBSERVED vs INFERRED separation.
  - VLM confidence is ALWAYS marked as unavailable because VLMs don't
    provide calibrated confidence scores. We're honest about this.
  - All communication is localhost only — no external network calls.

The ``requests`` library is used ONLY for http://localhost:11434.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional, Union

import requests

from multimodal.config import (
    OLLAMA_BASE_URL,
    VLM_MODEL,
    VLM_NUM_CTX,
    VLM_TIMEOUT,
    ErrorCode,
)
from multimodal.schemas import (
    ConfidenceInfo,
    ErrorDetail,
    ImageAnalysisResult,
    Observation,
)
from multimodal.security import validate_url
from multimodal.utils import encode_image_base64, safe_json_parse

logger = logging.getLogger("sovara.multimodal.vision")


# =========================================================================
# Prompts
# =========================================================================
# These prompts instruct the VLM to return structured JSON and to
# separate direct observations from inferences.

IMAGE_ANALYSIS_PROMPT = """\
Analyze this image carefully. Respond ONLY with a JSON object (no other text).

Separate what you can DIRECTLY SEE from what you INFER or INTERPRET.

Return this exact JSON structure:
{
    "description": "overall description of the image",
    "objects": ["list of objects visible"],
    "observed": ["things you can directly see - be factual"],
    "inferred": ["interpretations, implications, or conclusions you draw"],
    "text_content": ["any text visible in the image"],
    "uncertainties": ["things you are not sure about"]
}"""

PID_ANALYSIS_PROMPT = """\
This is a Piping and Instrumentation Diagram (P&ID) or engineering drawing. \
Analyze it carefully.

Respond ONLY with a JSON object. Identify:
- Equipment (pumps, vessels, tanks, reactors, heat exchangers)
- Valves (gate, globe, ball, check, control valves)
- Instruments (flow, level, pressure, temperature indicators/transmitters/controllers)
- Pipes and connections
- Flow direction
- Any text labels or annotations

For each component, provide its tag if visible. \
If you are uncertain about any identification, say so.

Return this JSON structure:
{
    "equipment": [{"tag": "P-101", "type": "pump", "description": "..."}],
    "valves": [{"tag": "XV-201", "type": "gate valve", "description": "..."}],
    "instruments": [{"tag": "FT-301", "type": "flow transmitter", \
"measured_variable": "flow", "function": "transmitter"}],
    "pipes": [{"label": "...", "from": "...", "to": "..."}],
    "connections": [{"from": "...", "to": "...", "type": "pipe"}],
    "annotations": ["visible text annotations"],
    "observations": ["what you directly observe"],
    "uncertainties": ["what you're uncertain about"]
}"""

FIGURE_DESCRIPTION_PROMPT = (
    "Describe this figure briefly and factually. "
    "Focus on what is directly visible. Respond with plain text only."
)

VQA_PROMPT = """\
Answer the following question about this image. \
Base your answer ONLY on what is visible in the image.

QUESTION: {question}

Respond ONLY with a JSON object:
{{
    "answer": "your answer based on what you can see",
    "observations": ["things you can directly see that are relevant"],
    "inferences": ["interpretations you draw from what you see"],
    "uncertainties": ["things you cannot determine from this image"]
}}"""

DEEP_ANALYSIS_PROMPT = """\
Perform a thorough analysis of this image. Respond ONLY with a JSON object.

Identify:
- Entities (objects, equipment, people, text)
- Attributes (colors, sizes, conditions, states)
- Relationships between entities
- Spatial relationships (above, below, left, right, connected to)
- Any measurements or numeric values visible
- Annotations, labels, or markings
- Warnings, hazard indicators, or safety markings
- Any anomalies or unusual features
- Technical observations relevant to industrial/engineering context

For each finding, classify as:
- OBSERVED: directly visible in the image
- INFERRED: your interpretation of what you see

Return this JSON structure:
{{
    "description": "overall description",
    "entities": ["list of entities found"],
    "attributes": ["notable attributes"],
    "relationships": ["entity_a is connected to entity_b"],
    "spatial_info": ["entity_a is to the left of entity_b"],
    "measurements": ["any visible measurements"],
    "annotations": ["visible text annotations"],
    "warnings": ["visible warnings or hazard indicators"],
    "anomalies": ["unusual or notable features"],
    "technical_observations": ["engineering/technical observations"],
    "observed": ["things directly visible"],
    "inferred": ["interpretations"],
    "text_content": ["any text in the image"],
    "uncertainties": ["things you cannot determine"]
}}"""


def _safe_list(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item).strip() for item in items if item and str(item).strip()]


class VisionModel:
    """
    Communicates with the Ollama REST API for local vision-language inference.

    Wraps the Qwen2.5-VL-3B model (configurable) running in Ollama.
    All requests go to localhost — no external network calls.

    Usage:
        vlm = VisionModel()
        if vlm.is_available():
            result = vlm.analyze_image("path/to/image.png")
            print(result.description)
    """

    def __init__(self) -> None:
        """Initialize with settings from config."""
        self.base_url = OLLAMA_BASE_URL
        self.model = VLM_MODEL
        self.timeout = VLM_TIMEOUT
        try:
            validate_url(self.base_url)
        except ValueError as exc:
            logger.error("VLM URL validation failed: %s", exc)
            raise

    # =================================================================
    # Availability Check
    # =================================================================

    def is_available(self) -> bool:
        """
        Check if Ollama is running and the required VLM model is loaded.

        Makes a GET request to Ollama's /api/tags endpoint to list
        available models, then checks if our configured model is present.

        Returns:
            True if Ollama is running and the model is available.
            False if Ollama is down or the model isn't pulled.
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/tags",
                timeout=10,  # Short timeout for availability check
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if our model name appears (partial match for tag variants)
            available = any(self.model in name for name in model_names)

            if not available:
                logger.warning(
                    "Model '%s' not found in Ollama. Available: %s",
                    self.model,
                    model_names,
                )
            return available

        except requests.ConnectionError:
            logger.error(
                "Cannot connect to Ollama at %s. Is it running?",
                self.base_url,
            )
            return False
        except requests.RequestException as exc:
            logger.error("Ollama availability check failed: %s", exc)
            return False

    # =================================================================
    # Core Ollama Communication
    # =================================================================

    def _call_ollama(
        self,
        prompt: str,
        image_path: Optional[Union[str, Path]] = None,
    ) -> tuple[str, Optional[ErrorDetail]]:
        """
        Call Ollama's /api/generate endpoint with a text prompt and
        optional image.

        Args:
            prompt: The text prompt to send to the model.
            image_path: Optional path to an image file. If provided,
                the image is base64-encoded and included in the request.

        Returns:
            Tuple of (response_text, error).
            On success: (text, None).
            On failure: ("", ErrorDetail).
        """
        # Build the request payload
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,  # Get the complete response at once
            "options": {
                "num_ctx": VLM_NUM_CTX,
            },
        }

        # Encode and attach the image if provided
        if image_path:
            try:
                base64_image = encode_image_base64(image_path)
                payload["images"] = [base64_image]
            except FileNotFoundError:
                return "", ErrorDetail(
                    code=ErrorCode.FILE_NOT_FOUND,
                    message=f"Image file not found: {image_path}",
                )
            except Exception as exc:
                return "", ErrorDetail(
                    code=ErrorCode.IMAGE_CORRUPTED,
                    message=f"Failed to encode image: {exc}",
                )

        # Send the request to Ollama
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json().get("response", ""), None

        except requests.Timeout:
            logger.error("VLM request timed out after %ds", self.timeout)
            return "", ErrorDetail(
                code=ErrorCode.VLM_TIMEOUT,
                message=f"VLM request timed out after {self.timeout} seconds",
            )

        except requests.ConnectionError:
            logger.error("Cannot connect to Ollama at %s", self.base_url)
            return "", ErrorDetail(
                code=ErrorCode.VLM_UNAVAILABLE,
                message=f"Cannot connect to Ollama at {self.base_url}",
            )

        except requests.RequestException as exc:
            logger.error("VLM request failed: %s", exc)
            return "", ErrorDetail(
                code=ErrorCode.VLM_UNAVAILABLE,
                message=f"VLM request failed: {exc}",
            )

    # =================================================================
    # Image Analysis
    # =================================================================

    def analyze_image(
        self, image_path: Union[str, Path]
    ) -> ImageAnalysisResult:
        """
        Analyze an image using the VLM and return structured results.

        Sends a structured prompt that instructs the model to:
          - Describe what it sees
          - List detected objects
          - Separate OBSERVED (directly visible) from INFERRED (interpretation)
          - Note any visible text
          - Flag uncertainties

        Args:
            image_path: Path to the image file.

        Returns:
            ImageAnalysisResult with observations, objects, text content,
            and uncertainties. Confidence is always marked as unavailable
            because VLMs don't provide calibrated scores.
        """
        source_name = Path(image_path).name

        # --- Check availability ---
        if not self.is_available():
            return ImageAnalysisResult(
                success=False,
                image=source_name,
                error=ErrorDetail(
                    code=ErrorCode.VLM_UNAVAILABLE,
                    message="Vision model is not available in Ollama",
                ),
            )

        # --- Call the VLM ---
        response_text, error = self._call_ollama(
            IMAGE_ANALYSIS_PROMPT, image_path
        )

        if error:
            return ImageAnalysisResult(
                success=False,
                image=source_name,
                error=error,
            )

        if not response_text.strip():
            return ImageAnalysisResult(
                success=False,
                image=source_name,
                error=ErrorDetail(
                    code=ErrorCode.EMPTY_RESULT,
                    message="VLM returned empty response",
                ),
            )

        # --- Parse the JSON response ---
        parsed = safe_json_parse(response_text)

        if not parsed:
            # VLM didn't return valid JSON — return raw text as description
            logger.warning("VLM response was not valid JSON, using as raw text")
            return ImageAnalysisResult(
                success=True,
                image=source_name,
                description=response_text.strip(),
                confidence=ConfidenceInfo(available=False),
                warnings=["VLM response was not structured JSON"],
            )

        # --- Build structured observations ---
        observations: list[Observation] = []

        # Direct observations (things the model can SEE)
        for obs_text in parsed.get("observed", []):
            if isinstance(obs_text, str) and obs_text.strip():
                observations.append(Observation(
                    type="observed",
                    content=obs_text.strip(),
                ))

        # Inferences (things the model THINKS/INTERPRETS)
        for inf_text in parsed.get("inferred", []):
            if isinstance(inf_text, str) and inf_text.strip():
                observations.append(Observation(
                    type="inferred",
                    content=inf_text.strip(),
                ))

        return ImageAnalysisResult(
            success=True,
            image=source_name,
            description=parsed.get("description", ""),
            objects=parsed.get("objects", []),
            observations=observations,
            text_content=parsed.get("text_content", []),
            uncertainties=parsed.get("uncertainties", []),
            confidence=ConfidenceInfo(available=False),  # VLMs don't give scores
        )
        
    def analyze_image_deep(
        self, image_path: Union[str, Path]
    ) -> ImageAnalysisResult:
        """
        Deep analysis of an image with enhanced entity/relationship extraction.
        
        Uses the DEEP_ANALYSIS_PROMPT to extract more detailed information
        than the standard analyze_image method.
        """
        source_name = Path(image_path).name
        
        if not self.is_available():
            return ImageAnalysisResult(
                success=False,
                image=source_name,
                error=ErrorDetail(
                    code=ErrorCode.VLM_UNAVAILABLE,
                    message="Vision model is not available",
                ),
            )
        
        response_text, error = self._call_ollama(DEEP_ANALYSIS_PROMPT, image_path)
        
        if error:
            return ImageAnalysisResult(
                success=False,
                image=source_name,
                error=error,
            )
        
        if not response_text.strip():
            return ImageAnalysisResult(
                success=False,
                image=source_name,
                error=ErrorDetail(
                    code=ErrorCode.EMPTY_RESULT,
                    message="VLM returned empty response",
                ),
            )
        
        parsed = safe_json_parse(response_text)
        if not parsed:
            return ImageAnalysisResult(
                success=True,
                image=source_name,
                description=response_text.strip(),
                confidence=ConfidenceInfo(available=False),
                warnings=["VLM response was not structured JSON"],
            )
        
        # Build observations
        observations: list[Observation] = []
        for obs_text in parsed.get("observed", []):
            if isinstance(obs_text, str) and obs_text.strip():
                observations.append(Observation(type="observed", content=obs_text.strip()))
        for inf_text in parsed.get("inferred", []):
            if isinstance(inf_text, str) and inf_text.strip():
                observations.append(Observation(type="inferred", content=inf_text.strip()))
        
        return ImageAnalysisResult(
            success=True,
            image=source_name,
            description=parsed.get("description", ""),
            objects=_safe_list(parsed.get("entities", [])),
            observations=observations,
            text_content=_safe_list(parsed.get("text_content", [])),
            uncertainties=_safe_list(parsed.get("uncertainties", [])),
            entities=_safe_list(parsed.get("entities", [])),
            relationships=_safe_list(parsed.get("relationships", [])),
            spatial_info=_safe_list(parsed.get("spatial_info", [])),
            technical_observations=_safe_list(parsed.get("technical_observations", [])),
            anomalies=_safe_list(parsed.get("anomalies", [])),
            confidence=ConfidenceInfo(available=False),
        )

    # =================================================================
    # P&ID Analysis
    # =================================================================

    def analyze_for_pid(
        self, image_path: Union[str, Path]
    ) -> dict[str, Any]:
        """
        Run P&ID-specific VLM analysis.

        Uses a specialized prompt to identify equipment, valves,
        instruments, piping, and connections in engineering drawings.

        Args:
            image_path: Path to the P&ID image.

        Returns:
            Parsed dict with P&ID components, or empty dict on failure.
            The pid_analyzer.py module merges this with OCR results.
        """
        if not self.is_available():
            logger.warning("VLM unavailable for P&ID analysis")
            return {}

        response_text, error = self._call_ollama(
            PID_ANALYSIS_PROMPT, image_path
        )

        if error or not response_text.strip():
            logger.warning("P&ID VLM analysis returned no data")
            return {}

        parsed = safe_json_parse(response_text)
        if not parsed:
            logger.warning("P&ID VLM response was not valid JSON")
            return {}

        return parsed

    # =================================================================
    # Simple Figure Description
    # =================================================================

    def describe_figure(self, image_path: Union[str, Path]) -> str:
        """
        Generate a brief text description of a figure/image.

        Used by the document analyzer for embedded images in PDFs.
        Simpler than analyze_image() — returns plain text, not JSON.

        Args:
            image_path: Path to the figure image.

        Returns:
            Plain text description, or a fallback message on failure.
        """
        if not self.is_available():
            return ""

        response_text, error = self._call_ollama(
            FIGURE_DESCRIPTION_PROMPT, image_path
        )

        if error or not response_text.strip():
            return ""

        return response_text.strip()

    def describe_figure_from_pil(self, pil_image) -> str:
        """
        Describe a PIL Image by saving it to a temporary file first.

        Ollama needs a file path for base64 encoding, so we write
        the PIL image to a temp file, call describe_figure, then
        clean up.

        Args:
            pil_image: A PIL Image object.

        Returns:
            Plain text description.
        """
        import os

        try:
            # Save PIL image to a temp file
            fd, temp_path = tempfile.mkstemp(suffix=".png", prefix="sovara_fig_")
            os.close(fd)

            pil_image.save(temp_path, "PNG")
            description = self.describe_figure(temp_path)

            # Clean up
            try:
                os.unlink(temp_path)
            except OSError:
                pass

            return description

        except Exception as exc:
            logger.warning("Failed to describe figure from PIL image: %s", exc)
            return ""
            
    # =================================================================
    # VQA
    # =================================================================

    def answer_question(
        self, image_path: Union[str, Path], question: str
    ) -> dict[str, Any]:
        """
        Answer a visual question about an image.
        
        Uses the VLM to answer a specific question based on what
        is visible in the image. Returns structured response with
        observations, inferences, and uncertainties.
        
        Args:
            image_path: Path to the image.
            question: The question to answer.
            
        Returns:
            Dict with answer, observations, inferences, uncertainties.
            Returns empty/error dict on failure.
        """
        if not self.is_available():
            return {
                "answer": "",
                "observations": [],
                "inferences": [],
                "uncertainties": ["VLM unavailable"],
                "error": ErrorDetail(
                    code=ErrorCode.VLM_UNAVAILABLE,
                    message="Vision model is not available",
                ),
            }
        
        prompt = VQA_PROMPT.format(question=question)
        response_text, error = self._call_ollama(prompt, image_path)
        
        if error:
            return {
                "answer": "",
                "observations": [],
                "inferences": [],
                "uncertainties": [],
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
            "observations": _safe_list(parsed.get("observations", [])),
            "inferences": _safe_list(parsed.get("inferences", [])),
            "uncertainties": _safe_list(parsed.get("uncertainties", [])),
        }
