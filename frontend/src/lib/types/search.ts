export type SearchMode = "keyword" | "semantic" | "hybrid";

export interface SearchResultItem {
  document_id: string;
  filename: string;
  file_type: string;
  status: string;
  needs_review: boolean;
  supplier_name: string | null;
  invoice_number: string | null;
  total: string | number | null;
  currency: string | null;
  invoice_date: string | null;
  score: number;
  match_type: string;
  highlight: string | null;
}

export interface SearchResponse {
  query: string;
  mode: SearchMode;
  total_hits: number;
  results: SearchResultItem[];
}
