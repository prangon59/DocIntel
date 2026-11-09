export type IssueSeverity = "error" | "warning" | "info";

export interface ValidationIssue {
  id: string;
  code: string;
  severity: IssueSeverity;
  field: string | null;
  message: string;
  details?: Record<string, unknown> | null;
}

export interface ExtractedLineItem {
  id: string;
  description: string;
  quantity: string | null;
  unit_price: string | null;
  line_total: string | null;
  confidence?: number | null;
}

export interface InvoiceExtraction {
  id: string;
  invoice_number: string | null;
  invoice_date: string | null;
  supplier_name: string | null;
  customer_name: string | null;
  subtotal: string | null;
  tax: string | null;
  total: string | null;
  currency: string | null;
  confidence: number;
  confidence_scores?: Record<string, number>;
  line_items: ExtractedLineItem[];
}

export interface DocumentResultResponse {
  document_id: string;
  filename: string;
  status: string;
  needs_review: boolean;
  extraction: InvoiceExtraction | null;
  extractions?: InvoiceExtraction[];
  validation_issues: ValidationIssue[];
}

export interface UpdateExtractionPayload {
  invoice_number?: string | null;
  invoice_date?: string | null;
  supplier_name?: string | null;
  customer_name?: string | null;
  subtotal?: string | null;
  tax?: string | null;
  total?: string | null;
  currency?: string | null;
  reason?: string;
  updated_by?: string;
}
