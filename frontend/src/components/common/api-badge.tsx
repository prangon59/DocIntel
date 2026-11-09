import { Badge } from "@/components/ui/badge";
import { CheckCircle2, ShieldAlert } from "lucide-react";

interface ApiBadgeProps {
  isMock?: boolean;
  className?: string;
}

export function ApiBadge({ isMock, className }: ApiBadgeProps) {
  if (isMock) {
    return (
      <Badge
        variant="warning"
        className={`text-[11px] font-medium tracking-tight ${className || ""}`}
        title="Active: typed API client with synthetic mock fallback for endpoints in progress (Phase 3)"
      >
        <ShieldAlert className="w-3 h-3 mr-1" />
        Mock Fallback Mode
      </Badge>
    );
  }

  return (
    <Badge
      variant="success"
      className={`text-[11px] font-medium tracking-tight ${className || ""}`}
      title="Backend connected at localhost:8000"
    >
      <CheckCircle2 className="w-3 h-3 mr-1" />
      API Connected
    </Badge>
  );
}
