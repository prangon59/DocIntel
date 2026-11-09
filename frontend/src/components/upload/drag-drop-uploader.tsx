"use client";

import * as React from "react";
import { UploadCloud, File, CheckCircle2, AlertCircle, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/components/ui/toast";
import { uploadDocuments, getDocumentStatus } from "@/lib/api/endpoints";

const ACCEPTED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".xlsx", ".xls", ".csv"];
const ACCEPTED_MIME_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/tiff",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
  "text/csv",
];

interface FileUploadState {
  id: string;
  file: File;
  status: "idle" | "uploading" | "processing" | "completed" | "failed";
  progress: number;
  stage?: string;
  errorMessage?: string;
  docId?: string;
}

interface DragDropUploaderProps {
  onUploadSuccess?: () => void;
  className?: string;
}

export function DragDropUploader({ onUploadSuccess, className }: DragDropUploaderProps) {
  const [isDragOver, setIsDragOver] = React.useState(false);
  const [fileList, setFileList] = React.useState<FileUploadState[]>([]);
  const [isUploading, setIsUploading] = React.useState(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const { toast, success, error } = useToast();

  const handleFiles = (files: FileList | File[]) => {
    const validFiles: FileUploadState[] = [];
    Array.from(files).forEach((file) => {
      const ext = `.${file.name.split(".").pop()?.toLowerCase()}`;
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        toast({
          title: "Unsupported Format",
          description: `Skipped ${file.name}: supported formats are PDF, JPG, PNG, TIFF, XLSX, XLS, CSV`,
          type: "error",
        });
        return;
      }

      validFiles.push({
        id: Math.random().toString(36).substring(2, 9),
        file,
        status: "idle",
        progress: 0,
      });
    });

    if (validFiles.length > 0) {
      setFileList((prev) => [...prev, ...validFiles]);
    }
  };

  const removeFile = (id: string) => {
    setFileList((prev) => prev.filter((item) => item.id !== id));
  };

  const startUpload = async () => {
    if (fileList.length === 0 || isUploading) return;

    setIsUploading(true);
    const filesToUpload = fileList.filter((f) => f.status === "idle" || f.status === "failed");

    // Set uploading state
    setFileList((prev) =>
      prev.map((item) =>
        item.status === "idle" || item.status === "failed"
          ? { ...item, status: "uploading", progress: 25 }
          : item
      )
    );

    try {
      const rawFiles = filesToUpload.map((f) => f.file);
      const res = await uploadDocuments(rawFiles);

      // Match returned items
      const updatedList = [...fileList];
      res.uploaded.forEach((uploadedDoc, index) => {
        const localItemIndex = updatedList.findIndex(
          (f) => f.file.name === uploadedDoc.filename && f.status === "uploading"
        );
        if (localItemIndex !== -1) {
          if (uploadedDoc.status === "FAILED") {
            updatedList[localItemIndex].status = "failed";
            updatedList[localItemIndex].progress = 100;
            updatedList[localItemIndex].errorMessage = "Server rejected file (magic-byte check failed)";
          } else {
            updatedList[localItemIndex].status = "processing";
            updatedList[localItemIndex].progress = 60;
            updatedList[localItemIndex].docId = String(uploadedDoc.id);
          }
        }
      });
      setFileList(updatedList);

      success(`Successfully uploaded ${res.uploaded.length} file(s) for extraction pipeline.`);

      // Poll processing files
      const processingItems = updatedList.filter(
        (f) => f.status === "processing" && f.docId
      );

      processingItems.forEach((item) => {
        pollStatus(item.id, item.docId!);
      });

      onUploadSuccess?.();
    } catch (err) {
      error("Failed to upload batch. Server may be unavailable.");
      setFileList((prev) =>
        prev.map((f) =>
          f.status === "uploading"
            ? { ...f, status: "failed", errorMessage: "Upload failed" }
            : f
        )
      );
    } finally {
      setIsUploading(false);
    }
  };

  const pollStatus = async (localId: string, docId: string) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const stat = await getDocumentStatus(docId);
        setFileList((prev) =>
          prev.map((item) => {
            if (item.id === localId) {
              const isDone = stat.status === "COMPLETED";
              const isFail = stat.status === "FAILED";
              return {
                ...item,
                status: isDone ? "completed" : isFail ? "failed" : "processing",
                progress: isDone ? 100 : Math.max(item.progress, stat.percentage),
                stage: stat.stage,
                errorMessage: stat.error_message || undefined,
              };
            }
            return item;
          })
        );

        if (stat.status === "COMPLETED" || stat.status === "FAILED" || attempts > 20) {
          clearInterval(interval);
          onUploadSuccess?.();
        }
      } catch {
        if (attempts > 5) clearInterval(interval);
      }
    }, 2000);
  };

  return (
    <div className={`space-y-4 ${className || ""}`}>
      {/* Drop Area */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (e.dataTransfer.files) {
            handleFiles(e.dataTransfer.files);
          }
        }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 flex flex-col items-center justify-center space-y-3 ${
          isDragOver
            ? "border-primary bg-primary/10 scale-[1.01]"
            : "border-border hover:border-primary/50 hover:bg-muted/30"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={(e) => {
            if (e.target.files) handleFiles(e.target.files);
          }}
        />
        <div className="w-12 h-12 rounded-full bg-primary/15 text-primary flex items-center justify-center">
          <UploadCloud className="w-6 h-6" />
        </div>
        <div>
          <p className="font-semibold text-sm text-foreground">
            Click to upload or drag & drop files here
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            PDF (up to 1,000 pages), JPG, PNG, TIFF, XLSX, XLS, CSV
          </p>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground bg-secondary/80 px-2.5 py-1 rounded-full">
          <span>Magic-byte validation</span>
          <span>&bull;</span>
          <span>OCR Fallback</span>
          <span>&bull;</span>
          <span>Parallel Chunking</span>
        </div>
      </div>

      {/* File List */}
      {fileList.length > 0 && (
        <div className="space-y-2 border border-border rounded-xl p-4 bg-card/60">
          <div className="flex items-center justify-between text-xs font-medium text-muted-foreground pb-2 border-b border-border">
            <span>Selected Documents ({fileList.length})</span>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setFileList([])}
                disabled={isUploading}
              >
                Clear All
              </Button>
              <Button
                size="sm"
                className="h-7 text-xs"
                onClick={startUpload}
                disabled={isUploading || fileList.every((f) => f.status === "completed")}
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  "Start Processing"
                )}
              </Button>
            </div>
          </div>

          <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
            {fileList.map((item) => (
              <div
                key={item.id}
                className="flex flex-col p-2.5 rounded-lg border border-border/60 bg-background/50 text-xs space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 truncate max-w-[70%]">
                    <File className="w-4 h-4 text-primary shrink-0" />
                    <span className="font-medium truncate">{item.file.name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      ({(item.file.size / 1024).toFixed(1)} KB)
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {item.status === "idle" && (
                      <span className="text-[11px] text-muted-foreground">Ready</span>
                    )}
                    {item.status === "uploading" && (
                      <span className="text-[11px] text-primary flex items-center gap-1">
                        <Loader2 className="w-3 h-3 animate-spin" /> Uploading
                      </span>
                    )}
                    {item.status === "processing" && (
                      <span className="text-[11px] text-amber-500 flex items-center gap-1 font-medium">
                        <Loader2 className="w-3 h-3 animate-spin" /> {item.stage || "Processing"}
                      </span>
                    )}
                    {item.status === "completed" && (
                      <span className="text-[11px] text-emerald-500 flex items-center gap-1 font-medium">
                        <CheckCircle2 className="w-3 h-3" /> Ingested
                      </span>
                    )}
                    {item.status === "failed" && (
                      <span className="text-[11px] text-destructive flex items-center gap-1 font-medium">
                        <AlertCircle className="w-3 h-3" /> Failed
                      </span>
                    )}

                    {item.status === "idle" && (
                      <button
                        type="button"
                        onClick={() => removeFile(item.id)}
                        className="text-muted-foreground hover:text-foreground p-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>

                {item.status !== "idle" && (
                  <Progress
                    value={item.progress}
                    indicatorClassName={
                      item.status === "failed"
                        ? "bg-destructive"
                        : item.status === "completed"
                        ? "bg-emerald-500"
                        : "bg-primary"
                    }
                  />
                )}

                {item.errorMessage && (
                  <p className="text-[10px] text-destructive">{item.errorMessage}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
