"use client";

import * as React from "react";
import Link from "next/link";
import { GitCompare, CheckCircle2, AlertTriangle, ArrowRight, RefreshCw, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { TableLoadingSkeleton } from "@/components/common/loading-state";
import { EmptyState } from "@/components/common/empty-state";
import { crossVerifyDocuments } from "@/lib/api/endpoints";
import { CrossVerifyResponse, CrossVerifyMismatch } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export function CrossVerifyView() {
  const { data, isLoading, isError, refetch } = useQuery<CrossVerifyResponse>({
    queryKey: ["crossverify"],
    queryFn: () =>
      crossVerifyDocuments([
        "9f3a1e2b-4c5d-4e6f-8a0b-1c2d3e4f5a6b",
        "8e2b1a3c-5d6e-4f7a-9b1c-2d3e4f5a6b7c",
      ]),
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold tracking-tight">Cross-Document Verification</h1>
          <p className="text-sm text-muted-foreground">
            Automated reconciliation across multi-format documents (PDF ↔ PDF, PDF ↔ Excel). Identifies invoice number matches, line-item differences, and financial totals deltas.
          </p>
        </div>

        <Button
          onClick={() => refetch()}
          size="sm"
          className="gap-1.5 self-start sm:self-auto text-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Re-run Reconciliation
        </Button>
      </div>

      {/* Summary KPI Badges */}
      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-border bg-card shadow-sm flex items-center justify-between">
            <span className="text-xs text-muted-foreground font-medium">Pairs Analyzed</span>
            <span className="text-xl font-bold font-mono">{data.total_compared}</span>
          </div>
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 shadow-sm flex items-center justify-between">
            <span className="text-xs text-emerald-400 font-medium flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              100% Agreement
            </span>
            <span className="text-xl font-bold font-mono text-emerald-400">
              {data.matched_count}
            </span>
          </div>
          <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/5 shadow-sm flex items-center justify-between">
            <span className="text-xs text-destructive font-medium flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-destructive" />
              Discrepancies
            </span>
            <span className="text-xl font-bold font-mono text-destructive">
              {data.mismatch_count}
            </span>
          </div>
        </div>
      )}

      {/* Results List */}
      {isLoading ? (
        <TableLoadingSkeleton rows={3} />
      ) : isError ? (
        <div className="p-8 text-center border border-destructive/30 rounded-xl bg-destructive/10 text-destructive text-sm">
          Failed to load cross-document verification results.
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          title="No reconciliation discrepancies"
          description="Uploaded documents have not yet been paired or verified against spreadsheets."
        />
      ) : (
        <div className="space-y-6">
          {data.results.map((mismatch: CrossVerifyMismatch, idx: number) => {
            const isMatch = mismatch.status === "MATCHED";

            return (
              <div
                key={idx}
                className={`rounded-xl border bg-card shadow-sm overflow-hidden transition-all ${
                  isMatch ? "border-emerald-500/40" : "border-destructive/40"
                }`}
              >
                {/* Header */}
                <div className="p-4 bg-muted/30 border-b border-border/60 flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <Badge variant={isMatch ? "success" : "destructive"} className="text-xs">
                      {mismatch.status}
                    </Badge>
                    <div>
                      <h3 className="font-semibold text-sm">
                        Invoice #{mismatch.invoice_number} &bull; {mismatch.supplier}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">{mismatch.summary}</p>
                    </div>
                  </div>

                  {/* Documents compared */}
                  <div className="flex items-center gap-2 text-xs font-mono bg-background/80 px-3 py-1.5 rounded-lg border border-border/60">
                    <Link
                      href={`/documents/${mismatch.source_doc_a.id}`}
                      className="text-primary hover:underline flex items-center gap-1"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      {mismatch.source_doc_a.filename}
                    </Link>
                    <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
                    <Link
                      href={`/documents/${mismatch.source_doc_b.id}`}
                      className="text-primary hover:underline flex items-center gap-1"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      {mismatch.source_doc_b.filename}
                    </Link>
                  </div>
                </div>

                {/* Field Comparison Table */}
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/10 text-xs">
                      <TableHead className="w-[200px]">Field</TableHead>
                      <TableHead>Doc A: {mismatch.source_doc_a.filename}</TableHead>
                      <TableHead>Doc B: {mismatch.source_doc_b.filename}</TableHead>
                      <TableHead className="w-[150px]">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mismatch.comparisons.map((c, cIdx) => (
                      <TableRow key={cIdx} className="text-xs">
                        <TableCell className="font-semibold text-foreground">
                          {c.field_name}
                        </TableCell>
                        <TableCell className="font-mono">{c.doc_a_value || "—"}</TableCell>
                        <TableCell className="font-mono">{c.doc_b_value || "—"}</TableCell>
                        <TableCell>
                          {c.is_match ? (
                            <Badge variant="success" className="text-[10px]">
                              Match
                            </Badge>
                          ) : (
                            <div className="space-y-0.5">
                              <Badge variant="destructive" className="text-[10px]">
                                Mismatch
                              </Badge>
                              {c.difference_note && (
                                <p className="text-[10px] text-destructive leading-tight font-sans">
                                  {c.difference_note}
                                </p>
                              )}
                            </div>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
