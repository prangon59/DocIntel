"""OCR and image preprocessing engine using OpenCV and Tesseract."""

import logging
from dataclasses import dataclass

import cv2
import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger("docintel.ocr")


@dataclass
class OCRPageResult:
    """OCR extraction result for an image or rendered PDF page."""

    text: str
    confidence: float  # Normalized 0.0 - 1.0
    char_count: int


def preprocess_image(image_input: np.ndarray | Image.Image) -> np.ndarray:
    """Apply computer vision preprocessing: grayscale, deskew, denoise, and Otsu thresholding.

    Args:
        image_input: NumPy array (OpenCV format) or PIL Image.

    Returns:
        Preprocessed binarized NumPy image array ready for OCR.
    """
    img = np.array(image_input) if isinstance(image_input, Image.Image) else image_input.copy()

    # 1. Convert to Grayscale
    if len(img.shape) == 3:
        if img.shape[2] == 4:
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img

    # 2. Deskew detection and correction
    try:
        # Invert colors so text is foreground for contour / minAreaRect
        thresh_inv = cv2.bitwise_not(gray)
        coords = np.column_stack(np.where(thresh_inv > 0))
        if coords.shape[0] > 50:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            if abs(angle) > 0.5 and abs(angle) < 45:
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                m = cv2.getRotationMatrix2D(center, angle, 1.0)
                gray = cv2.warpAffine(
                    gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
                )
    except Exception as exc:
        logger.debug("Deskew calculation skipped: %s", exc)

    # 3. Denoising
    denoised = cv2.medianBlur(gray, 3)

    # 4. Adaptive Otsu Thresholding
    _, binarized = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binarized


def extract_ocr_from_image(
    image_input: np.ndarray | Image.Image,
    lang: str = "eng",
) -> OCRPageResult:
    """Run OCR extraction with Tesseract and OpenCV preprocessing.

    Args:
        image_input: Raw image input.
        lang: Tesseract language model.

    Returns:
        OCRPageResult with text, average token confidence, and char count.
    """
    processed_img = preprocess_image(image_input)

    try:
        # Extract word-level data for confidence scoring
        data = pytesseract.image_to_data(
            processed_img,
            lang=lang,
            output_type=pytesseract.Output.DICT,
            config="--psm 1",
        )
        words: list[str] = []
        confidences: list[float] = []

        n_boxes = len(data["text"])
        for i in range(n_boxes):
            word = data["text"][i].strip()
            conf = float(data["conf"][i])
            if word and conf >= 0:
                words.append(word)
                confidences.append(conf)

        extracted_text = " ".join(words)
        avg_confidence = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0

        return OCRPageResult(
            text=extracted_text,
            confidence=round(avg_confidence, 4),
            char_count=len(extracted_text),
        )
    except Exception as exc:
        logger.warning("Tesseract OCR execution error: %s", exc)
        # Fallback to basic string extraction or empty result on error
        try:
            raw_text = pytesseract.image_to_string(processed_img, lang=lang)
            return OCRPageResult(
                text=raw_text.strip(),
                confidence=0.5,
                char_count=len(raw_text.strip()),
            )
        except Exception:
            return OCRPageResult(
                text="",
                confidence=0.0,
                char_count=0,
            )


def extract_ocr_from_multipage_tiff(file_path: str) -> list[OCRPageResult]:
    """Iterate frames of a multi-page TIFF and extract OCR per frame."""
    results: list[OCRPageResult] = []
    with Image.open(file_path) as img:
        page_index = 0
        while True:
            try:
                img.seek(page_index)
                page_img = img.copy()
                result = extract_ocr_from_image(page_img)
                results.append(result)
                page_index += 1
            except EOFError:
                break
    return results
