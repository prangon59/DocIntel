"use client";

import { Search, Filter, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { DocumentFilterParams, DocumentStatus } from "@/lib/types";

interface DocumentsFilterProps {
  filters: DocumentFilterParams;
  onFilterChange: (newFilters: Partial<DocumentFilterParams>) => void;
  onReset: () => void;
}

export function DocumentsFilter({
  filters,
  onFilterChange,
  onReset,
}: DocumentsFilterProps) {
  const isFiltered =
    filters.status !== undefined && filters.status !== "ALL" ||
    filters.needs_review !== undefined ||
    !!filters.file_type ||
    !!filters.search;

  return (
    <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3 p-4 rounded-xl border border-border bg-card shadow-sm">
      {/* Search Input */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Filter by filename..."
          value={filters.search || ""}
          onChange={(e) => onFilterChange({ search: e.target.value })}
          className="pl-9 h-9 text-xs"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {/* Status Filter */}
        <div className="w-36">
          <Select
            value={filters.status || "ALL"}
            onChange={(e) =>
              onFilterChange({
                status: e.target.value as DocumentStatus | "ALL",
              })
            }
            className="h-9 text-xs"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="PROCESSING">Processing</option>
            <option value="FAILED">Failed</option>
            <option value="PENDING">Pending</option>
          </Select>
        </div>

        {/* File Type Filter */}
        <div className="w-32">
          <Select
            value={filters.file_type || ""}
            onChange={(e) => onFilterChange({ file_type: e.target.value || undefined })}
            className="h-9 text-xs"
          >
            <option value="">All Formats</option>
            <option value="pdf">PDF</option>
            <option value="xlsx">Excel (.xlsx)</option>
            <option value="xls">Excel (.xls)</option>
            <option value="csv">CSV</option>
            <option value="png">PNG</option>
            <option value="jpg">JPG</option>
            <option value="tiff">TIFF</option>
          </Select>
        </div>

        {/* Needs Review Filter */}
        <div className="w-36">
          <Select
            value={
              filters.needs_review === undefined
                ? ""
                : filters.needs_review
                ? "review"
                : "clean"
            }
            onChange={(e) => {
              const val = e.target.value;
              onFilterChange({
                needs_review: val === "review" ? true : val === "clean" ? false : undefined,
              });
            }}
            className="h-9 text-xs"
          >
            <option value="">All Invoices</option>
            <option value="review">⚠️ Needs Review</option>
            <option value="clean">✅ Passed Validation</option>
          </Select>
        </div>

        {/* Reset Filter Button */}
        {isFiltered && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="h-9 px-2.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <X className="w-3.5 h-3.5 mr-1" />
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}
