"use client";

import * as React from "react";
import Link from "next/link";
import { Search, Sparkles, Filter, ExternalLink, FileText, ArrowRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/common/status-badge";
import { TableLoadingSkeleton } from "@/components/common/loading-state";
import { EmptyState } from "@/components/common/empty-state";
import { searchDocuments } from "@/lib/api/endpoints";
import { SearchMode, SearchResponse, SearchResultItem } from "@/lib/types";
import { useQuery } from "@tanstack/react-query";

export function SearchView() {
  const [query, setQuery] = React.useState("hydraulic pump");
  const [activeQuery, setActiveQuery] = React.useState("hydraulic pump");
  const [mode, setMode] = React.useState<SearchMode>("hybrid");

  const { data, isLoading, isError, refetch } = useQuery<SearchResponse>({
    queryKey: ["search", activeQuery, mode],
    queryFn: () => searchDocuments(activeQuery, mode),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveQuery(query);
  };

  return (
    <div className="space-y-6">
      {/* Search Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Enterprise Document Search</h1>
        <p className="text-sm text-muted-foreground">
          Retrieve invoices and receipts using full-text keyword indexing, vector semantic search, or hybrid RRF fusion.
        </p>
      </div>

      {/* Search Controls */}
      <form onSubmit={handleSearch} className="space-y-3">
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by invoice #, vendor, line item description, or natural phrase..."
              className="pl-10 h-10 text-sm bg-card shadow-sm"
            />
          </div>
          <Button type="submit" className="h-10 px-6 font-semibold">
            Search
          </Button>
        </div>

        {/* Mode Toggle Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="inline-flex rounded-lg border border-border p-1 bg-muted/40 text-xs">
            <button
              type="button"
              onClick={() => setMode("keyword")}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                mode === "keyword"
                  ? "bg-background text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Keyword (PostgreSQL tsvector)
            </button>
            <button
              type="button"
              onClick={() => setMode("semantic")}
              className={`px-3 py-1.5 rounded-md font-medium transition-all ${
                mode === "semantic"
                  ? "bg-background text-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Semantic (pgvector)
            </button>
            <button
              type="button"
              onClick={() => setMode("hybrid")}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 ${
                mode === "hybrid"
                  ? "bg-primary text-primary-foreground shadow-sm font-semibold"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Hybrid (RRF Fusion)
            </button>
          </div>

          {data && (
            <span className="text-xs text-muted-foreground font-mono">
              Found {data.total_hits} {data.total_hits === 1 ? "document" : "documents"}
            </span>
          )}
        </div>
      </form>

      {/* Results Section */}
      {isLoading ? (
        <TableLoadingSkeleton rows={4} />
      ) : isError ? (
        <div className="p-8 text-center border border-destructive/30 rounded-xl bg-destructive/10 text-destructive text-sm">
          Failed to execute search. Please check your query or backend connection.
        </div>
      ) : !data || data.results.length === 0 ? (
        <EmptyState
          title="No documents matched your query"
          description={`We couldn't find any documents matching "${activeQuery}" in ${mode} mode. Try adjusting your keywords or toggle search modes.`}
          actionLabel="Try 'hydraulic pump'"
          onAction={() => {
            setQuery("hydraulic pump");
            setActiveQuery("hydraulic pump");
          }}
        />
      ) : (
        <div className="space-y-3">
          {data.results.map((item: SearchResultItem) => (
            <div
              key={item.document_id}
              className="p-5 rounded-xl border border-border bg-card shadow-sm hover:border-primary/40 transition-colors space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2.5 truncate">
                  <FileText className="w-5 h-5 text-primary shrink-0" />
                  <Link
                    href={`/documents/${item.document_id}`}
                    className="font-semibold text-sm hover:underline hover:text-primary transition-colors truncate"
                  >
                    {item.filename}
                  </Link>
                  <Badge variant="outline" className="text-[10px] uppercase font-mono">
                    {item.file_type}
                  </Badge>
                  <StatusBadge status={item.status} />
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant="secondary" className="font-mono text-xs">
                    Score: {(item.score * 100).toFixed(0)}%
                  </Badge>
                  <Badge variant="outline" className="text-[10px] capitalize">
                    {item.match_type}
                  </Badge>
                  <Link href={`/documents/${item.document_id}`}>
                    <Button variant="ghost" size="sm" className="h-7 text-xs gap-1">
                      View
                      <ExternalLink className="w-3 h-3" />
                    </Button>
                  </Link>
                </div>
              </div>

              {/* Highlight snippet */}
              {item.highlight && (
                <div
                  className="text-xs text-muted-foreground bg-muted/40 p-3 rounded-lg font-sans leading-relaxed border border-border/40"
                  dangerouslySetInnerHTML={{ __html: item.highlight }}
                />
              )}

              {/* Structured Metadata Row */}
              <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-muted-foreground pt-1 border-t border-border/40">
                {item.invoice_number && (
                  <span>
                    Inv #: <strong className="text-foreground font-mono">{item.invoice_number}</strong>
                  </span>
                )}
                {item.supplier_name && (
                  <span>
                    Supplier: <strong className="text-foreground">{item.supplier_name}</strong>
                  </span>
                )}
                {item.total && (
                  <span>
                    Total:{" "}
                    <strong className="text-foreground font-mono">
                      {item.currency || "$"} {item.total}
                    </strong>
                  </span>
                )}
                {item.invoice_date && (
                  <span>
                    Date: <strong className="text-foreground font-mono">{item.invoice_date}</strong>
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
