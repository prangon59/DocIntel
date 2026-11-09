"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  getDocument,
  getDocumentResult,
  getCorrectionHistory,
  reprocessDocument,
} from "@/lib/api/endpoints";
import { DocumentViewer } from "@/components/detail/document-viewer";
import { ExtractionForm } from "@/components/detail/extraction-form";
import { ValidationIssues } from "@/components/detail/validation-issues";
import { LineItemsTable } from "@/components/detail/line-items-table";
import { CorrectionHistory } from "@/components/detail/correction-history";
import { StatusBadge } from "@/components/common/status-badge";
import { DetailLoadingSkeleton } from "@/components/common/loading-state";
import { ErrorState } from "@/components/common/error-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/toast";
import {
  ArrowLeft,
  RotateCw,
  AlertTriangle,
  FileText,
  Clock,
  Sparkles,
  History,
} from "lucide-react";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = String(params?.id || "");
  const { toast, success, error } = useToast();

  const [activeTab, setActiveTab] = React.useState<"extraction" | "line_items" | "history">(
    "extraction"
  );

  // 1. Fetch document metadata & pages
  const {
    data: doc,
    isLoading: isDocLoading,
    isError: isDocError,
    refetch: refetchDoc,
  } = useQuery({
    queryKey: ["document", id],
    queryFn: () => getDocument(id),
    enabled: !!id,
  });

  // 2. Fetch structured results & validation issues
  const {
    data: result,
    isLoading: isResultLoading,
    isError: isResultError,
    refetch: refetchResult,
  } = useQuery({
    queryKey: ["document-result", id],
    queryFn: () => getDocumentResult(id),
    enabled: !!id,
  });

  // 3. Fetch correction history audit log
  const {
    data: history,
    refetch: refetchHistory,
  } = useQuery({
    queryKey: ["document-corrections", id],
    queryFn: () => getCorrectionHistory(id),
    enabled: !!id,
  });

  const handleReprocess = async () => {
    try {
      await reprocessDocument(id);
      success("Reprocessing pipeline initiated.", "Pipeline Restarted");
      refetchDoc();
      refetchResult();
    } catch {
      error("Failed to reprocess document.");
    }
  };

  const handleSaved = () => {
    refetchResult();
    refetchHistory();
    refetchDoc();
  };

  if (isDocLoading || isResultLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-1" /> Back
          </Button>
        </div>
        <DetailLoadingSkeleton />
      </div>
    );
  }

  if (isDocError || !doc) {
    return (
      <div className="space-y-4">
        <Link href="/documents">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-1" /> Back to Documents
          </Button>
        </Link>
        <ErrorState
          title="Document Not Found"
          message={`Unable to load details for document ID: ${id}. It may have been deleted or does not exist.`}
          onRetry={() => {
            refetchDoc();
            refetchResult();
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Bar Navigation & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
          <Link href="/documents">
            <Button variant="outline" size="sm" className="h-8 px-2.5 text-xs">
              <ArrowLeft className="w-3.5 h-3.5 mr-1" />
              Documents
            </Button>
          </Link>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold truncate max-w-md">{doc.filename}</h1>
              <StatusBadge status={doc.status} />
              {doc.needs_review && (
                <Badge variant="warning" className="text-[11px] inline-flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-amber-500" />
                  Needs Review
                </Badge>
              )}
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              ID: {doc.id} &bull; Uploaded {new Date(doc.created_at).toLocaleString()}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReprocess}
            className="text-xs h-8 gap-1.5"
          >
            <RotateCw className="w-3.5 h-3.5" />
            Reprocess Pipeline
          </Button>
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: Document Text / OCR Viewer (5 cols) */}
        <div className="lg:col-span-5 h-[760px] sticky top-20">
          <DocumentViewer
            filename={doc.filename}
            fileType={doc.file_type}
            pages={doc.pages || []}
          />
        </div>

        {/* Right Side: Extracted Fields, Validation, Line Items, Audit Trail (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Deterministic Validation Issues Alerts */}
          <ValidationIssues issues={result?.validation_issues || []} />

          {/* Tab Selector */}
          <div className="flex items-center gap-1 border-b border-border pb-1">
            <button
              type="button"
              onClick={() => setActiveTab("extraction")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                activeTab === "extraction"
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Structured Fields
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("line_items")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                activeTab === "line_items"
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Line Items ({result?.extraction?.line_items?.length || 0})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("history")}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors flex items-center gap-1.5 ${
                activeTab === "history"
                  ? "bg-secondary text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <History className="w-3.5 h-3.5" />
              Audit Log ({history?.corrections?.length || 0})
            </button>
          </div>

          {/* Tab Contents */}
          <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
            {activeTab === "extraction" && (
              <ExtractionForm
                documentId={id}
                extraction={result?.extraction || null}
                onSaved={handleSaved}
              />
            )}

            {activeTab === "line_items" && (
              <LineItemsTable
                items={result?.extraction?.line_items || []}
                currency={result?.extraction?.currency}
              />
            )}

            {activeTab === "history" && (
              <CorrectionHistory corrections={history?.corrections || []} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
