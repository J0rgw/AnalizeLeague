import { ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn, formatTimestamp } from "@/lib/utils";
import type { AgendaItem, AgendaLabel } from "@/lib/api";

const LABEL_ICONS: Record<AgendaLabel, string> = {
  fight:     "⚔",
  objective: "🏰",
  lane:      "〰",
  jungle:    "🌲",
  recall:    "↩",
};

interface AgendaRowProps {
  item: AgendaItem;
}

function AgendaRow({ item }: AgendaRowProps) {
  const { rank, t, label, title, context, what_to_watch } = item;
  const isCritical = rank === 1;

  // Deep-link placeholder — replace with actual VOD URL when backend provides it
  const vodHref = `#vod?t=${t}`;

  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        isCritical
          ? "border-red-500/40 bg-red-500/5"
          : "border-border bg-card hover:border-border/80"
      )}
    >
      <div className="flex items-start gap-3">
        {/* Rank */}
        <span
          className={cn(
            "flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold",
            isCritical
              ? "bg-red-500/20 text-red-400"
              : "bg-muted text-muted-foreground"
          )}
        >
          {rank}
        </span>

        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex flex-wrap items-center gap-2 mb-1.5">
            {/* Timestamp link */}
            <a
              href={vodHref}
              className="flex items-center gap-1 font-mono text-xs text-primary hover:underline"
              title="Open in VOD (placeholder)"
            >
              <span>{formatTimestamp(t)}</span>
              <ExternalLink className="h-3 w-3" />
            </a>

            {/* Label badge */}
            <Badge variant={label}>
              {LABEL_ICONS[label]} {label.charAt(0).toUpperCase() + label.slice(1)}
            </Badge>

            {/* Title */}
            <span className={cn("text-sm font-medium", isCritical ? "text-red-300" : "text-foreground")}>
              {title}
            </span>
          </div>

          {/* Context */}
          <p className="text-xs text-muted-foreground mb-1.5 font-mono">{context}</p>

          {/* What to watch */}
          <p className="text-xs text-foreground/80 leading-relaxed">{what_to_watch}</p>
        </div>
      </div>
    </div>
  );
}

interface ReviewAgendaProps {
  items: AgendaItem[];
}

export function ReviewAgenda({ items }: ReviewAgendaProps) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No agenda items available.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <AgendaRow key={item.rank} item={item} />
      ))}
    </div>
  );
}
