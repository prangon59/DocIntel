import { CorrectionAuditItem } from "@/lib/types";
import { History, UserCheck, ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface CorrectionHistoryProps {
  corrections: CorrectionAuditItem[];
}

export function CorrectionHistory({ corrections }: CorrectionHistoryProps) {
  if (!corrections || corrections.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-muted-foreground border border-dashed border-border rounded-xl">
        No manual corrections recorded. All fields are in original AI extraction state.
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <History className="w-4 h-4 text-primary" />
        <h4 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
          Audit Trail ({corrections.length} {corrections.length === 1 ? "correction" : "corrections"})
        </h4>
      </div>

      <div className="space-y-2.5">
        {corrections.map((item) => (
          <div
            key={item.id}
            className="p-3 rounded-lg border border-border bg-card/60 text-xs space-y-1.5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="font-mono text-[10px] uppercase">
                  {item.field_name}
                </Badge>
                <span className="text-[11px] text-muted-foreground inline-flex items-center gap-1 font-mono">
                  <UserCheck className="w-3 h-3 text-primary" />
                  {item.updated_by}
                </span>
              </div>
              <span className="text-[10px] text-muted-foreground font-mono">
                {formatDate(item.created_at)}
              </span>
            </div>

            <div className="flex items-center gap-2 font-mono text-xs bg-muted/30 p-2 rounded">
              <span className="text-muted-foreground line-through truncate max-w-[45%]">
                {item.old_value || "<null>"}
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <span className="text-foreground font-semibold truncate max-w-[45%]">
                {item.new_value || "<null>"}
              </span>
            </div>

            {item.reason && (
              <p className="text-[11px] text-muted-foreground italic">
                Reason: &ldquo;{item.reason}&rdquo;
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
