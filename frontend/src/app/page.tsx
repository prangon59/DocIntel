import Link from "next/link";

export default function Home() {
  return (
    <div className="container max-w-5xl mx-auto py-12 px-4 space-y-8">
      <div className="space-y-3">
        <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
          AI-Powered Document Intelligence System
        </h1>
        <p className="text-muted-foreground text-lg max-w-3xl">
          Automated multi-format document ingestion, OCR, Gemini 2.5 Flash invoice extraction,
          deterministic financial validation, and cross-document verification.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
        <div className="rounded-lg border border-border p-6 space-y-2 bg-card">
          <h2 className="text-lg font-semibold">1. Multi-Format Ingestion</h2>
          <p className="text-sm text-muted-foreground">
            Ingest PDFs up to 1,000 pages, scanned images, TIFF, Excel, and CSV files with
            magic-byte validation and OCR fallback.
          </p>
        </div>

        <div className="rounded-lg border border-border p-6 space-y-2 bg-card">
          <h2 className="text-lg font-semibold">2. Grounded Extraction</h2>
          <p className="text-sm text-muted-foreground">
            Structured invoice extraction via Gemini 2.5 Flash with strict Decimal arithmetic,
            source grounding, and confidence scores.
          </p>
        </div>

        <div className="rounded-lg border border-border p-6 space-y-2 bg-card">
          <h2 className="text-lg font-semibold">3. Deterministic Validation</h2>
          <p className="text-sm text-muted-foreground">
            Non-LLM mathematical consistency rules, duplicate detection, and cross-document
            reconciliation (PDF ↔ PDF, PDF ↔ Excel).
          </p>
        </div>
      </div>

      <div className="pt-4 flex items-center gap-4">
        <div className="inline-flex items-center gap-2 text-sm text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-3 py-1.5 rounded-md">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Phase 0 Initialized — Ready for Phase 1 DB & Ingestion Pipeline
        </div>
      </div>
    </div>
  );
}
