import { ExtractedLineItem } from "@/lib/types";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { ConfidenceBadge } from "@/components/common/confidence-badge";
import { Badge } from "@/components/ui/badge";

interface LineItemsTableProps {
  items: ExtractedLineItem[];
  currency?: string | null;
}

export function LineItemsTable({ items, currency = "USD" }: LineItemsTableProps) {
  if (!items || items.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-muted-foreground border border-dashed border-border rounded-xl">
        No individual line items detected or document is a summary receipt.
      </div>
    );
  }

  const formatMoney = (val: string | null) => {
    if (!val) return "—";
    const num = parseFloat(val);
    if (isNaN(num)) return val;
    return `${currency || "$"} ${num.toFixed(2)}`;
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
          Line Items ({items.length})
        </h4>
        <Badge variant="outline" className="text-[10px] font-mono">
          Currency: {currency || "USD"}
        </Badge>
      </div>

      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="w-[45%]">Description</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead className="text-right">Unit Price</TableHead>
              <TableHead className="text-right">Line Total</TableHead>
              <TableHead className="text-right w-20">Conf</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item, idx) => {
              const qty = parseFloat(item.quantity || "0");
              const price = parseFloat(item.unit_price || "0");
              const total = parseFloat(item.line_total || "0");
              const isMathClean =
                !isNaN(qty) && !isNaN(price) && !isNaN(total) && qty > 0
                  ? Math.abs(qty * price - total) < 0.05
                  : true;

              return (
                <TableRow key={item.id || idx}>
                  <TableCell className="font-medium text-xs">
                    {item.description || "Unlabeled Item"}
                  </TableCell>
                  <TableCell className="text-right text-xs font-mono">
                    {item.quantity || "—"}
                  </TableCell>
                  <TableCell className="text-right text-xs font-mono">
                    {formatMoney(item.unit_price)}
                  </TableCell>
                  <TableCell className="text-right text-xs font-mono font-semibold">
                    <span className={!isMathClean ? "text-destructive underline" : ""}>
                      {formatMoney(item.line_total)}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">
                    <ConfidenceBadge score={item.confidence} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
