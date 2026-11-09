"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FileText, Search, GitCompare, LayoutDashboard, UploadCloud } from "lucide-react";
import { cn } from "@/lib/utils";
import { ApiBadge } from "@/components/common/api-badge";
import { getIsMockActive } from "@/lib/api/endpoints";
import { useEffect, useState } from "react";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Documents", icon: FileText },
  { href: "/search", label: "Search", icon: Search },
  { href: "/crossverify", label: "Cross-Verify", icon: GitCompare },
];

export function Navbar() {
  const pathname = usePathname();
  const [isMock, setIsMock] = useState(false);

  useEffect(() => {
    // Check mock status periodically
    const check = () => setIsMock(getIsMockActive());
    check();
    const interval = setInterval(check, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 lg:px-8 py-3">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Brand */}
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-90">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-black text-base shadow-sm">
              D
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-base tracking-tight leading-none">DocIntel</span>
              <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider mt-0.5">
                Enterprise AI
              </span>
            </div>
          </Link>

          {/* Navigation links */}
          <nav className="hidden md:flex items-center gap-1 text-sm font-medium">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors",
                    isActive
                      ? "bg-secondary text-foreground font-semibold"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Status & Actions */}
        <div className="flex items-center gap-3">
          <ApiBadge isMock={isMock} />
          <Link
            href="/documents?action=upload"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 transition-all active:scale-95"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Upload Invoices
          </Link>
        </div>
      </div>
    </header>
  );
}
