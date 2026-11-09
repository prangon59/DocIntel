import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ConfidenceBadgeProps {
  score?: number | null;
  className?: string;
  showPercent?: boolean;
}

export function ConfidenceBadge({
  score,
  className,
  showPercent = true,
}: ConfidenceBadgeProps) {
  if (score === undefined || score === null) {
    return (
      <Badge variant="outline" className={cn("text-xs text-muted-foreground", className)}>
        N/A
      </Badge>
    );
  }

  const pct = Math.round(score * 100);

  if (score >= 0.85) {
    return (
      <Badge
        variant="success"
        className={cn("font-mono text-xs", className)}
        title={`High confidence: ${(score * 100).toFixed(1)}%`}
      >
        {showPercent ? `${pct}%` : "High"}
      </Badge>
    );
  }

  if (score >= 0.6) {
    return (
      <Badge
        variant="warning"
        className={cn("font-mono text-xs", className)}
        title={`Medium confidence: ${(score * 100).toFixed(1)}%`}
      >
        {showPercent ? `${pct}%` : "Medium"}
      </Badge>
    );
  }

  return (
    <Badge
      variant="destructive"
      className={cn("font-mono text-xs", className)}
      title={`Low confidence: ${(score * 100).toFixed(1)}% - verify carefully`}
    >
      {showPercent ? `${pct}%` : "Low"}
    </Badge>
  );
}
