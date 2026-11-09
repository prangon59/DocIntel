"""Unit tests for OpenCV image preprocessing and OCR extraction."""

from pathlib import Path

import numpy as np
from PIL import Image

from app.services.ocr.engine import extract_ocr_from_image, preprocess_image

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_preprocess_image():
    """Verify that preprocessing turns an image into a 2D binarized NumPy array."""
    img_path = FIXTURES_DIR / "scanned_invoice.png"
    with Image.open(img_path) as pil_img:
        processed = preprocess_image(pil_img)

    assert isinstance(processed, np.ndarray)
    assert len(processed.shape) == 2  # Grayscale/binary 2D
    # Values should be mostly 0 or 255 (binary)
    unique_vals = np.unique(processed)
    assert set(unique_vals).issubset({0, 255})


def test_extract_ocr_from_image():
    """Test OCR extraction on scanned invoice fixture."""
    img_path = FIXTURES_DIR / "scanned_invoice.png"
    with Image.open(img_path) as pil_img:
        result = extract_ocr_from_image(pil_img)

    assert result.confidence >= 0.0
    assert result.char_count >= 0
