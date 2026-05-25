import Link from "next/link";
import { ChevronRight, Clock, Swords } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { formatDuration } from "@/lib/utils";
import type { GameSummary } from "@/lib/api";

interface GameCardProps {
  game: GameSummary;
  index: number;
}

export function GameCard({ game, index }: GameCardProps) {
  const { game_id, patch, duration_s, side, result } = game;

  return (
    <Link
      href={`/games/${encodeURIComponent(game_id)}`}
      className="group flex items-center gap-4 border-b border-border py-4 transition-colors duration-150 ease-[cubic-bezier(0.25,1,0.5,1)] hover:bg-muted/40 animate-fade-in"
      style={{ animationDelay: `${index * 45}ms` }}
    >
      {/* Index */}
      <span className="w-6 shrink-0 text-right font-mono text-xs text-muted-foreground/50">
        {index + 1}
      </span>

      {/* Result + side */}
      <div className="flex shrink-0 items-center gap-1.5">
        <Badge variant={result === "win" ? "win" : "loss"}>
          {result === "win" ? "W" : "L"}
        </Badge>
        <Badge variant={side === "blue" ? "blue" : "red"}>
          {side === "blue" ? "Blue" : "Red"}
        </Badge>
      </div>

      {/* Game ID + patch */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{game_id}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">Patch {patch}</p>
      </div>

      {/* Duration */}
      <div className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
        <Clock className="h-3 w-3" />
        <span className="font-mono">{formatDuration(duration_s)}</span>
      </div>

      {/* Review hint — hidden on small screens */}
      <div className="hidden shrink-0 items-center gap-1 text-xs text-muted-foreground sm:flex">
        <Swords className="h-3 w-3" />
        <span>Review</span>
      </div>

      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/50 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-muted-foreground" />
    </Link>
  );
}
