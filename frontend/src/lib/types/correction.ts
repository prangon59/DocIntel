export interface CorrectionAuditItem {
  id: string;
  document_id: string;
  field_name: string;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  updated_by: string;
  created_at: string;
}

export interface CorrectionHistoryResponse {
  document_id: string;
  corrections: CorrectionAuditItem[];
}
