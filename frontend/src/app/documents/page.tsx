"use client";

import * as React from "react";
import { Suspense } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { listDocuments, reprocessDocument } from "@/lib/api/endpoints";
import { DocumentFilterParams } from "@/lib/types";
import { DocumentsTable } from "@/components/documents/documents-table";
import { DocumentsFilter } from "@/components/documents/documents-filter";
import { DragDropUploader } from "@/components/upload/drag-drop-uploader";
import { TableLoadingSkeleton } from "@/components/common/loading-state";
import { ErrorState } from "@/components/common/error-state";
import { EmptyState } from "@/components/common/empty-state";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/toast";
import { UploadCloud, RefreshCw, FileText } from "lucide-react";

function DocumentsContent() {
  const searchParams = useSearchParams();
  const initialAction = searchParams.get("action");
  const [uploadDialogOpen, setUploadDialogOpen] = React.useState(initialAction === "upload");
  const { toast, success, error } = useToast();

  const [filters, setFilters] = React.useState<DocumentFilterParams>({
    status: "ALL",
    file_type: undefined,
    needs_review: undefined,
    search: "",
    skip: 0,
    limit: 50,
  });

  const {
    data,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["documents", filters],
    queryFn: () => listDocuments(filters),
  });

  const handleFilterChange = (newFilters: Partial<DocumentFilterParams>) => {
    setFilters((prev) => ({ ...prev, ...newFilters, skip: 0 }));
  };

  const handleResetFilters = () => {
    setFilters({
      status: "ALL",
      file_type: undefined,
      needs_review: undefined,
      search: "",
      skip: 0,
      limit: 50,
    });
  };

  const handleReprocess = async (id: string) => {
    try {
      await reprocessDocument(id);
      success("Document queued for full re-extraction.", "Reprocessing Triggered");
      refetch();
    } catch {
      error("Failed to reprocess document.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Documents Repository</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage ingested invoices, receipts, and spreadsheets with real-time status and validation alerts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="text-xs h-9 gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="text-xs h-9 gap-1.5 shadow-sm">
                <UploadCloud className="w-4 h-4" />
                Upload Files
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-xl">
              <DialogHeader>
                <DialogTitle className="text-base font-bold">
                  Upload Documents for Ingestion
                </DialogTitle>
              </DialogHeader>
              <DragDropUploader
                onUploadSuccess={() => {
                  refetch();
                }}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filter Toolbar */}
      <DocumentsFilter
        filters={filters}
        onFilterChange={handleFilterChange}
        onReset={handleResetFilters}
      />

      {/* Content */}
      {isLoading ? (
        <TableLoadingSkeleton rows={8} />
      ) : isError ? (
        <ErrorState
          title="Failed to load documents"
          message="Could not communicate with the documents backend service."
          onRetry={refetch}
        />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-8 h-8 text-muted-foreground" />}
          title="No documents found"
          description="There are no documents matching your current filters. Try resetting filters or uploading new invoice files."
          actionLabel="Upload Invoices"
          onAction={() => setUploadDialogOpen(true)}
        />
      ) : (
        <div className="space-y-4">
          <DocumentsTable documents={data.items} onReprocess={handleReprocess} />

          {/* Pagination Footer */}
          <div className="flex items-center justify-between text-xs text-muted-foreground px-2">
            <span>
              Showing {data.items.length} of {data.total} documents
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={filters.skip === 0}
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    skip: Math.max(0, (prev.skip || 0) - (prev.limit || 50)),
                  }))
                }
                className="h-8 text-xs"
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={(filters.skip || 0) + data.items.length >= data.total}
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    skip: (prev.skip || 0) + (prev.limit || 50),
                  }))
                }
                className="h-8 text-xs"
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={<TableLoadingSkeleton rows={6} />}>
      <DocumentsContent />
    </Suspense>
  );
}
