import os
import shutil
import logging
from typing import List, Dict, Any, Optional
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import pymupdf  # PyMuPDF
import docx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Tesseract binary path if available
def get_tesseract_path() -> Optional[str]:
    if settings.TESSERACT_CMD and os.path.exists(settings.TESSERACT_CMD):
        return settings.TESSERACT_CMD
    
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        shutil.which("tesseract"),
    ]
    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand
    return None

tesseract_path = get_tesseract_path()
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    logger.info(f"Configured Tesseract OCR path: {tesseract_path}")
else:
    logger.warning("Tesseract binary not detected. OCR will fall back to digital extraction or graceful notice.")


class DocumentParser:
    """
    Unified multi-format document parser.
    Supports:
    - Digital PDF (PyMuPDF)
    - Scanned PDF (PyMuPDF rendering + Tesseract OCR)
    - Images: PNG, JPG, JPEG, WEBP, BMP (Pillow preprocessing + Tesseract OCR)
    - DOCX (python-docx)
    - Plain text / Markdown
    """

    @staticmethod
    def preprocess_image(image: Image.Image) -> Image.Image:
        """
        Applies grayscale, contrast enhancement, and adaptive filtering for high OCR accuracy.
        """
        # Convert to Grayscale
        gray = image.convert("L")
        
        # Enhance Contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.0)
        
        # Noise reduction / Sharpening
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        return sharpened

    @classmethod
    def ocr_image(cls, image: Image.Image) -> str:
        """
        Performs OCR on a PIL Image with preprocessing.
        """
        processed = cls.preprocess_image(image)
        try:
            text = pytesseract.image_to_string(processed, lang="eng")
            return text.strip()
        except Exception as e:
            logger.warning(f"OCR execution error: {e}")
            return ""

    @classmethod
    def parse_pdf(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from PDF page by page.
        If a page has minimal digital text, uses OCR.
        Preserves exact 1-indexed page numbers.
        """
        pages_content = []
        doc = pymupdf.open(file_path)
        
        for page_idx in range(len(doc)):
            page_num = page_idx + 1
            page = doc[page_idx]
            text = page.get_text("text").strip()
            
            # If digital text is scarce (< 30 characters), attempt OCR
            if len(text) < 30 and tesseract_path:
                try:
                    # Render page as high-res pixmap (300 DPI)
                    pix = page.get_pixmap(dpi=300)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = cls.ocr_image(img)
                    if len(ocr_text) > len(text):
                        text = ocr_text
                except Exception as e:
                    logger.warning(f"Error performing OCR on PDF page {page_num}: {e}")
            
            if text:
                pages_content.append({
                    "page_number": page_num,
                    "section": f"Page {page_num}",
                    "text": text
                })
        
        doc.close()
        return pages_content

    @classmethod
    def parse_image(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text from image file using Pillow and Tesseract OCR.
        """
        try:
            with Image.open(file_path) as img:
                text = cls.ocr_image(img)
                if not text:
                    text = f"[Image Document: {os.path.basename(file_path)} - No readable text extracted]"
                return [{
                    "page_number": 1,
                    "section": "Image Content",
                    "text": text
                }]
        except Exception as e:
            logger.error(f"Failed to parse image {file_path}: {e}")
            return [{
                "page_number": 1,
                "section": "Image Content",
                "text": f"[Error reading image: {str(e)}]"
            }]

    @classmethod
    def parse_docx(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Extracts text and heading sections from a DOCX document.
        """
        doc = docx.Document(file_path)
        pages_content = []
        current_section = "General"
        current_paragraphs = []
        page_num = 1
        
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            
            # If it's a heading, we start a new section
            if p.style and p.style.name.startswith("Heading"):
                if current_paragraphs:
                    pages_content.append({
                        "page_number": page_num,
                        "section": current_section,
                        "text": "\n".join(current_paragraphs)
                    })
                    current_paragraphs = []
                    # Approximate page boundary for long documents
                    if len(pages_content) % 3 == 0:
                        page_num += 1
                current_section = text
            else:
                current_paragraphs.append(text)
        
        if current_paragraphs:
            pages_content.append({
                "page_number": page_num,
                "section": current_section,
                "text": "\n".join(current_paragraphs)
            })
            
        return pages_content if pages_content else [{
            "page_number": 1,
            "section": "Document Content",
            "text": ""
        }]

    @classmethod
    def parse_txt(cls, file_path: str) -> List[Dict[str, Any]]:
        """
        Parses plain text / markdown files.
        """
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()
        
        # Split into approximate pages (every ~2000 characters)
        page_size = 2000
        pages = []
        for idx, i in enumerate(range(0, max(len(content), 1), page_size)):
            chunk_text = content[i:i + page_size].strip()
            if chunk_text:
                pages.append({
                    "page_number": idx + 1,
                    "section": f"Section {idx + 1}",
                    "text": chunk_text
                })
        return pages

    @classmethod
    def parse_document(cls, file_path: str, file_type: str) -> List[Dict[str, Any]]:
        """
        Main routing function for document parsing based on file extension / type.
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".pdf" or file_type == "application/pdf":
            return cls.parse_pdf(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"] or "image" in file_type:
            return cls.parse_image(file_path)
        elif ext in [".docx", ".doc"] or "word" in file_type:
            return cls.parse_docx(file_path)
        elif ext in [".txt", ".md", ".csv", ".json"]:
            return cls.parse_txt(file_path)
        else:
            # Fallback text reading
            return cls.parse_txt(file_path)
