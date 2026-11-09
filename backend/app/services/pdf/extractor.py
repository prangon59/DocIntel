"""Digital PDF extraction with per-page OCR fallback via PyMuPDF and Tesseract."""

import logging
import re
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image

from app.core.config import settings
from app.services.ocr.engine import extract_ocr_from_image

logger = logging.getLogger("docintel.pdf")


@dataclass
class PDFPageExtraction:
    """Extraction output for an individual PDF page."""

    page_number: int  # 1-indexed
    text: str
    method: str  # "digital_pdf" or "tesseract_ocr"
    ocr_confidence: float | None
    char_count: int


class PDFProcessingError(Exception):
    """Raised when a PDF cannot be opened or parsed."""

    pass


def inspect_pdf(file_path: str) -> tuple[int, bool, str | None]:
    """Inspect PDF structure without loading all pages into memory.

    Returns:
        Tuple of (page_count, is_encrypted, error_message).
    """
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            return 0, True, "PDF is password protected / encrypted."
        page_count = len(doc)
        doc.close()
        return page_count, False, None
    except Exception as exc:
        return 0, False, f"Failed to open PDF document: {exc}"


def extract_page_text(
    file_path: str,
    page_number: int,  # 1-indexed
    char_threshold: int = settings.OCR_FALLBACK_CHAR_THRESHOLD,
) -> PDFPageExtraction:
    """Extract text from a specific PDF page, triggering OCR fallback if char count < threshold.

    Args:
        file_path: Filesystem path to the PDF.
        page_number: 1-indexed page number to extract.
        char_threshold: Min character count to avoid OCR fallback (default 30).

    Returns:
        PDFPageExtraction with extracted text, method, confidence, and char count.
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        raise PDFProcessingError(f"Corrupted PDF file: {exc}") from exc

    if doc.is_encrypted:
        doc.close()
        raise PDFProcessingError("Cannot process password-protected PDF.")

    page_idx = page_number - 1
    if page_idx < 0 or page_idx >= len(doc):
        doc.close()
        raise IndexError(f"Page number {page_number} out of bounds (1..{len(doc)}).")

    page = doc[page_idx]
    # 1. Attempt digital text extraction
    digital_text = page.get_text("text").strip()
    char_count = len(digital_text)

    # 2. Check if digital text meets character threshold
    if char_count >= char_threshold:
        doc.close()
        return PDFPageExtraction(
            page_number=page_number,
            text=digital_text,
            method="digital_pdf",
            ocr_confidence=1.0,
            char_count=char_count,
        )

    # 3. Fallback to OCR on rendered high-resolution page
    logger.info(
        "Page %d has %d chars (< %d threshold); invoking OCR fallback.",
        page_number,
        char_count,
        char_threshold,
    )
    try:
        pix = page.get_pixmap(dpi=300)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        ocr_result = extract_ocr_from_image(img)
        doc.close()

        # If OCR yields more text than digital, prefer OCR
        final_text = ocr_result.text if len(ocr_result.text) >= char_count else digital_text
        return PDFPageExtraction(
            page_number=page_number,
            text=final_text,
            method="tesseract_ocr",
            ocr_confidence=ocr_result.confidence,
            char_count=len(final_text),
        )
    except Exception as exc:
        doc.close()
        logger.warning(
            "OCR fallback failed on page %d: %s. Returning raw digital text.", page_number, exc
        )
        return PDFPageExtraction(
            page_number=page_number,
            text=digital_text,
            method="digital_pdf",
            ocr_confidence=0.5,
            char_count=char_count,
        )


def extract_all_pdf_pages(
    file_path: str,
    char_threshold: int = settings.OCR_FALLBACK_CHAR_THRESHOLD,
) -> list[PDFPageExtraction]:
    """Sequentially extract all pages of a PDF (used for small PDFs or testing)."""
    page_count, is_enc, err = inspect_pdf(file_path)
    if err:
        raise PDFProcessingError(err)

    extractions: list[PDFPageExtraction] = []
    for p in range(1, page_count + 1):
        extractions.append(extract_page_text(file_path, p, char_threshold))
    return extractions


def segment_invoice_pages(pages: list[PDFPageExtraction]) -> list[list[int]]:
    """Group sequential pages into invoice segments based on header change heuristics.

    Returns:
        List of lists, where each inner list contains 1-indexed page numbers for one invoice.
    """
    if not pages:
        return []

    segments: list[list[int]] = []
    current_segment: list[int] = []

    # Patterns indicating the start of a distinct new invoice
    header_pattern = re.compile(
        r"(?:invoice\s*(?:no|number|#)?[:\s]+[a-z0-9\-_]+|tax\s*invoice|bill\s*to)",
        re.IGNORECASE,
    )

    for page in pages:
        text = page.text
        has_new_header = bool(header_pattern.search(text))

        if not current_segment:
            current_segment.append(page.page_number)
        elif has_new_header and "page 2" not in text.lower():
            # New invoice segment identified
            segments.append(current_segment)
            current_segment = [page.page_number]
        else:
            current_segment.append(page.page_number)

    if current_segment:
        segments.append(current_segment)

    return segments
