import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from typing import List, Dict, Any, Optional
import pytesseract
from src.config import Config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SlideOCR:
    def __init__(self, config: Config):
        self.config = config
        if config.TESSERACT_CMD:
            pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
        
        self._check_tesseract()
    
    def _check_tesseract(self) -> None:
        try:
            pytesseract.get_tesseract_version()
            logger.debug("Tesseract OCR available")
        except Exception as e:
            logger.warning(f"Tesseract OCR not available: {e}")
    
    def extract_text_from_slides(self, aligned_slides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        slides_with_ocr = []
        
        for slide in aligned_slides:
            slide_copy = slide.copy()
            
            try:
                ocr_text = self.extract_text_from_image(slide['image_path'])
                slide_copy['ocr_text'] = ocr_text
                slide_copy['ocr_confidence'] = self._calculate_confidence(ocr_text)
                
                logger.debug(f"OCR extracted {len(ocr_text)} characters from slide {slide.get('slide_number')}")
                
            except Exception as e:
                logger.warning(f"OCR failed for slide {slide.get('slide_number')}: {e}")
                slide_copy['ocr_text'] = ""
                slide_copy['ocr_confidence'] = 0.0
            
            slides_with_ocr.append(slide_copy)
        
        logger.info(f"Completed OCR processing for {len(slides_with_ocr)} slides")
        return slides_with_ocr
    
    def extract_text_from_image(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        try:
            processed_image = self._preprocess_image(image_path)
            
            ocr_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,!?:;()[]{}"\'-+*/=<>@#$%&_|~`^'
            
            text = pytesseract.image_to_string(processed_image, config=ocr_config)
            
            cleaned_text = self._clean_ocr_text(text)
            return cleaned_text
            
        except Exception as e:
            logger.error(f"OCR processing failed for {image_path}: {e}")
            return ""
    
    def _preprocess_image(self, image_path: str) -> Image.Image:
        with Image.open(image_path) as img:
            img = img.convert('RGB')
            
            img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
            
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(1.2)
            
            img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            
            denoised = cv2.fastNlMeansDenoising(gray)
            
            _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            kernel = np.ones((1, 1), np.uint8)
            processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return Image.fromarray(processed)
    
    def _clean_ocr_text(self, text: str) -> str:
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            if len(line) < 2:
                continue
            
            if line.count(' ') == 0 and len(line) > 20:
                continue
            
            if any(char.isalnum() for char in line):
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _calculate_confidence(self, text: str) -> float:
        if not text:
            return 0.0
        
        total_chars = len(text)
        if total_chars == 0:
            return 0.0
        
        alphanumeric_chars = sum(1 for char in text if char.isalnum())
        confidence = alphanumeric_chars / total_chars
        
        return min(1.0, confidence)
    
    def get_text_regions(self, image_path: str) -> List[Dict[str, Any]]:
        try:
            with Image.open(image_path) as img:
                processed_img = self._preprocess_image(image_path)
                
                data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
                
                regions = []
                for i, text in enumerate(data['text']):
                    if text.strip():
                        confidence = data['conf'][i]
                        if confidence > 30:
                            regions.append({
                                'text': text.strip(),
                                'confidence': confidence,
                                'x': data['left'][i],
                                'y': data['top'][i],
                                'width': data['width'][i],
                                'height': data['height'][i]
                            })
                
                return regions
                
        except Exception as e:
            logger.error(f"Failed to extract text regions from {image_path}: {e}")
            return []
    
    def filter_slides_by_text_content(
        self, 
        slides_with_ocr: List[Dict[str, Any]], 
        min_text_length: int = 10,
        min_confidence: float = 0.3
    ) -> List[Dict[str, Any]]:
        filtered_slides = []
        
        for slide in slides_with_ocr:
            ocr_text = slide.get('ocr_text', '')
            ocr_confidence = slide.get('ocr_confidence', 0.0)
            
            if len(ocr_text) >= min_text_length and ocr_confidence >= min_confidence:
                filtered_slides.append(slide)
            else:
                logger.debug(
                    f"Filtered slide {slide.get('slide_number')} "
                    f"(text length: {len(ocr_text)}, confidence: {ocr_confidence:.2f})"
                )
        
        logger.info(f"OCR filtering: {len(slides_with_ocr)} -> {len(filtered_slides)} slides")
        return filtered_slides
    
    def combine_transcript_and_ocr(self, slides_with_ocr: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        combined_slides = []
        
        for slide in slides_with_ocr:
            slide_copy = slide.copy()
            
            transcript_text = slide.get('transcript_text', '')
            ocr_text = slide.get('ocr_text', '')
            
            combined_text_parts = []
            
            if transcript_text:
                combined_text_parts.append(f"Spoken: {transcript_text}")
            
            if ocr_text and slide.get('ocr_confidence', 0) > 0.3:
                combined_text_parts.append(f"Text on slide: {ocr_text}")
            
            slide_copy['combined_text'] = '\n\n'.join(combined_text_parts)
            combined_slides.append(slide_copy)
        
        return combined_slides