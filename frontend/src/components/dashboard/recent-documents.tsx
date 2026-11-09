import Link from "next/link";
import { DocumentRead } from "@/lib/types";
import { StatusBadge } from "@/components/common/status-badge";
import { Badge } from "@/components/ui/badge";
import { FileText, ArrowRight, AlertTriangle } from "lucide-react";

interface RecentDocumentsProps {
  documents: DocumentRead[];
}

export function RecentDocuments({ documents }: RecentDocumentsProps) {
  if (!documents || documents.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground border border-dashed rounded-xl">
        No recent documents. Upload documents above to begin.
      </div>
    );
  }

  const formatFileSize = (bytes: number) => {
    if (!bytes) return "0 B";
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-tight">Recent Ingestions</h3>
        <Link
          href="/documents"
          className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
        >
          View all
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="divide-y divide-border/60 rounded-xl border border-border bg-card shadow-sm overflow-hidden">
        {documents.slice(0, 5).map((doc) => (
          <div
            key={doc.id}
            className="p-3.5 flex items-center justify-between hover:bg-muted/30 transition-colors"
          >
            <div className="flex items-center gap-3 truncate max-w-[60%]">
              <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center text-primary shrink-0">
                <FileText className="w-4 h-4" />
              </div>
              <div className="flex flex-col truncate">
                <Link
                  href={`/documents/${doc.id}`}
                  className="font-medium text-xs hover:underline text-foreground truncate"
                >
                  {doc.filename}
                </Link>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono">
                  <span className="uppercase">{doc.file_type}</span>
                  <span>&bull;</span>
                  <span>{formatFileSize(doc.file_size)}</span>
                  <span>&bull;</span>
                  <span>{formatDate(doc.created_at)}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {doc.needs_review && (
                <Badge variant="warning" className="text-[10px] hidden sm:inline-flex">
                  <AlertTriangle className="w-3 h-3 mr-1" />
                  Review
                </Badge>
              )}
              <StatusBadge status={doc.status} />
              <Link href={`/documents/${doc.id}`}>
                <span className="text-xs text-muted-foreground hover:text-foreground font-medium p-1">
                  &rarr;
                </span>
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
