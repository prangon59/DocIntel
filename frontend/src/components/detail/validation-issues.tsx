import { ValidationIssue } from "@/lib/types";
import { AlertCircle, AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ValidationIssuesProps {
  issues: ValidationIssue[];
}

export function ValidationIssues({ issues }: ValidationIssuesProps) {
  if (!issues || issues.length === 0) {
    return (
      <div className="flex items-center gap-2 p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs">
        <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
        <span>All deterministic validation checks passed with 100% mathematical consistency.</span>
      </div>
    );
  }

  const errorCount = issues.filter((i) => i.severity === "error").length;
  const warningCount = issues.filter((i) => i.severity === "warning").length;

  return (
    <div className="space-y-2.5">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
          Deterministic Validation ({issues.length} {issues.length === 1 ? "flag" : "flags"})
        </h4>
        <div className="flex items-center gap-1.5">
          {errorCount > 0 && (
            <Badge variant="destructive" className="text-[10px]">
              {errorCount} {errorCount === 1 ? "Error" : "Errors"}
            </Badge>
          )}
          {warningCount > 0 && (
            <Badge variant="warning" className="text-[10px]">
              {warningCount} {warningCount === 1 ? "Warning" : "Warnings"}
            </Badge>
          )}
        </div>
      </div>

      <div className="space-y-2">
        {issues.map((issue) => {
          const isError = issue.severity === "error";
          const isWarning = issue.severity === "warning";

          return (
            <div
              key={issue.id}
              className={`p-3 rounded-lg border text-xs flex items-start gap-3 transition-colors ${
                isError
                  ? "border-destructive/40 bg-destructive/10 text-destructive-foreground"
                  : isWarning
                  ? "border-amber-500/40 bg-amber-500/10 text-foreground"
                  : "border-blue-500/40 bg-blue-500/10 text-foreground"
              }`}
            >
              {isError && <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />}
              {isWarning && <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />}
              {!isError && !isWarning && <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />}

              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-xs">{issue.code}</span>
                  {issue.field && (
                    <Badge variant="outline" className="text-[10px] font-mono uppercase">
                      Field: {issue.field}
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground leading-normal">{issue.message}</p>
                {issue.details && (
                  <pre className="mt-1 p-1.5 rounded bg-background/50 text-[10px] font-mono text-muted-foreground overflow-x-auto">
                    {JSON.stringify(issue.details, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
