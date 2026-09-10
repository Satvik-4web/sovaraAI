from typing import Dict, Any, List
from multimodal.pipeline import analyze_document, analyze_image, analyze_pid
from multimodal.schemas import DocumentAnalysisResult, ImageAnalysisResult, PIDAnalysisResult

class MultimodalAdapter:
    @staticmethod
    def extract_text(file_path: str) -> Dict[str, Any]:
        """Maps to Person B's analyze_document"""
        try:
            res: DocumentAnalysisResult = analyze_document(file_path)
            
            text = ""
            uncertainties = []
            if res.success:
                for page in res.pages:
                    if page.text:
                        text += page.text + "\\n"
                    if page.visual_observations:
                        for obs in page.visual_observations:
                            if hasattr(obs, 'confidence') and obs.confidence:
                                if obs.confidence.available and obs.confidence.score is not None and obs.confidence.score < 0.7:
                                    uncertainties.append(f"Low confidence in {obs.type} observation: {obs.content}")
            
            if not res.success or res.error:
                uncertainties.append(res.error or "Document analysis failed")
                if "vision model" in (res.error or "").lower() or "qwen2.5vl" in (res.error or "").lower():
                    uncertainties.append("Vision capability unavailable. Required model: qwen2.5vl:3b. Run 'ollama run qwen2.5vl:3b'")
                    
            return {
                "success": res.success,
                "content_type": "document",
                "text": text.strip(),
                "uncertainties": uncertainties + res.warnings,
                "source": file_path,
                "page": None
            }
        except Exception as e:
            err_msg = str(e)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                return {"success": True, "content_type": "document", "text": text, "uncertainties": [], "source": file_path, "page": None}
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="utf-16") as f:
                        text = f.read().strip()
                    return {"success": True, "content_type": "document", "text": text, "uncertainties": [], "source": file_path, "page": None}
                except: pass
            except: pass
            
            if "not installed" in err_msg.lower() or "not found" in err_msg.lower():
                err_msg += " -> Run 'ollama run qwen2.5vl:3b'"
            return {
                "success": False,
                "content_type": "document",
                "text": "",
                "uncertainties": [f"Document extraction error: {err_msg}"],
                "source": file_path,
                "page": None
            }

    @staticmethod
    def analyze_image(image_path: str) -> Dict[str, Any]:
        try:
            res: ImageAnalysisResult = analyze_image(image_path)
            findings = []
            objects = []
            if res.success:
                if res.description: findings.append(res.description)
                findings.extend(res.technical_observations)
                findings.extend(res.anomalies)
                objects.extend([obj.label for obj in res.objects])
                
            uncertainties = res.uncertainties + res.warnings
            if not res.success or res.error:
                uncertainties.append(res.error or "Image analysis failed")
                if "qwen2.5vl:3b" in str(res.error) or "ollama" in str(res.error):
                    uncertainties.append("Vision capability unavailable. Required model: qwen2.5vl:3b. Run 'ollama run qwen2.5vl:3b'")

            return {
                "success": res.success,
                "content_type": "image",
                "findings": findings,
                "objects": objects,
                "uncertainties": uncertainties,
                "source": image_path,
                "page": None
            }
        except Exception as e:
            err_msg = str(e)
            if "not installed" in err_msg.lower() or "not found" in err_msg.lower():
                err_msg += " -> Run 'ollama run qwen2.5vl:3b'"
            return {
                "success": False,
                "content_type": "image",
                "findings": [],
                "objects": [],
                "uncertainties": [f"Image analysis error: {err_msg}"],
                "source": image_path,
                "page": None
            }

    @staticmethod
    def analyze_document_wrapper(file_path: str) -> Dict[str, Any]:
        return MultimodalAdapter.extract_text(file_path)

    @staticmethod
    def analyze_pid(image_path: str) -> Dict[str, Any]:
        try:
            res: PIDAnalysisResult = analyze_pid(image_path)
            equipment = []
            labels = []
            if res.success:
                equipment = [eq.tag for eq in res.equipment if eq.tag]
                labels = res.annotations
                
            uncertainties = res.uncertainties + res.warnings
            if not res.success or res.error:
                uncertainties.append(res.error or "P&ID analysis failed")
                if "qwen2.5vl:3b" in str(res.error) or "ollama" in str(res.error):
                    uncertainties.append("Vision capability unavailable. Required model: qwen2.5vl:3b. Run 'ollama run qwen2.5vl:3b'")

            return {
                "success": res.success,
                "content_type": "pid",
                "equipment": equipment,
                "connections": [f"{c.from_tag} -> {c.to_tag}" for c in res.connections],
                "labels": labels,
                "findings": [obs.content for obs in res.observations],
                "uncertainties": uncertainties,
                "source": image_path
            }
        except Exception as e:
            err_msg = str(e)
            if "not installed" in err_msg.lower() or "not found" in err_msg.lower():
                err_msg += " -> Run 'ollama run qwen2.5vl:3b'"
            return {
                "success": False,
                "content_type": "pid",
                "equipment": [],
                "connections": [],
                "labels": [],
                "findings": [],
                "uncertainties": [f"P&ID analysis error: {err_msg}"],
                "source": image_path
            }