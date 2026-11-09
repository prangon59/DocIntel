/**
 * Unified API endpoints layer with automatic mock fallback.
 */

import { apiFetch, ApiError } from "./client";
import {
  MOCK_DOCUMENTS,
  getMockDocumentDetail,
  getMockDocumentResult,
  updateMockDocumentResult,
  getMockCorrections,
  getMockSearch,
  getMockCrossVerify,
  getMockMetrics,
} from "./mock-fallback";
import {
  DocumentFilterParams,
  DocumentListResponse,
  DocumentDetailResponse,
  DocumentStatusResponse,
  DocumentUploadResponse,
  DocumentResultResponse,
  UpdateExtractionPayload,
  CorrectionHistoryResponse,
  SearchMode,
  SearchResponse,
  CrossVerifyResponse,
  MetricsResponse,
} from "@/lib/types";

// Track mock state for UI indication
let isMockActive = false;
export const getIsMockActive = () => isMockActive;

// --- Documents API ---

export async function listDocuments(
  params: DocumentFilterParams = {}
): Promise<DocumentListResponse> {
  try {
    const qParams: Record<string, string | number | boolean | undefined> = {};
    if (params.status && params.status !== "ALL") qParams.status = params.status;
    if (params.file_type) qParams.file_type = params.file_type;
    if (params.needs_review !== undefined) qParams.needs_review = params.needs_review;
    if (params.skip !== undefined) qParams.skip = params.skip;
    if (params.limit !== undefined) qParams.limit = params.limit;

    const res = await apiFetch<DocumentListResponse>("/api/v1/documents", {
      params: qParams,
    });
    isMockActive = false;
    return res;
  } catch (err) {
    // If backend is not available, fallback to mock data
    isMockActive = true;
    let items = [...MOCK_DOCUMENTS];
    if (params.status && params.status !== "ALL") {
      items = items.filter((d) => d.status === params.status);
    }
    if (params.needs_review !== undefined) {
      items = items.filter((d) => d.needs_review === params.needs_review);
    }
    if (params.file_type) {
      items = items.filter((d) => d.file_type.toLowerCase() === params.file_type?.toLowerCase());
    }
    if (params.search) {
      const q = params.search.toLowerCase();
      items = items.filter((d) => d.filename.toLowerCase().includes(q));
    }
    return {
      items,
      total: items.length,
      skip: params.skip || 0,
      limit: params.limit || 50,
    };
  }
}

export async function getDocument(id: string): Promise<DocumentDetailResponse> {
  try {
    const res = await apiFetch<DocumentDetailResponse>(`/api/v1/documents/${id}`);
    isMockActive = false;
    return res;
  } catch (err) {
    isMockActive = true;
    return getMockDocumentDetail(id);
  }
}

export async function getDocumentStatus(id: string): Promise<DocumentStatusResponse> {
  try {
    const res = await apiFetch<DocumentStatusResponse>(`/api/v1/documents/${id}/status`);
    return res;
  } catch (err) {
    return {
      document_id: id,
      status: "COMPLETED",
      stage: "EXTRACTION",
      pages_done: 1,
      pages_total: 1,
      percentage: 100,
    };
  }
}

export async function getDocumentResult(id: string): Promise<DocumentResultResponse> {
  try {
    const res = await apiFetch<DocumentResultResponse>(`/api/v1/documents/${id}/result`);
    isMockActive = false;
    return res;
  } catch (err) {
    isMockActive = true;
    return getMockDocumentResult(id);
  }
}

export async function uploadDocuments(files: File[]): Promise<DocumentUploadResponse> {
  try {
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));

    const res = await apiFetch<DocumentUploadResponse>("/api/v1/documents/upload", {
      method: "POST",
      body: formData,
    });
    isMockActive = false;
    return res;
  } catch (err) {
    // Return graceful mock upload response if backend is offline
    isMockActive = true;
    return {
      total_files: files.length,
      message: `Mock queued ${files.length} file(s) for ingestion.`,
      uploaded: files.map((f) => ({
        id: `mock-${Math.random().toString(36).substring(2, 9)}`,
        filename: f.name,
        status: "COMPLETED",
        job_id: `job-mock-${Math.random().toString(36).substring(2, 7)}`,
      })),
    };
  }
}

export async function updateDocumentResult(
  id: string,
  payload: UpdateExtractionPayload
): Promise<DocumentResultResponse> {
  try {
    const res = await apiFetch<DocumentResultResponse>(`/api/v1/documents/${id}/result`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    isMockActive = false;
    return res;
  } catch (err) {
    // Fallback to mock update engine
    isMockActive = true;
    return updateMockDocumentResult(id, payload);
  }
}

export async function getCorrectionHistory(id: string): Promise<CorrectionHistoryResponse> {
  try {
    const res = await apiFetch<CorrectionHistoryResponse>(`/api/v1/documents/${id}/corrections`);
    isMockActive = false;
    return res;
  } catch (err) {
    isMockActive = true;
    return getMockCorrections(id);
  }
}

export async function reprocessDocument(id: string): Promise<{ status: string; message: string }> {
  try {
    const res = await apiFetch<{ status: string; message: string }>(
      `/api/v1/documents/${id}/reprocess`,
      { method: "POST" }
    );
    isMockActive = false;
    return res;
  } catch (err) {
    isMockActive = true;
    return { status: "PROCESSING", message: "Document queued for reprocessing." };
  }
}

// --- Search API ---

export async function searchDocuments(
  query: string,
  mode: SearchMode = "hybrid"
): Promise<SearchResponse> {
  try {
    const res = await apiFetch<SearchResponse>("/api/v1/search", {
      params: { q: query, mode },
    });
    isMockActive = false;
    return res;
  } catch (err) {
    isMockActive = true;
    return getMockSearch(query, mode);
  }
}

// --- Cross-Verify API ---

export async function crossVerifyDocuments(documentIds: string[]): Promise<CrossVerifyResponse> {
  try {
    const res = await apiFetch<CrossVerifyResponse>("/api/v1/crossverify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_ids: documentIds }),
    });
    isMockActive = false;
    return res;
  } catch (err) {
    isMockActive = true;
    return getMockCrossVerify(documentIds);
  }
}

// --- Metrics API ---

export async function getMetrics(): Promise<MetricsResponse> {
  try {
    const res = await apiFetch<MetricsResponse>("/api/v1/metrics");
    isMockActive = false;
    return res;
  } catch (err) {
    isMockActive = true;
    return getMockMetrics();
  }
}
