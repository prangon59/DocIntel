import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/layout/providers";
import { Navbar } from "@/components/layout/navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Document Intelligence System",
  description:
    "Enterprise AI document ingestion, OCR, Gemini extraction, financial validation, and cross-document verification.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-background text-foreground flex flex-col antialiased">
            <Navbar />
            <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 lg:p-8">{children}</main>
            <footer className="border-t border-border/60 py-4 px-6 text-center text-xs text-muted-foreground">
              DocIntel AI Document Intelligence System &bull; Production Architecture &bull; Next.js 14 App Router
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
