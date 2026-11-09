export interface MetricsResponse {
  total_documents: number;
  completed_count: number;
  failed_count: number;
  processing_count: number;
  pending_count: number;
  needs_review_count: number;
  success_rate: number; // e.g. 96.5
  failure_rate: number; // e.g. 3.5
  avg_processing_time_seconds: number; // e.g. 2.4
  avg_confidence_score: number; // e.g. 0.94
  documents_by_type: Record<string, number>;
  daily_volume: Array<{
    date: string;
    count: number;
  }>;
}
