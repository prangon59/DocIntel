import { DocumentStatus } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, Clock, Loader2 } from "lucide-react";

interface StatusBadgeProps {
  status: DocumentStatus | string;
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({ status, className, showIcon = true }: StatusBadgeProps) {
  const normStatus = (status || "").toUpperCase();

  switch (normStatus) {
    case "COMPLETED":
      return (
        <Badge variant="success" className={className}>
          {showIcon && <CheckCircle2 className="w-3 h-3 mr-1" />}
          COMPLETED
        </Badge>
      );
    case "PROCESSING":
      return (
        <Badge variant="warning" className={className}>
          {showIcon && <Loader2 className="w-3 h-3 mr-1 animate-spin" />}
          PROCESSING
        </Badge>
      );
    case "FAILED":
      return (
        <Badge variant="destructive" className={className}>
          {showIcon && <AlertCircle className="w-3 h-3 mr-1" />}
          FAILED
        </Badge>
      );
    case "PENDING":
    default:
      return (
        <Badge variant="secondary" className={className}>
          {showIcon && <Clock className="w-3 h-3 mr-1" />}
          {normStatus || "PENDING"}
        </Badge>
      );
  }
}
