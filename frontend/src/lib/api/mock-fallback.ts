/**
 * Mock fallback generator complying with docs/SPEC.md.
 * Used when backend endpoints (search, corrections, cross-verify, metrics)
 * are still being built by the Phase 3 worker or during offline dev.
 */

import {
  DocumentRead,
  DocumentDetailResponse,
  DocumentResultResponse,
  DocumentStatusResponse,
  CorrectionHistoryResponse,
  CorrectionAuditItem,
  SearchResponse,
  CrossVerifyResponse,
  MetricsResponse,
  SearchMode,
  UpdateExtractionPayload,
} from "@/lib/types";

// In-memory mock store to persist edits within a session
const mockCorrectionsStore: Record<string, CorrectionAuditItem[]> = {};
const mockExtractionsStore: Record<string, DocumentResultResponse> = {};

export const MOCK_DOCUMENTS: DocumentRead[] = [
  {
    id: "9f3a1e2b-4c5d-4e6f-8a0b-1c2d3e4f5a6b",
    filename: "INV-2024-001_Acme_Supplies.pdf",
    file_type: "pdf",
    mime_type: "application/pdf",
    file_size: 148200,
    file_hash: "a1b2c3d4e5f67890",
    status: "COMPLETED",
    page_count: 2,
    needs_review: false,
    error_message: null,
    created_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 1.8).toISOString(),
  },
  {
    id: "8e2b1a3c-5d6e-4f7a-9b1c-2d3e4f5a6b7c",
    filename: "Vendor_Ledger_Q1_2024.xlsx",
    file_type: "xlsx",
    mime_type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    file_size: 512000,
    file_hash: "b2c3d4e5f6789012",
    status: "COMPLETED",
    page_count: 1,
    needs_review: false,
    error_message: null,
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 4.9).toISOString(),
  },
  {
    id: "7d1c2b3a-6e7f-4a8b-0c2d-3e4f5a6b7c8d",
    filename: "Scanned_Receipt_4892.png",
    file_type: "png",
    mime_type: "image/png",
    file_size: 894000,
    file_hash: "c3d4e5f678901234",
    status: "COMPLETED",
    page_count: 1,
    needs_review: true,
    error_message: null,
    created_at: new Date(Date.now() - 3600000 * 10).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 9.8).toISOString(),
  },
  {
    id: "6c0b1a2d-7e8f-4b9c-1d3e-4f5a6b7c8d9e",
    filename: "Invoice_Discrepancy_Test.pdf",
    file_type: "pdf",
    mime_type: "application/pdf",
    file_size: 215000,
    file_hash: "d4e5f67890123456",
    status: "COMPLETED",
    page_count: 3,
    needs_review: true,
    error_message: null,
    created_at: new Date(Date.now() - 3600000 * 14).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 13.7).toISOString(),
  },
  {
    id: "5b9a0c1d-8e9f-4c0d-2e4f-5a6b7c8d9e0f",
    filename: "Corrupted_Batch_File.tiff",
    file_type: "tiff",
    mime_type: "image/tiff",
    file_size: 32000,
    file_hash: "e5f6789012345678",
    status: "FAILED",
    page_count: 0,
    needs_review: false,
    error_message: "Header corrupt: Image decode failed at byte 1024",
    created_at: new Date(Date.now() - 3600000 * 20).toISOString(),
    updated_at: new Date(Date.now() - 3600000 * 20).toISOString(),
  },
  {
    id: "4a8b9c0d-9f0a-4d1e-3f5a-6b7c8d9e0f1a",
    filename: "Large_Catalog_Invoice_300p.pdf",
    file_type: "pdf",
    mime_type: "application/pdf",
    file_size: 8940000,
    file_hash: "f67890123456789a",
    status: "PROCESSING",
    page_count: 300,
    needs_review: false,
    error_message: null,
    created_at: new Date(Date.now() - 30000).toISOString(),
    updated_at: new Date(Date.now() - 10000).toISOString(),
  },
];

export function getMockDocumentDetail(id: string): DocumentDetailResponse {
  const doc = MOCK_DOCUMENTS.find((d) => d.id === id) || MOCK_DOCUMENTS[0];
  return {
    ...doc,
    pages: [
      {
        page_number: 1,
        raw_text: `INVOICE
Invoice Number: ${doc.id.startsWith("9f") ? "INV-2024-001" : "INV-8492"}
Date: 2024-03-15
Supplier: Acme Industrial Supplies Ltd.
123 Enterprise Way, Industrial Park, CA 94016
Customer: Global Manufacturing Corp.
500 Tech Boulevard, Austin, TX 78701

Item Description                     Qty   Unit Price    Line Total
Industrial Hydraulic Pump #4A         2     $1,250.00     $2,500.00
High-Pressure Seal Kit               10       $45.00       $450.00
Synthetic Lubricant 55 Gal            1       $350.00       $350.00

Subtotal: $3,300.00
Tax (8.25%): $272.25
Total Due: $3,572.25
Currency: USD`,
        extraction_method: "digital_pdf",
        ocr_confidence: 0.99,
        char_count: 485,
      },
      {
        page_number: 2,
        raw_text: `TERMS AND CONDITIONS
Payment due within 30 days of receipt.
Direct wire transfer details: Bank of America, Routing #121000358, Acct #987654321.
Remit inquiries to billing@acmesupplies.com. Thank you for your business!`,
        extraction_method: "digital_pdf",
        ocr_confidence: 0.98,
        char_count: 220,
      },
    ],
  };
}

export function getMockDocumentResult(id: string): DocumentResultResponse {
  if (mockExtractionsStore[id]) {
    return mockExtractionsStore[id];
  }

  const isDiscrepancy = id.includes("6c0b") || id.includes("Discrepancy");
  const isNeedsReview = id.includes("7d1c") || id.includes("Receipt");

  const result: DocumentResultResponse = {
    document_id: id,
    filename: isDiscrepancy
      ? "Invoice_Discrepancy_Test.pdf"
      : isNeedsReview
      ? "Scanned_Receipt_4892.png"
      : "INV-2024-001_Acme_Supplies.pdf",
    status: "COMPLETED",
    needs_review: isDiscrepancy || isNeedsReview,
    extraction: {
      id: `ext-${id.slice(0, 8)}`,
      invoice_number: isDiscrepancy ? "INV-DISC-99" : "INV-2024-001",
      invoice_date: "2024-03-15",
      supplier_name: "Acme Industrial Supplies Ltd.",
      customer_name: "Global Manufacturing Corp.",
      subtotal: isDiscrepancy ? "3300.00" : "3300.00",
      tax: isDiscrepancy ? "272.25" : "272.25",
      total: isDiscrepancy ? "4000.00" : "3572.25", // deliberate math mismatch on discrepancy
      currency: "USD",
      confidence: isNeedsReview ? 0.62 : 0.94,
      confidence_scores: {
        invoice_number: 0.98,
        invoice_date: 0.95,
        supplier_name: 0.92,
        customer_name: 0.91,
        subtotal: 0.94,
        tax: 0.88,
        total: isDiscrepancy ? 0.70 : 0.96,
        currency: 0.99,
      },
      line_items: [
        {
          id: `li-1-${id.slice(0, 4)}`,
          description: "Industrial Hydraulic Pump #4A",
          quantity: "2",
          unit_price: "1250.00",
          line_total: "2500.00",
          confidence: 0.96,
        },
        {
          id: `li-2-${id.slice(0, 4)}`,
          description: "High-Pressure Seal Kit",
          quantity: "10",
          unit_price: "45.00",
          line_total: "450.00",
          confidence: 0.92,
        },
        {
          id: `li-3-${id.slice(0, 4)}`,
          description: "Synthetic Lubricant 55 Gal",
          quantity: "1",
          unit_price: "350.00",
          line_total: "350.00",
          confidence: 0.89,
        },
      ],
    },
    validation_issues: isDiscrepancy
      ? [
          {
            id: "val-1",
            code: "MATH_MISMATCH_TOTAL",
            severity: "error",
            field: "total",
            message:
              "Subtotal (3300.00) + Tax (272.25) does not equal stated Total (4000.00). Difference: 427.75",
            details: { expected: 3572.25, found: 4000.0, diff: 427.75 },
          },
        ]
      : isNeedsReview
      ? [
          {
            id: "val-2",
            code: "LOW_CONFIDENCE_OCR",
            severity: "warning",
            field: "invoice_number",
            message:
              "Scanned image has degraded text clarity. Confidence score 62% is below recommended threshold (85%).",
          },
        ]
      : [],
  };

  mockExtractionsStore[id] = result;
  return result;
}

export function updateMockDocumentResult(
  id: string,
  payload: UpdateExtractionPayload
): DocumentResultResponse {
  const current = getMockDocumentResult(id);
  const updatedExtraction = { ...current.extraction! };

  // Track audit log
  const newAuditItems: CorrectionAuditItem[] = [];
  const fields: (keyof UpdateExtractionPayload)[] = [
    "invoice_number",
    "invoice_date",
    "supplier_name",
    "customer_name",
    "subtotal",
    "tax",
    "total",
    "currency",
  ];

  for (const f of fields) {
    if (payload[f] !== undefined && payload[f] !== null) {
      const oldVal = (updatedExtraction as Record<string, unknown>)[f] as string | null;
      const newVal = payload[f] as string;
      if (oldVal !== newVal) {
        (updatedExtraction as Record<string, unknown>)[f] = newVal;
        newAuditItems.push({
          id: `corr-${Math.random().toString(36).substring(2, 9)}`,
          document_id: id,
          field_name: f,
          old_value: oldVal,
          new_value: newVal,
          reason: payload.reason || "Manual user correction",
          updated_by: payload.updated_by || "frontend_user",
          created_at: new Date().toISOString(),
        });
      }
    }
  }

  if (!mockCorrectionsStore[id]) {
    mockCorrectionsStore[id] = [];
  }
  mockCorrectionsStore[id].unshift(...newAuditItems);

  // Recalculate deterministic validation
  const subtotal = parseFloat(updatedExtraction.subtotal || "0");
  const tax = parseFloat(updatedExtraction.tax || "0");
  const total = parseFloat(updatedExtraction.total || "0");
  const sumDiff = Math.abs(subtotal + tax - total);

  const newIssues = [];
  if (sumDiff > 0.02) {
    newIssues.push({
      id: "val-math-recalc",
      code: "MATH_MISMATCH_TOTAL",
      severity: "error" as const,
      field: "total",
      message: `Subtotal (${subtotal.toFixed(2)}) + Tax (${tax.toFixed(2)}) does not equal Total (${total.toFixed(2)}). Difference: ${sumDiff.toFixed(2)}`,
    });
  }

  const updated: DocumentResultResponse = {
    ...current,
    extraction: updatedExtraction,
    validation_issues: newIssues,
    needs_review: newIssues.length > 0,
  };

  mockExtractionsStore[id] = updated;
  return updated;
}

export function getMockCorrections(id: string): CorrectionHistoryResponse {
  return {
    document_id: id,
    corrections: mockCorrectionsStore[id] || [
      {
        id: "corr-init-1",
        document_id: id,
        field_name: "supplier_name",
        old_value: "Acme Industrial Supplies",
        new_value: "Acme Industrial Supplies Ltd.",
        reason: "Matched corporate registry standard",
        updated_by: "system_normalizer",
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
    ],
  };
}

export function getMockSearch(
  query: string,
  mode: SearchMode = "hybrid"
): SearchResponse {
  const q = (query || "").toLowerCase().trim();

  const allItems = [
    {
      document_id: "9f3a1e2b-4c5d-4e6f-8a0b-1c2d3e4f5a6b",
      filename: "INV-2024-001_Acme_Supplies.pdf",
      file_type: "pdf",
      status: "COMPLETED",
      needs_review: false,
      supplier_name: "Acme Industrial Supplies Ltd.",
      invoice_number: "INV-2024-001",
      total: "3572.25",
      currency: "USD",
      invoice_date: "2024-03-15",
      score: 0.95,
      match_type: mode,
      highlight:
        "Industrial Hydraulic Pump #4A ... Subtotal: <mark class='bg-primary/20 text-primary font-semibold px-1 rounded'>$3,300.00</mark> Total Due: $3,572.25",
    },
    {
      document_id: "8e2b1a3c-5d6e-4f7a-9b1c-2d3e4f5a6b7c",
      filename: "Vendor_Ledger_Q1_2024.xlsx",
      file_type: "xlsx",
      status: "COMPLETED",
      needs_review: false,
      supplier_name: "Apex Logistics Corp",
      invoice_number: "APX-88210",
      total: "12840.00",
      currency: "USD",
      invoice_date: "2024-02-28",
      score: 0.88,
      match_type: mode,
      highlight:
        "Quarterly freight transport services for North America distribution hub ... Total: <mark class='bg-primary/20 text-primary font-semibold px-1 rounded'>$12,840.00</mark>",
    },
    {
      document_id: "7d1c2b3a-6e7f-4a8b-0c2d-3e4f5a6b7c8d",
      filename: "Scanned_Receipt_4892.png",
      file_type: "png",
      status: "COMPLETED",
      needs_review: true,
      supplier_name: "Metro Office Depot",
      invoice_number: "REC-4892",
      total: "148.50",
      currency: "USD",
      invoice_date: "2024-03-10",
      score: 0.74,
      match_type: mode,
      highlight:
        "Ergonomic mesh chairs, copy paper boxes ... Total: <mark class='bg-primary/20 text-primary font-semibold px-1 rounded'>$148.50</mark>",
    },
    {
      document_id: "6c0b1a2d-7e8f-4b9c-1d3e-4f5a6b7c8d9e",
      filename: "Invoice_Discrepancy_Test.pdf",
      file_type: "pdf",
      status: "COMPLETED",
      needs_review: true,
      supplier_name: "Acme Industrial Supplies Ltd.",
      invoice_number: "INV-DISC-99",
      total: "4000.00",
      currency: "USD",
      invoice_date: "2024-03-15",
      score: 0.82,
      match_type: mode,
      highlight:
        "Discrepancy test run: <mark class='bg-primary/20 text-primary font-semibold px-1 rounded'>INV-DISC-99</mark> subtotal + tax mismatch",
    },
  ];

  if (!q) {
    return {
      query: "",
      mode,
      total_hits: allItems.length,
      results: allItems,
    };
  }

  const filtered = allItems.filter(
    (item) =>
      item.filename.toLowerCase().includes(q) ||
      (item.supplier_name && item.supplier_name.toLowerCase().includes(q)) ||
      (item.invoice_number && item.invoice_number.toLowerCase().includes(q)) ||
      (item.highlight && item.highlight.toLowerCase().includes(q))
  );

  return {
    query,
    mode,
    total_hits: filtered.length,
    results: filtered,
  };
}

export function getMockCrossVerify(documentIds: string[]): CrossVerifyResponse {
  return {
    total_compared: 2,
    matched_count: 1,
    mismatch_count: 1,
    results: [
      {
        invoice_number: "INV-2024-001",
        supplier: "Acme Industrial Supplies Ltd.",
        source_doc_a: {
          id: documentIds[0] || "9f3a1e2b-4c5d-4e6f-8a0b-1c2d3e4f5a6b",
          filename: "INV-2024-001_Acme_Supplies.pdf",
          file_type: "pdf",
        },
        source_doc_b: {
          id: documentIds[1] || "8e2b1a3c-5d6e-4f7a-9b1c-2d3e4f5a6b7c",
          filename: "Vendor_Ledger_Q1_2024.xlsx",
          file_type: "xlsx",
        },
        status: "MATCHED",
        comparisons: [
          {
            field_name: "Invoice Number",
            doc_a_value: "INV-2024-001",
            doc_b_value: "INV-2024-001",
            is_match: true,
          },
          {
            field_name: "Supplier Name",
            doc_a_value: "Acme Industrial Supplies Ltd.",
            doc_b_value: "Acme Industrial Supplies Ltd.",
            is_match: true,
          },
          {
            field_name: "Invoice Date",
            doc_a_value: "2024-03-15",
            doc_b_value: "2024-03-15",
            is_match: true,
          },
          {
            field_name: "Total Amount",
            doc_a_value: "$3,572.25",
            doc_b_value: "$3,572.25",
            is_match: true,
          },
        ],
        summary: "100% agreement between PDF invoice and Excel accounts payable ledger.",
      },
      {
        invoice_number: "INV-DISC-99",
        supplier: "Acme Industrial Supplies Ltd.",
        source_doc_a: {
          id: "6c0b1a2d-7e8f-4b9c-1d3e-4f5a6b7c8d9e",
          filename: "Invoice_Discrepancy_Test.pdf",
          file_type: "pdf",
        },
        source_doc_b: {
          id: "8e2b1a3c-5d6e-4f7a-9b1c-2d3e4f5a6b7c",
          filename: "Vendor_Ledger_Q1_2024.xlsx",
          file_type: "xlsx",
        },
        status: "MISMATCH",
        comparisons: [
          {
            field_name: "Invoice Number",
            doc_a_value: "INV-DISC-99",
            doc_b_value: "INV-DISC-99",
            is_match: true,
          },
          {
            field_name: "Supplier Name",
            doc_a_value: "Acme Industrial Supplies Ltd.",
            doc_b_value: "Acme Industrial Supplies Ltd.",
            is_match: true,
          },
          {
            field_name: "Total Amount",
            doc_a_value: "$4,000.00",
            doc_b_value: "$3,572.25",
            is_match: false,
            difference_note: "Delta: +$427.75 in PDF compared to spreadsheet record",
          },
        ],
        summary: "Total amount discrepancy identified between PDF ($4,000.00) and Excel ledger ($3,572.25).",
      },
    ],
  };
}

export function getMockMetrics(): MetricsResponse {
  return {
    total_documents: 142,
    completed_count: 136,
    failed_count: 4,
    processing_count: 2,
    pending_count: 0,
    needs_review_count: 8,
    success_rate: 95.8,
    failure_rate: 2.8,
    avg_processing_time_seconds: 2.6,
    avg_confidence_score: 0.94,
    documents_by_type: {
      pdf: 98,
      xlsx: 24,
      csv: 12,
      png: 5,
      jpg: 3,
    },
    daily_volume: [
      { date: "2024-03-09", count: 18 },
      { date: "2024-03-10", count: 22 },
      { date: "2024-03-11", count: 35 },
      { date: "2024-03-12", count: 28 },
      { date: "2024-03-13", count: 19 },
      { date: "2024-03-14", count: 12 },
      { date: "2024-03-15", count: 8 },
    ],
  };
}
