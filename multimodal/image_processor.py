import logging
import os
import tempfile
from pathlib import Path
from typing import Union, Optional
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from PIL import Image
except ImportError:
    Image = None

from multimodal import config

logger = logging.getLogger("sovara.multimodal.image_processor")

class ImagePreprocessor:
    """Image preprocessing using OpenCV and Pillow."""
    
    def __init__(self) -> None:
        """Initialize ImagePreprocessor."""
        if cv2 is None:
            logger.warning("cv2 is not installed. Image processing functions will fail.")
        if Image is None:
            logger.warning("PIL is not installed. Image processing functions will fail.")
            
    def _pil_to_cv2(self, image: "Image.Image") -> np.ndarray:
        """Convert a PIL image to an OpenCV numpy array."""
        try:
            # Check if image is already grayscale or has alpha
            if image.mode == 'L':
                return np.array(image)
            elif image.mode == 'RGBA':
                # Convert RGBA to BGR (ignore alpha for OpenCV processing here)
                return cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGR)
            else:
                return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            logger.error(f"Error converting PIL to cv2: {e}")
            raise

    def _cv2_to_pil(self, cv2_img: np.ndarray, is_gray: bool = False) -> "Image.Image":
        """Convert an OpenCV numpy array to a PIL image."""
        try:
            if is_gray or len(cv2_img.shape) == 2:
                return Image.fromarray(cv2_img)
            return Image.fromarray(cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB))
        except Exception as e:
            logger.error(f"Error converting cv2 to PIL: {e}")
            raise

    def preprocess_for_ocr(self, image: "Image.Image") -> "Image.Image":
        """
        Preprocess image for optimal OCR results.
        
        Args:
            image (PIL.Image.Image): Input image.
            
        Returns:
            PIL.Image.Image: Preprocessed image.
        """
        try:
            cv2_img = self._pil_to_cv2(image)
            
            # 1. Convert to grayscale
            if len(cv2_img.shape) == 3:
                gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv2_img
                
            # 2. Apply slight Gaussian blur (denoise)
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # 3. Apply adaptive thresholding for text contrast
            thresh = cv2.adaptiveThreshold(
                blurred, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            return self._cv2_to_pil(thresh, is_gray=True)
            
        except Exception as e:
            logger.error(f"Failed to preprocess for OCR: {e}")
            return image

    def preprocess_for_vlm(self, image_path: Union[str, Path]) -> Path:
        """
        Preprocess image for Vision Language Model input.
        
        Args:
            image_path (Union[str, Path]): Path to the input image.
            
        Returns:
            Path: Path to the processed and saved image.
        """
        try:
            img_path = Path(image_path)
            if not img_path.exists():
                raise FileNotFoundError(f"Image not found: {img_path}")
                
            # 1. Open image
            with Image.open(img_path) as img:
                # Load image to memory before processing
                img.load()
                
                # 2. Resize if larger than config.IMAGE_MAX_DIMENSION
                max_dim = getattr(config, 'IMAGE_MAX_DIMENSION', 2048)
                resized_img = self.resize_to_limit(img, max_dim)
                
                # 3. Save to temp file (JPEG quality 85)
                # Create a temp file
                fd, temp_path = tempfile.mkstemp(suffix=".jpg", prefix="vlm_prep_")
                os.close(fd)
                
                # Convert to RGB to save as JPEG (handles RGBA/P modes)
                if resized_img.mode in ('RGBA', 'P', 'LA'):
                    resized_img = resized_img.convert('RGB')
                    
                resized_img.save(temp_path, "JPEG", quality=85)
                
                return Path(temp_path)
                
        except Exception as e:
            logger.error(f"Failed to preprocess for VLM: {e}")
            raise

    def enhance_engineering_drawing(self, image: "Image.Image") -> "Image.Image":
        """
        Enhance engineering drawings (like P&ID) for better legibility.
        
        Args:
            image (PIL.Image.Image): Input drawing image.
            
        Returns:
            PIL.Image.Image: Enhanced drawing.
        """
        try:
            cv2_img = self._pil_to_cv2(image)
            
            # 1. Convert to grayscale
            if len(cv2_img.shape) == 3:
                gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv2_img
                
            # 2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            clahe_img = clahe.apply(gray)
            
            # 3. Apply bilateral filter (denoise while keeping edges)
            bilateral = cv2.bilateralFilter(clahe_img, 9, 75, 75)
            
            # 4. Apply Otsu's thresholding
            _, thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return self._cv2_to_pil(thresh, is_gray=True)
            
        except Exception as e:
            logger.error(f"Failed to enhance engineering drawing: {e}")
            return image

    def resize_to_limit(self, image: "Image.Image", max_dim: Optional[int] = None) -> "Image.Image":
        """
        Resize image keeping aspect ratio so the longest side <= max_dim.
        
        Args:
            image (PIL.Image.Image): Input image.
            max_dim (int, optional): Maximum dimension length. Defaults to config.IMAGE_MAX_DIMENSION.
            
        Returns:
            PIL.Image.Image: Resized image.
        """
        try:
            if max_dim is None:
                max_dim = getattr(config, 'IMAGE_MAX_DIMENSION', 2048)
                
            width, height = image.size
            if max(width, height) <= max_dim:
                return image.copy()
                
            # Calculate new dimensions
            scale = max_dim / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # Ensure dimensions > 0
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
        except Exception as e:
            logger.error(f"Failed to resize image: {e}")
            return image

    def detect_image_type(self, image: "Image.Image") -> str:
        """
        Detect whether an image is a photo, document, or engineering drawing.
        
        Args:
            image (PIL.Image.Image): Input image.
            
        Returns:
            str: One of 'photo', 'document', or 'drawing'.
        """
        try:
            cv2_img = self._pil_to_cv2(image)
            
            if len(cv2_img.shape) == 3:
                gray = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv2_img
                
            # Basic heuristics
            # 1. Variance of Laplacian for edge density
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # 2. Proportion of white/light pixels (documents and drawings are mostly white)
            light_pixels = np.sum(gray > 200)
            total_pixels = gray.size
            light_ratio = light_pixels / total_pixels if total_pixels > 0 else 0
            
            # 3. Check for color variance if it's a color image
            color_variance = 0
            if len(cv2_img.shape) == 3:
                # Calculate standard deviation of colors
                b, g, r = cv2.split(cv2_img)
                color_variance = np.var(r) + np.var(g) + np.var(b)
                
            # Classification logic
            if light_ratio > 0.7:
                # Mostly light background -> document or drawing
                if laplacian_var > 1500:
                    # High edge density and variation
                    return 'drawing'
                else:
                    return 'document'
            else:
                # If it has high color variance or not mostly white, likely a photo
                if color_variance > 5000 and laplacian_var < 2000:
                    return 'photo'
                else:
                    return 'document' # Default fallback
                    
        except Exception as e:
            logger.error(f"Failed to detect image type: {e}")
            return 'document'
