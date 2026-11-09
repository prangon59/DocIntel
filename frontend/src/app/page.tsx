"use client";

import * as React from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getMetrics, listDocuments } from "@/lib/api/endpoints";
import { MetricsGrid } from "@/components/dashboard/metrics-grid";
import { RecentDocuments } from "@/components/dashboard/recent-documents";
import { DragDropUploader } from "@/components/upload/drag-drop-uploader";
import { CardLoadingSkeleton, TableLoadingSkeleton } from "@/components/common/loading-state";
import { ErrorState } from "@/components/common/error-state";
import {
  FileText,
  Search,
  GitCompare,
  UploadCloud,
  CheckCircle2,
  Cpu,
  Layers,
  ShieldCheck,
} from "lucide-react";

export default function DashboardPage() {
  const {
    data: metrics,
    isLoading: isMetricsLoading,
    isError: isMetricsError,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ["metrics"],
    queryFn: getMetrics,
  });

  const {
    data: docsData,
    isLoading: isDocsLoading,
    refetch: refetchDocs,
  } = useQuery({
    queryKey: ["recent-documents"],
    queryFn: () => listDocuments({ limit: 5 }),
  });

  const handleUploadSuccess = () => {
    refetchMetrics();
    refetchDocs();
  };

  return (
    <div className="space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-border">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 text-xs font-semibold text-primary bg-primary/10 border border-primary/20 px-2.5 py-0.5 rounded-full mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            AI Document Intelligence Engine
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Document Ingestion & Financial Extraction
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Automated multi-format document processing, OCR fallback, Gemini structured invoice extraction, deterministic financial validation, and cross-verification.
          </p>
        </div>

        {/* Quick links */}
        <div className="flex items-center gap-2">
          <Link
            href="/search"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors shadow-sm"
          >
            <Search className="w-3.5 h-3.5 text-primary" />
            Search Invoices
          </Link>
          <Link
            href="/crossverify"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-border bg-card hover:bg-muted/50 transition-colors shadow-sm"
          >
            <GitCompare className="w-3.5 h-3.5 text-primary" />
            Cross-Verify
          </Link>
        </div>
      </div>

      {/* KPI Metrics */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
          System Performance & Extraction Metrics
        </h2>
        {isMetricsLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <CardLoadingSkeleton key={i} />
            ))}
          </div>
        ) : isMetricsError || !metrics ? (
          <ErrorState
            title="Failed to load metrics"
            message="Could not fetch system metrics from backend API. Retry to check connection."
            onRetry={refetchMetrics}
          />
        ) : (
          <MetricsGrid metrics={metrics} />
        )}
      </section>

      {/* Main Grid: Upload & Recent Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Drag-and-Drop Ingestion */}
        <section className="lg:col-span-7 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
              Multi-Format Document Upload
            </h2>
            <span className="text-[11px] text-muted-foreground font-mono">
              Max 100MB &bull; Non-blocking Batch
            </span>
          </div>
          <DragDropUploader onUploadSuccess={handleUploadSuccess} />
        </section>

        {/* Right: Recent Ingestions */}
        <section className="lg:col-span-5 space-y-3">
          <h2 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
            Live Document Stream
          </h2>
          {isDocsLoading ? (
            <TableLoadingSkeleton rows={5} />
          ) : (
            <RecentDocuments documents={docsData?.items || []} />
          )}
        </section>
      </div>

      {/* System Architecture Feature Cards */}
      <section className="pt-4 border-t border-border/60">
        <h2 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground mb-4">
          Core Processing Pipeline Capabilities
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-border bg-card/60 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
              <Layers className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm">Large PDF Chunking</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Splits PDFs up to 1,000 pages into parallel Celery tasks with per-page progress aggregation and segment grouping.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card/60 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <Cpu className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm">Adaptive OCR Fallback</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Tesseract + OpenCV preprocessing automatically triggers on scanned pages with &lt;30 digital text characters.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card/60 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm">Gemini 2.5 Flash + Grounding</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Strict JSON schema extraction with source snippet verification. Missing fields resolve strictly to null.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-border bg-card/60 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <h3 className="font-semibold text-sm">Deterministic Validation</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Mathematical consistency checks, duplicate detection, and cross-document reconciliation done by code, never LLM.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
