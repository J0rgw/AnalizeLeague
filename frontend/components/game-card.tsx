import Link from "next/link";
import { ChevronRight, Clock, Swords } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
    <Link href={`/games/${encodeURIComponent(game_id)}`}>
      <Card className="group cursor-pointer transition-all duration-150 hover:border-primary/40 hover:bg-card/80">
        <CardContent className="flex items-center gap-4 p-4">
          {/* Index */}
          <span className="w-6 text-center text-xs text-muted-foreground font-mono">
            {index + 1}
          </span>

          {/* Result + side */}
          <div className="flex flex-col items-center gap-1 w-16">
            <Badge variant={result === "win" ? "win" : "loss"}>
              {result === "win" ? "WIN" : "LOSS"}
            </Badge>
            <Badge variant={side === "blue" ? "blue" : "red"} className="capitalize">
              {side}
            </Badge>
          </div>

          {/* Game ID */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{game_id}</p>
            <p className="text-xs text-muted-foreground mt-0.5">Patch {patch}</p>
          </div>

          {/* Duration */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span className="font-mono">{formatDuration(duration_s)}</span>
          </div>

          {/* Fights hint */}
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Swords className="h-3 w-3" />
            <span>Review</span>
          </div>

          <ChevronRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
        </CardContent>
      </Card>
    </Link>
  );
}
