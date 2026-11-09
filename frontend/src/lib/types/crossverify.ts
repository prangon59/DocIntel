export type MatchStatus = "MATCHED" | "MISMATCH" | "UNVERIFIED";

export interface FieldComparison {
  field_name: string;
  doc_a_value: string | null;
  doc_b_value: string | null;
  is_match: boolean;
  difference_note?: string;
}

export interface CrossVerifyMismatch {
  invoice_number: string;
  supplier: string;
  source_doc_a: {
    id: string;
    filename: string;
    file_type: string;
  };
  source_doc_b: {
    id: string;
    filename: string;
    file_type: string;
  };
  status: MatchStatus;
  comparisons: FieldComparison[];
  summary: string;
}

export interface CrossVerifyResponse {
  total_compared: number;
  matched_count: number;
  mismatch_count: number;
  results: CrossVerifyMismatch[];
}

export interface CrossVerifyRequest {
  document_ids: string[];
}
