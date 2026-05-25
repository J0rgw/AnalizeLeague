import Link from "next/link";
import { BarChart2, MessageSquare, Shield } from "lucide-react";

export function Nav() {
  return (
    <header className="fixed top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-screen-xl items-center gap-6 px-6">
        {/* Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold text-foreground hover:text-primary transition-colors"
        >
          <Shield className="h-5 w-5 text-primary" />
          <span className="tracking-tight">AnalizeLeague</span>
        </Link>

        <div className="h-4 w-px bg-border" />

        {/* Nav links */}
        <nav className="flex items-center gap-1">
          <Link
            href="/"
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <BarChart2 className="h-3.5 w-3.5" />
            Games
          </Link>
          <Link
            href="/ask"
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            Ask
          </Link>
        </nav>

        {/* Mock indicator */}
        {process.env.NEXT_PUBLIC_USE_MOCKS === "true" && (
          <div className="ml-auto flex items-center gap-1.5 rounded-sm border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs text-amber-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            MOCK DATA
          </div>
        )}
      </div>
    </header>
  );
}
