import logging
from pathlib import Path
from typing import List, Dict, Union
import fitz  # PyMuPDF
import PIL.Image
import io

from multimodal.config import PDF_RENDER_DPI, ErrorCode

logger = logging.getLogger("sovara.multimodal.pdf_processor")

class PDFProcessor:
    """PDF processing using PyMuPDF (fitz)."""

    def extract_text(self, pdf_path: Union[str, Path]) -> List[Dict[str, Union[int, str]]]:
        """
        Extract selectable text from each page of the PDF.
        """
        results = []
        try:
            with fitz.open(str(Path(pdf_path).resolve())) as doc:
                if doc.is_encrypted:
                    logger.warning(f"PDF is encrypted: {pdf_path}")
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    results.append({"page": page_num + 1, "text": text})
        except fitz.FileDataError as e:
            logger.error(f"Corrupted or invalid PDF {pdf_path}: {e}")
        except RuntimeError as e:
            logger.error(f"Runtime error processing PDF {pdf_path}: {e}")
        return results

    def render_pages(self, pdf_path: Union[str, Path], dpi: int = None) -> List[PIL.Image.Image]:
        """
        Render each page of the PDF to a PIL Image.
        """
        if dpi is None:
            dpi = PDF_RENDER_DPI
            
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        images = []
        
        try:
            with fitz.open(str(Path(pdf_path).resolve())) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=mat)
                    img = PIL.Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                    images.append(img)
        except Exception as e:
            logger.error(f"Error rendering pages for {pdf_path}: {e}")
            
        return images

    def extract_images(self, pdf_path: Union[str, Path]) -> List[Dict]:
        """
        Extract embedded images from the PDF.
        """
        extracted_images = []
        try:
            with fitz.open(str(Path(pdf_path).resolve())) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    image_list = page.get_images(full=True)
                    
                    for img_index, img_info in enumerate(image_list):
                        xref = img_info[0]
                        try:
                            base_image = doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            
                            img = PIL.Image.open(io.BytesIO(image_bytes))
                            img.load()
                            
                            extracted_images.append({
                                "page": page_num,
                                "index": img_index,
                                "image": img,
                                "width": base_image["width"],
                                "height": base_image["height"]
                            })
                        except Exception as e:
                            logger.error(f"Failed to extract image {img_index} on page {page_num}: {e}")
        except Exception as e:
            logger.error(f"Error extracting images from {pdf_path}: {e}")
            
        return extracted_images

    def is_scanned(self, pdf_path: Union[str, Path]) -> bool:
        """
        Detect if the PDF is scanned.
        """
        try:
            total_text_len = 0
            with fitz.open(str(Path(pdf_path).resolve())) as doc:
                pages_to_check = min(3, len(doc))
                for page_num in range(pages_to_check):
                    page = doc[page_num]
                    text = page.get_text()
                    total_text_len += len(text.strip())
                    
                if total_text_len < 50:
                    return True
        except Exception as e:
            logger.error(f"Error checking if {pdf_path} is scanned: {e}")
            return True
            
        return False

    def get_page_count(self, pdf_path: Union[str, Path]) -> int:
        """
        Get the total number of pages in the PDF.
        """
        try:
            with fitz.open(str(Path(pdf_path).resolve())) as doc:
                return len(doc)
        except Exception as e:
            logger.error(f"Error getting page count for {pdf_path}: {e}")
            return 0
