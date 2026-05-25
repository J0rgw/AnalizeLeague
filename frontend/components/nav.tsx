"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, MessageSquare, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const APP_LINKS = [
  { href: "/app", icon: BarChart2,     label: "Games" },
  { href: "/ask", icon: MessageSquare, label: "Ask"   },
];

export function Nav() {
  const pathname = usePathname();
  const isLanding = pathname === "/";

  return (
    <header className="fixed top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center gap-6 px-6">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-semibold text-foreground transition-colors duration-200 hover:text-primary"
        >
          <Shield className="h-4 w-4 text-primary" />
          <span className="tracking-tight">AnalizeLeague</span>
        </Link>

        {isLanding ? (
          /* Landing page: only a CTA button on the right */
          <div className="ml-auto">
            <Button size="sm" asChild>
              <Link href="/app">Open App</Link>
            </Button>
          </div>
        ) : (
          /* App pages: internal navigation */
          <>
            <div className="h-4 w-px shrink-0 bg-border" />

            <nav className="flex items-center gap-0.5">
              {APP_LINKS.map(({ href, icon: Icon, label }) => {
                const isActive = pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={cn(
                      "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors duration-150",
                      isActive
                        ? "text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </Link>
                );
              })}
            </nav>

            {/* Mock data indicator */}
            {process.env.NEXT_PUBLIC_USE_MOCKS === "true" && (
              <div className="ml-auto flex items-center gap-1.5 rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                MOCK DATA
              </div>
            )}
          </>
        )}
      </div>
    </header>
  );
}
