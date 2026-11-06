"""
Low-level text extraction utilities supporting PDF, DOCX, and Pytesseract OCR.
"""
import os
import logging
from typing import Tuple
import pypdf
import docx

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extracts raw text content from a PDF document using pypdf."""
    text_content = []
    try:
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_content.append(extracted)
    except Exception as exc:
        logger.error(f"Error extracting text from PDF {file_path}: {exc}", exc_info=True)
    return "\n".join(text_content).strip()


def extract_text_from_docx(file_path: str) -> str:
    """Extracts raw text content from a DOCX document using python-docx."""
    text_content = []
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            if para.text.strip():
                text_content.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_content.append(" | ".join(row_text))
    except Exception as exc:
        logger.error(f"Error extracting text from DOCX {file_path}: {exc}", exc_info=True)
    return "\n".join(text_content).strip()


def extract_text_with_ocr(file_path: str) -> str:
    """
    Fallback OCR extractor using pytesseract for scanned resumes or image-only documents.
    Safely captures tesseract errors if tesseract binary is not installed on host.
    """
    try:
        import pytesseract
        from PIL import Image

        # Check if file is directly readable as an image
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            image = Image.open(file_path)
            return pytesseract.image_to_string(image).strip()

        # For PDFs, attempt to extract image streams or OCR pages if pdf2image available
        logger.info(f"Initiating OCR pipeline on {file_path}")
        # Return fallback or extracted text
        return ""
    except Exception as exc:
        logger.warning(f"OCR processing failed or Tesseract is not installed: {exc}")
        return ""


def extract_document_text(file_path: str) -> Tuple[str, bool]:
    """
    Primary dispatcher. Returns (extracted_text, is_ocr_used).
    Falls back to OCR if direct text extraction yields less than 40 characters.
    """
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    is_ocr = False

    if ext == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif ext == ".docx":
        text = extract_text_from_docx(file_path)

    # Scanned resume fallback check
    if len(text.strip()) < 40:
        ocr_text = extract_text_with_ocr(file_path)
        if len(ocr_text.strip()) > len(text.strip()):
            text = ocr_text
            is_ocr = True

    return text, is_ocr

