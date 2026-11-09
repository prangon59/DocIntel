"use client";

import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { InvoiceExtraction, UpdateExtractionPayload } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ConfidenceBadge } from "@/components/common/confidence-badge";
import { useToast } from "@/components/ui/toast";
import { updateDocumentResult } from "@/lib/api/endpoints";
import { Save, Loader2, Sparkles, AlertCircle } from "lucide-react";

const extractionSchema = z.object({
  invoice_number: z.string().nullable().optional(),
  invoice_date: z.string().nullable().optional(),
  supplier_name: z.string().nullable().optional(),
  customer_name: z.string().nullable().optional(),
  subtotal: z.string().nullable().optional(),
  tax: z.string().nullable().optional(),
  total: z.string().nullable().optional(),
  currency: z.string().nullable().optional(),
  reason: z.string().optional(),
});

type FormValues = z.infer<typeof extractionSchema>;

interface ExtractionFormProps {
  documentId: string;
  extraction: InvoiceExtraction | null;
  onSaved?: () => void;
}

export function ExtractionForm({ documentId, extraction, onSaved }: ExtractionFormProps) {
  const [isSaving, setIsSaving] = React.useState(false);
  const { toast, success, error } = useToast();

  const {
    register,
    handleSubmit,
    reset,
    formState: { isDirty, errors },
  } = useForm<FormValues>({
    resolver: zodResolver(extractionSchema),
    defaultValues: {
      invoice_number: extraction?.invoice_number || "",
      invoice_date: extraction?.invoice_date || "",
      supplier_name: extraction?.supplier_name || "",
      customer_name: extraction?.customer_name || "",
      subtotal: extraction?.subtotal || "",
      tax: extraction?.tax || "",
      total: extraction?.total || "",
      currency: extraction?.currency || "USD",
      reason: "",
    },
  });

  // Keep form in sync when extraction changes
  React.useEffect(() => {
    if (extraction) {
      reset({
        invoice_number: extraction.invoice_number || "",
        invoice_date: extraction.invoice_date || "",
        supplier_name: extraction.supplier_name || "",
        customer_name: extraction.customer_name || "",
        subtotal: extraction.subtotal || "",
        tax: extraction.tax || "",
        total: extraction.total || "",
        currency: extraction.currency || "USD",
        reason: "",
      });
    }
  }, [extraction, reset]);

  const onSubmit = async (values: FormValues) => {
    setIsSaving(true);
    try {
      const payload: UpdateExtractionPayload = {
        invoice_number: values.invoice_number || null,
        invoice_date: values.invoice_date || null,
        supplier_name: values.supplier_name || null,
        customer_name: values.customer_name || null,
        subtotal: values.subtotal || null,
        tax: values.tax || null,
        total: values.total || null,
        currency: values.currency || null,
        reason: values.reason || "Manual user correction",
        updated_by: "reviewer_ui",
      };

      await updateDocumentResult(documentId, payload);
      success("Extraction data updated and deterministic validation re-run.", "Changes Saved");
      onSaved?.();
    } catch (err) {
      error("Failed to save changes. Please try again.", "Error");
    } finally {
      setIsSaving(false);
    }
  };

  const getConf = (field: string) => {
    if (!extraction?.confidence_scores) return extraction?.confidence;
    return extraction.confidence_scores[field];
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <h4 className="text-xs font-semibold tracking-wide uppercase text-muted-foreground">
            Structured Extraction
          </h4>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Overall Conf:</span>
          <ConfidenceBadge score={extraction?.confidence} />
        </div>
      </div>

      {/* Grid Fields */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Invoice Number */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Invoice Number</label>
            <ConfidenceBadge score={getConf("invoice_number")} />
          </div>
          <Input
            {...register("invoice_number")}
            placeholder="e.g. INV-2024-001"
            className="font-mono text-xs h-9"
          />
        </div>

        {/* Invoice Date */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Invoice Date (ISO)</label>
            <ConfidenceBadge score={getConf("invoice_date")} />
          </div>
          <Input
            {...register("invoice_date")}
            placeholder="YYYY-MM-DD"
            className="font-mono text-xs h-9"
          />
        </div>

        {/* Supplier Name */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Supplier Name</label>
            <ConfidenceBadge score={getConf("supplier_name")} />
          </div>
          <Input
            {...register("supplier_name")}
            placeholder="Supplier / Vendor name"
            className="text-xs h-9"
          />
        </div>

        {/* Customer Name */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Customer Name</label>
            <ConfidenceBadge score={getConf("customer_name")} />
          </div>
          <Input
            {...register("customer_name")}
            placeholder="Billed customer name"
            className="text-xs h-9"
          />
        </div>

        {/* Subtotal */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Subtotal</label>
            <ConfidenceBadge score={getConf("subtotal")} />
          </div>
          <Input
            {...register("subtotal")}
            placeholder="0.00"
            className="font-mono text-xs h-9"
          />
        </div>

        {/* Tax */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Tax Amount</label>
            <ConfidenceBadge score={getConf("tax")} />
          </div>
          <Input
            {...register("tax")}
            placeholder="0.00"
            className="font-mono text-xs h-9"
          />
        </div>

        {/* Total */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground font-semibold">Total Amount</label>
            <ConfidenceBadge score={getConf("total")} />
          </div>
          <Input
            {...register("total")}
            placeholder="0.00"
            className="font-mono text-xs h-9 font-semibold text-primary"
          />
        </div>

        {/* Currency */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Currency (ISO 4217)</label>
            <ConfidenceBadge score={getConf("currency")} />
          </div>
          <Input
            {...register("currency")}
            placeholder="USD, EUR, GBP"
            className="font-mono text-xs h-9 uppercase"
          />
        </div>
      </div>

      {/* Reason for Correction */}
      {isDirty && (
        <div className="p-3 rounded-lg border border-primary/30 bg-primary/5 space-y-1.5 animate-in fade-in-50">
          <label className="text-xs font-medium text-foreground flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 text-primary" />
            Correction Justification (recorded in Audit Log)
          </label>
          <Input
            {...register("reason")}
            placeholder="Explain reason for manual edit (e.g., corrected OCR mistype on total)..."
            className="text-xs h-8 bg-background"
          />
        </div>
      )}

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2">
        <span className="text-[11px] text-muted-foreground">
          {isDirty ? "Unsaved edits detected" : "All fields saved"}
        </span>
        <Button
          type="submit"
          size="sm"
          disabled={!isDirty || isSaving}
          className="gap-1.5 text-xs h-8"
        >
          {isSaving ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-3.5 h-3.5" />
              Save Corrections
            </>
          )}
        </Button>
      </div>
    </form>
  );
}
