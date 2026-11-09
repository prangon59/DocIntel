"""Spreadsheet parsing engine supporting multi-sheet XLSX, legacy XLS, and CSV files.

Handles merged cell value propagation, leading empty row skipping, and header detection.
"""

import csv
import logging
from dataclasses import dataclass
from typing import Any

import openpyxl
import pandas as pd

logger = logging.getLogger("docintel.spreadsheet")


class SpreadsheetProcessingError(Exception):
    """Raised when an Excel or CSV file cannot be parsed."""

    pass


@dataclass
class ParsedSheet:
    """Parsed output of an individual worksheet."""

    sheet_name: str
    sheet_index: int  # 1-indexed
    headers: list[str]
    rows: list[dict[str, Any]]
    raw_text: str
    row_count: int


def _unmerge_and_fill_cells(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    """Propagate top-left value across all cells in each merged range, then unmerge."""
    merged_ranges = list(ws.merged_cells.ranges)
    for cell_range in merged_ranges:
        min_col, min_row, max_col, max_row = cell_range.bounds
        top_left_value = ws.cell(row=min_row, column=min_col).value

        # Unmerge first
        ws.unmerge_cells(str(cell_range))

        # Fill all cells in the previously merged area
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                ws.cell(row=r, column=c, value=top_left_value)


def parse_xlsx(file_path: str) -> list[ParsedSheet]:
    """Parse modern multi-sheet Excel (.xlsx) workbooks with openpyxl."""
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
    except Exception as exc:
        raise SpreadsheetProcessingError(f"Failed to open XLSX workbook: {exc}") from exc

    parsed_sheets: list[ParsedSheet] = []

    for sheet_idx, sheet_name in enumerate(wb.sheetnames, start=1):
        ws = wb[sheet_name]
        _unmerge_and_fill_cells(ws)

        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            continue

        # Skip leading title/banner rows to detect the true header row with distinct column names
        header_row_idx = -1
        headers: list[str] = []
        for idx, row in enumerate(all_rows):
            unique_non_empty = {
                str(c).strip().lower() for c in row if c is not None and str(c).strip() != ""
            }
            if (
                len(unique_non_empty) >= 2
            ):  # Candidate header with at least 2 distinct named columns
                header_row_idx = idx
                headers = [
                    str(c).strip() if c is not None else f"Column_{col_i + 1}"
                    for col_i, c in enumerate(row)
                ]
                break

        if header_row_idx == -1:
            # No structured header found; treat as generic data
            headers = [f"Col_{i + 1}" for i in range(len(all_rows[0]))]
            header_row_idx = -1

        rows_data: list[dict[str, Any]] = []
        text_lines: list[str] = [f"Sheet: {sheet_name}", "Headers: " + " | ".join(headers)]

        data_rows = all_rows[header_row_idx + 1 :] if header_row_idx != -1 else all_rows
        for r_i, row in enumerate(data_rows, start=1):
            if all(c is None or str(c).strip() == "" for c in row):
                continue  # Skip trailing / intermediate blank rows

            row_dict: dict[str, Any] = {}
            line_parts: list[str] = []
            for col_i, val in enumerate(row):
                col_name = headers[col_i] if col_i < len(headers) else f"Column_{col_i + 1}"
                row_dict[col_name] = val
                if val is not None and str(val).strip() != "":
                    line_parts.append(f"{col_name}: {val}")

            rows_data.append(row_dict)
            text_lines.append(f"Row {r_i}: " + "; ".join(line_parts))

        parsed_sheets.append(
            ParsedSheet(
                sheet_name=sheet_name,
                sheet_index=sheet_idx,
                headers=headers,
                rows=rows_data,
                raw_text="\n".join(text_lines),
                row_count=len(rows_data),
            )
        )

    wb.close()
    return parsed_sheets


def parse_csv(file_path: str) -> list[ParsedSheet]:
    """Parse CSV documents using pandas/csv module with automatic dialect detection."""
    try:
        # Detect encoding
        encoding = "utf-8"
        with open(file_path, "rb") as f:
            sample = f.read(4096)
            if sample.startswith(b"\xef\xbb\xbf"):
                encoding = "utf-8-sig"

        # Sniff delimiter
        with open(file_path, encoding=encoding, errors="replace") as f:
            sample_text = "".join(f.readline() for _ in range(15))
            try:
                dialect = csv.Sniffer().sniff(sample_text, delimiters=",\t;|")
                sep = dialect.delimiter
            except Exception:
                sep = ","

        df = pd.read_csv(file_path, encoding=encoding, sep=sep, on_bad_lines="skip")
    except Exception as exc:
        raise SpreadsheetProcessingError(f"Failed to parse CSV file: {exc}") from exc

    # Strip empty rows and whitespace from column names
    df = df.dropna(how="all")
    headers = [str(col).strip() for col in df.columns]

    rows_data: list[dict[str, Any]] = []
    text_lines: list[str] = ["Sheet: CSV Data", "Headers: " + " | ".join(headers)]

    for r_i, (_, row) in enumerate(df.iterrows(), start=1):
        row_dict = row.to_dict()
        rows_data.append(row_dict)
        line_parts = [
            f"{k}: {v}" for k, v in row_dict.items() if pd.notna(v) and str(v).strip() != ""
        ]
        text_lines.append(f"Row {r_i}: " + "; ".join(line_parts))

    return [
        ParsedSheet(
            sheet_name="CSV Data",
            sheet_index=1,
            headers=headers,
            rows=rows_data,
            raw_text="\n".join(text_lines),
            row_count=len(rows_data),
        )
    ]


def parse_xls(file_path: str) -> list[ParsedSheet]:
    """Parse legacy Excel 97-2004 (.xls) files using xlrd."""
    try:
        excel_file = pd.ExcelFile(file_path, engine="xlrd")
    except Exception as exc:
        raise SpreadsheetProcessingError(f"Failed to read legacy XLS file: {exc}") from exc

    parsed_sheets: list[ParsedSheet] = []
    for sheet_idx, sheet_name in enumerate(excel_file.sheet_names, start=1):
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        df = df.dropna(how="all")
        headers = [str(c).strip() for c in df.columns]

        rows_data: list[dict[str, Any]] = []
        text_lines: list[str] = [f"Sheet: {sheet_name}", "Headers: " + " | ".join(headers)]

        for r_i, (_, row) in enumerate(df.iterrows(), start=1):
            row_dict = row.to_dict()
            rows_data.append(row_dict)
            line_parts = [f"{k}: {v}" for k, v in row_dict.items() if pd.notna(v)]
            text_lines.append(f"Row {r_i}: " + "; ".join(line_parts))

        parsed_sheets.append(
            ParsedSheet(
                sheet_name=sheet_name,
                sheet_index=sheet_idx,
                headers=headers,
                rows=rows_data,
                raw_text="\n".join(text_lines),
                row_count=len(rows_data),
            )
        )

    return parsed_sheets


def parse_spreadsheet(file_path: str, file_type: str) -> list[ParsedSheet]:
    """Master spreadsheet parser dispatching by verified file type."""
    normalized_type = file_type.lower()
    if normalized_type == "xlsx":
        return parse_xlsx(file_path)
    elif normalized_type == "csv":
        return parse_csv(file_path)
    elif normalized_type == "xls":
        return parse_xls(file_path)
    else:
        raise SpreadsheetProcessingError(f"Unsupported spreadsheet format: {file_type}")
