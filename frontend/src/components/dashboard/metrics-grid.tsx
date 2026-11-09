import { MetricsResponse } from "@/lib/types";
import { CheckCircle2, AlertTriangle, Clock, Sparkles, FileText, XCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface MetricsGridProps {
  metrics: MetricsResponse;
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  const cards = [
    {
      title: "Total Invoices",
      value: metrics.total_documents,
      subtitle: `${metrics.completed_count} successfully parsed`,
      icon: FileText,
      color: "text-primary",
      bg: "bg-primary/10",
    },
    {
      title: "Success Rate",
      value: `${metrics.success_rate.toFixed(1)}%`,
      subtitle: `${metrics.failure_rate.toFixed(1)}% failure rate`,
      icon: CheckCircle2,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    {
      title: "Avg Processing Time",
      value: `${metrics.avg_processing_time_seconds.toFixed(1)}s`,
      subtitle: "Digital text + OCR fallback",
      icon: Clock,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
    },
    {
      title: "Needs Review",
      value: metrics.needs_review_count,
      subtitle: "Math flags or low confidence",
      icon: AlertTriangle,
      color: "text-amber-400",
      bg: "bg-amber-500/10",
    },
    {
      title: "Failed Documents",
      value: metrics.failed_count,
      subtitle: "Batch continued safely",
      icon: XCircle,
      color: "text-destructive",
      bg: "bg-destructive/10",
    },
    {
      title: "Extraction Confidence",
      value: `${(metrics.avg_confidence_score * 100).toFixed(0)}%`,
      subtitle: "Gemini 2.5 Flash Grounding",
      icon: Sparkles,
      color: "text-purple-400",
      bg: "bg-purple-500/10",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <Card key={i} className="shadow-sm border-border bg-card">
            <CardContent className="p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground font-medium truncate">
                  {c.title}
                </span>
                <div className={`p-1.5 rounded-md ${c.bg} ${c.color}`}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
              </div>
              <div className="text-xl sm:text-2xl font-bold tracking-tight font-mono">
                {c.value}
              </div>
              <p className="text-[10px] text-muted-foreground truncate">{c.subtitle}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
