export type DocumentStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface PageRead {
  page_number: number;
  raw_text: string;
  extraction_method: string;
  ocr_confidence?: number | null;
  char_count: number;
}

export interface DocumentRead {
  id: string;
  filename: string;
  file_type: string;
  mime_type: string;
  file_size: number;
  file_hash: string;
  status: DocumentStatus;
  page_count: number;
  needs_review: boolean;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentDetailResponse extends DocumentRead {
  pages: PageRead[];
}

export interface DocumentUploadItem {
  id: string;
  filename: string;
  status: string;
  job_id: string;
}

export interface DocumentUploadResponse {
  uploaded: DocumentUploadItem[];
  total_files: number;
  message: string;
}

export interface DocumentStatusResponse {
  document_id: string;
  status: DocumentStatus;
  stage: string;
  pages_done: number;
  pages_total: number;
  percentage: number;
  error_message?: string | null;
}

export interface DocumentListResponse {
  items: DocumentRead[];
  total: number;
  skip: number;
  limit: number;
}

export interface DocumentFilterParams {
  status?: DocumentStatus | "ALL";
  file_type?: string;
  needs_review?: boolean;
  skip?: number;
  limit?: number;
  search?: string;
}
