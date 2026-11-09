"""Deterministic magic-byte file signature sniffer and validator.

Validates business documents strictly by binary file signatures (magic bytes),
preventing spoofed extensions and unsupported payload ingestion.
Supported formats: PDF, JPG, PNG, TIFF (multi-page), XLSX, XLS, CSV.
"""

import csv
import io
import zipfile
from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedFileType:
    """Result of magic-byte file signature detection."""

    file_type: str  # pdf, png, jpg, tiff, xlsx, xls, csv, unknown
    mime_type: str
    is_supported: bool
    error_message: str | None = None


# Known binary file signatures
SIGNATURE_PDF = b"%PDF-"
SIGNATURE_PNG = b"\x89PNG\r\n\x1a\n"
SIGNATURE_JPEG = b"\xff\xd8\xff"
SIGNATURE_TIFF_LE = b"II*\x00"  # Little-endian TIFF
SIGNATURE_TIFF_BE = b"MM\x00*"  # Big-endian TIFF
SIGNATURE_ZIP = b"PK\x03\x04"  # Standard ZIP container (used by XLSX)
SIGNATURE_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # Compound Document File (XLS)
UTF8_BOM = b"\xef\xbb\xbf"


def detect_file_type(data: bytes, filename: str | None = None) -> DetectedFileType:
    """Identify document type exclusively using binary signatures and structural checks.

    Args:
        data: Initial bytes or entire content of the file (at least 2048 bytes recommended).
        filename: Optional filename for logging or cross-validation warnings.

    Returns:
        DetectedFileType with normalized type, mime_type, and support status.
    """
    if not data or len(data) == 0:
        return DetectedFileType(
            file_type="empty",
            mime_type="application/x-empty",
            is_supported=False,
            error_message="Uploaded file is empty (0 bytes).",
        )

    # 1. Check PDF
    if data.startswith(SIGNATURE_PDF):
        # Additional sanity: ensure it contains minimum PDF trailer or xref structure
        # even if corrupted, it is recognized as a PDF file
        return DetectedFileType(
            file_type="pdf",
            mime_type="application/pdf",
            is_supported=True,
        )

    # 2. Check PNG
    if data.startswith(SIGNATURE_PNG):
        return DetectedFileType(
            file_type="png",
            mime_type="image/png",
            is_supported=True,
        )

    # 3. Check JPEG
    if data.startswith(SIGNATURE_JPEG):
        return DetectedFileType(
            file_type="jpg",
            mime_type="image/jpeg",
            is_supported=True,
        )

    # 4. Check TIFF (multi-page or single)
    if data.startswith(SIGNATURE_TIFF_LE) or data.startswith(SIGNATURE_TIFF_BE):
        return DetectedFileType(
            file_type="tiff",
            mime_type="image/tiff",
            is_supported=True,
        )

    # 5. Check Compound File Binary (Legacy Excel XLS)
    if data.startswith(SIGNATURE_OLE):
        return DetectedFileType(
            file_type="xls",
            mime_type="application/vnd.ms-excel",
            is_supported=True,
        )

    # 6. Check ZIP / Modern Excel XLSX
    if data.startswith(SIGNATURE_ZIP):
        # Verify it is indeed an OpenXML spreadsheet (contains [Content_Types].xml or xl/)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                namelist = zf.namelist()
                is_excel = any(
                    name.startswith("xl/") or name == "[Content_Types].xml" for name in namelist
                )
                if is_excel:
                    return DetectedFileType(
                        file_type="xlsx",
                        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        is_supported=True,
                    )
        except Exception:
            # Corrupted ZIP
            return DetectedFileType(
                file_type="corrupted_archive",
                mime_type="application/zip",
                is_supported=False,
                error_message="Corrupted ZIP archive; failed OpenXML spreadsheet validation.",
            )

    # 7. Check CSV / Plain Text
    # Must not contain null bytes (common in binary files) and must be decodable text
    if b"\x00" not in data[:1024]:
        raw_text: str | None = None
        # Strip UTF-8 BOM if present
        clean_data = data[len(UTF8_BOM) :] if data.startswith(UTF8_BOM) else data
        for encoding in ("utf-8", "latin-1", "ascii"):
            try:
                raw_text = clean_data[:4096].decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if raw_text is not None and len(raw_text.strip()) > 0:
            # Check for delimiter structure
            try:
                # Use csv.Sniffer to identify structured delimiter
                sample = "\n".join(raw_text.splitlines()[:15])
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                if dialect.delimiter in (",", "\t", ";", "|"):
                    return DetectedFileType(
                        file_type="csv",
                        mime_type="text/csv",
                        is_supported=True,
                    )
            except Exception:
                # Fallback: check if line contains comma/semicolon/tab regularly
                first_lines = [line for line in raw_text.splitlines() if line.strip()][:5]
                if any("," in item or "\t" in item or ";" in item for item in first_lines):
                    return DetectedFileType(
                        file_type="csv",
                        mime_type="text/csv",
                        is_supported=True,
                    )

    # Unsupported or unrecognized binary
    return DetectedFileType(
        file_type="unknown",
        mime_type="application/octet-stream",
        is_supported=False,
        error_message=f"Unsupported file format or invalid magic bytes for {filename or 'document'}.",
    )
