"use client";

import * as React from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastType = "default" | "success" | "error" | "info";

export interface ToastItem {
  id: string;
  title?: string;
  description: string;
  type?: ToastType;
  duration?: number;
}

interface ToastContextValue {
  toasts: ToastItem[];
  toast: (options: Omit<ToastItem, "id">) => void;
  dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = React.useCallback(
    (options: Omit<ToastItem, "id">) => {
      const id = Math.random().toString(36).slice(2, 9);
      const newToast: ToastItem = { id, ...options };
      setToasts((prev) => [...prev, newToast]);

      const duration = options.duration ?? 4000;
      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ toasts, toast: addToast, dismiss }}>
      {children}
      <Toaster />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return {
    toast: context.toast,
    dismiss: context.dismiss,
    success: (desc: string, title?: string) =>
      context.toast({ description: desc, title, type: "success" }),
    error: (desc: string, title?: string) =>
      context.toast({ description: desc, title, type: "error" }),
    info: (desc: string, title?: string) =>
      context.toast({ description: desc, title, type: "info" }),
  };
}

export function Toaster() {
  const context = React.useContext(ToastContext);
  if (!context) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {context.toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "pointer-events-auto flex items-start gap-3 p-4 rounded-lg border shadow-lg bg-card text-card-foreground transition-all duration-300 animate-in slide-in-from-bottom-5",
            t.type === "success" && "border-emerald-500/50 bg-emerald-950/20 text-emerald-200",
            t.type === "error" && "border-destructive/50 bg-destructive/15 text-destructive-foreground",
            t.type === "info" && "border-blue-500/50 bg-blue-950/20 text-blue-200"
          )}
        >
          {t.type === "success" && <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />}
          {t.type === "error" && <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />}
          {t.type === "info" && <Info className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />}
          
          <div className="flex-1 space-y-0.5">
            {t.title && <h5 className="font-medium text-sm leading-none">{t.title}</h5>}
            <p className="text-xs text-muted-foreground">{t.description}</p>
          </div>

          <button
            type="button"
            onClick={() => context.dismiss(t.id)}
            className="text-muted-foreground hover:text-foreground shrink-0 p-1"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
