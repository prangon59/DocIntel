"use client";

import Link from "next/link";
import { DocumentRead } from "@/lib/types";
import { StatusBadge } from "@/components/common/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  FileText,
  AlertTriangle,
  ExternalLink,
  RotateCw,
  FileSpreadsheet,
  FileImage,
} from "lucide-react";

interface DocumentsTableProps {
  documents: DocumentRead[];
  onReprocess?: (id: string) => void;
}

export function DocumentsTable({ documents, onReprocess }: DocumentsTableProps) {
  const getFormatIcon = (format: string) => {
    const f = (format || "").toLowerCase();
    if (f === "xlsx" || f === "xls" || f === "csv") {
      return <FileSpreadsheet className="w-4 h-4 text-emerald-500" />;
    }
    if (f === "png" || f === "jpg" || f === "jpeg" || f === "tiff") {
      return <FileImage className="w-4 h-4 text-purple-400" />;
    }
    return <FileText className="w-4 h-4 text-primary" />;
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/40 hover:bg-muted/40">
            <TableHead className="w-[320px]">Document</TableHead>
            <TableHead className="w-[110px]">Format</TableHead>
            <TableHead className="w-[120px]">Pages</TableHead>
            <TableHead className="w-[140px]">Status</TableHead>
            <TableHead className="w-[150px]">Validation</TableHead>
            <TableHead className="w-[180px]">Uploaded At</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id} className="group hover:bg-muted/30">
              <TableCell className="font-medium">
                <Link
                  href={`/documents/${doc.id}`}
                  className="flex items-center gap-2.5 text-foreground hover:text-primary transition-colors group-hover:underline"
                >
                  {getFormatIcon(doc.file_type)}
                  <div className="flex flex-col truncate max-w-[260px]">
                    <span className="truncate text-sm font-semibold">{doc.filename}</span>
                    <span className="text-[11px] text-muted-foreground font-mono">
                      {formatFileSize(doc.file_size)}
                    </span>
                  </div>
                </Link>
              </TableCell>

              <TableCell>
                <Badge variant="outline" className="uppercase text-[10px] font-mono tracking-wider">
                  {doc.file_type}
                </Badge>
              </TableCell>

              <TableCell>
                <span className="text-xs text-muted-foreground font-mono">
                  {doc.page_count > 0 ? `${doc.page_count} pg` : "—"}
                </span>
              </TableCell>

              <TableCell>
                <StatusBadge status={doc.status} />
              </TableCell>

              <TableCell>
                {doc.needs_review ? (
                  <Badge variant="warning" className="text-[11px] inline-flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3 text-amber-500" />
                    Needs Review
                  </Badge>
                ) : doc.status === "COMPLETED" ? (
                  <Badge variant="success" className="text-[11px]">
                    Passed
                  </Badge>
                ) : (
                  <span className="text-xs text-muted-foreground">—</span>
                )}
              </TableCell>

              <TableCell className="text-xs text-muted-foreground font-mono">
                {formatDate(doc.created_at)}
              </TableCell>

              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-1.5">
                  {onReprocess && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onReprocess(doc.id)}
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                      title="Reprocess Document"
                    >
                      <RotateCw className="w-3.5 h-3.5" />
                    </Button>
                  )}
                  <Link href={`/documents/${doc.id}`}>
                    <Button variant="outline" size="sm" className="h-8 text-xs gap-1">
                      Details
                      <ExternalLink className="w-3 h-3" />
                    </Button>
                  </Link>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
