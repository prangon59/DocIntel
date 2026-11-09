import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Document Intelligence System",
  description: "Enterprise document ingestion, extraction, validation, and search.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <div className="min-h-screen bg-background text-foreground flex flex-col">
          <header className="border-b border-border px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight">DocIntel</span>
              <span className="text-xs bg-primary/20 text-primary px-2 py-0.5 rounded-full font-medium">
                Phase 0
              </span>
            </div>
            <nav className="flex items-center gap-4 text-sm text-muted-foreground">
              <a href="/documents" className="hover:text-foreground transition-colors">
                Documents
              </a>
              <a href="/search" className="hover:text-foreground transition-colors">
                Search
              </a>
              <a href="/crossverify" className="hover:text-foreground transition-colors">
                Cross-Verify
              </a>
            </nav>
          </header>
          <main className="flex-1">{children}</main>
        </div>
      </body>
    </html>
  );
}
