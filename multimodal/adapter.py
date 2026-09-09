from typing import Dict, Any, List
import requests
import json
import base64
import os

OLLAMA_URL = "http://localhost:11434"
VISION_MODEL = "llava:latest"

def _check_vision_model() -> bool:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            # check if any vision model is available
            for m in models:
                if "llava" in m.lower() or "vision" in m.lower() or "minicpm" in m.lower():
                    global VISION_MODEL
                    VISION_MODEL = m
                    return True
    except:
        pass
    return False

class MultimodalAdapter:
    @staticmethod
    def extract_text(file_path: str) -> Dict[str, Any]:
        """Extracts text from a selectable PDF using PyMuPDF. If scanned (no text), it flags for OCR."""
        try:
            import fitz
            doc = fitz.open(file_path)
            text = ""
            for i in range(len(doc)):
                page = doc.load_page(i)
                text += page.get_text() + "\\n"
            
            if len(text.strip()) < 50:
                # Likely scanned PDF, needs OCR/Vision
                return {
                    "success": False,
                    "content_type": "scanned_pdf",
                    "text": "",
                    "uncertainties": ["Scanned PDF detected, requires OCR/Vision capability"],
                    "source": file_path,
                    "page": None
                }

            return {
                "success": True,
                "content_type": "document",
                "text": text.strip(),
                "uncertainties": [],
                "source": file_path,
                "page": None
            }
        except Exception as e:
            if "failed to open" in str(e).lower() or "cannot open" in str(e).lower():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        return {
                            "success": True, "content_type": "document", "text": f.read().strip(), "uncertainties": [], "source": file_path, "page": None
                        }
                except:
                    pass
            return {
                "success": False,
                "content_type": "document",
                "text": "",
                "uncertainties": [f"Document extraction error: {e}"],
                "source": file_path,
                "page": None
            }

    @staticmethod
    def _run_vision_model(prompt: str, image_path: str) -> Dict[str, Any]:
        if not _check_vision_model():
            return {
                "success": False,
                "error": "Local vision model unavailable",
                "uncertainties": ["Vision capability unavailable. Required model (e.g. llava) not found. Run 'ollama pull llava'"]
            }
            
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")
                
            payload = {
                "model": VISION_MODEL,
                "messages": [{
                    "role": "user",
                    "content": prompt,
                    "images": [img_b64]
                }],
                "stream": False
            }
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
            r.raise_for_status()
            content = r.json()["message"]["content"]
            
            return {
                "success": True,
                "content": content,
                "uncertainties": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Vision model inference failed: {e}",
                "uncertainties": [str(e)]
            }

    @staticmethod
    def analyze_image(image_path: str) -> Dict[str, Any]:
        res = MultimodalAdapter._run_vision_model("Analyze this image and list findings and objects in detail.", image_path)
        if not res["success"]:
            return {
                "success": False,
                "content_type": "image",
                "findings": [],
                "objects": [],
                "uncertainties": res.get("uncertainties", []),
                "source": image_path,
                "page": None
            }
            
        return {
            "success": True,
            "content_type": "image",
            "findings": [res["content"]],
            "objects": [],
            "uncertainties": ["Vision interpretation may be uncertain"],
            "source": image_path,
            "page": None
        }

    @staticmethod
    def analyze_document(file_path: str) -> Dict[str, Any]:
        return MultimodalAdapter.extract_text(file_path)

    @staticmethod
    def analyze_pid(image_path: str) -> Dict[str, Any]:
        prompt = "Analyze this P&ID diagram. Identify equipment labels, visible components, line connections, text labels, and anomalies. Do NOT invent symbols or connections."
        res = MultimodalAdapter._run_vision_model(prompt, image_path)
        if not res["success"]:
            return {
                "success": False,
                "content_type": "pid",
                "equipment": [],
                "connections": [],
                "labels": [],
                "findings": [],
                "uncertainties": res.get("uncertainties", []),
                "source": image_path
            }
            
        return {
            "success": True,
            "content_type": "pid",
            "equipment": [],
            "connections": [],
            "labels": [],
            "findings": [res["content"]],
            "uncertainties": ["P&ID parsing heavily relies on VLM and may contain ambiguous interpretations. Not engineering-grade."],
            "source": image_path
        }