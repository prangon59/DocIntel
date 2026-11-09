"use client";

import * as React from "react";
import { PageRead } from "@/lib/types";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { FileText, Cpu, Eye } from "lucide-react";

interface DocumentViewerProps {
  filename: string;
  fileType: string;
  pages: PageRead[];
}

export function DocumentViewer({ filename, fileType, pages }: DocumentViewerProps) {
  const [selectedPageIndex, setSelectedPageIndex] = React.useState<number>(0);

  const activePage = pages[selectedPageIndex] || {
    page_number: 1,
    raw_text: "No text extracted for this document.",
    extraction_method: "n/a",
    ocr_confidence: null,
    char_count: 0,
  };

  return (
    <div className="rounded-xl border border-border bg-card flex flex-col h-full shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between bg-muted/20">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-primary" />
          <span className="font-semibold text-sm truncate max-w-xs">{filename}</span>
          <Badge variant="outline" className="text-[10px] uppercase font-mono">
            {fileType}
          </Badge>
        </div>
        <div className="text-xs text-muted-foreground font-mono">
          {pages.length} {pages.length === 1 ? "page" : "pages"}
        </div>
      </div>

      {/* Page Tabs */}
      {pages.length > 1 && (
        <div className="px-4 py-2 border-b border-border/60 bg-muted/10 overflow-x-auto flex items-center gap-1.5">
          {pages.map((p, idx) => (
            <button
              key={p.page_number}
              type="button"
              onClick={() => setSelectedPageIndex(idx)}
              className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
                selectedPageIndex === idx
                  ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              Page {p.page_number}
            </button>
          ))}
        </div>
      )}

      {/* Page Metadata Bar */}
      <div className="px-4 py-2 bg-muted/30 border-b border-border/40 flex items-center justify-between text-xs text-muted-foreground font-mono">
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1">
            <Cpu className="w-3.5 h-3.5" />
            Method: <strong className="text-foreground">{activePage.extraction_method}</strong>
          </span>
          {activePage.ocr_confidence !== null && activePage.ocr_confidence !== undefined && (
            <span>
              OCR Conf:{" "}
              <strong className="text-foreground">
                {(activePage.ocr_confidence * 100).toFixed(0)}%
              </strong>
            </span>
          )}
        </div>
        <span>{activePage.char_count} chars</span>
      </div>

      {/* Text Content */}
      <div className="flex-1 p-4 overflow-y-auto font-mono text-xs leading-relaxed whitespace-pre-wrap text-foreground/90 bg-background/50 selection:bg-primary/30 min-h-[380px]">
        {activePage.raw_text}
      </div>
    </div>
  );
}
