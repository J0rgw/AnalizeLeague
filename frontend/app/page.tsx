"use client";

import { useEffect, useState } from "react";
import { BarChart2, AlertCircle, RefreshCw } from "lucide-react";
import { GameCard } from "@/components/game-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { listGames } from "@/lib/api";
import type { GameSummary } from "@/lib/api";

function LoadingSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      <AlertCircle className="h-8 w-8 text-destructive" />
      <div>
        <p className="text-sm font-medium text-foreground">Failed to load games</p>
        <p className="text-xs text-muted-foreground mt-1">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="h-3.5 w-3.5" />
        Retry
      </Button>
    </div>
  );
}

export default function HomePage() {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    listGames()
      .then(setGames)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Unknown error")
      )
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const wins = games.filter((g) => g.result === "win").length;
  const losses = games.filter((g) => g.result === "loss").length;

  return (
    <div className="mx-auto max-w-screen-lg px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <BarChart2 className="h-5 w-5 text-primary" />
          <div>
            <h1 className="text-lg font-semibold">Scrim Library</h1>
            {!loading && !error && games.length > 0 && (
              <p className="text-xs text-muted-foreground">
                {games.length} games · {wins}W {losses}L
              </p>
            )}
          </div>
        </div>
        {!loading && (
          <Button variant="ghost" size="sm" onClick={load}>
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {/* Content */}
      {loading && <LoadingSkeleton />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && games.length === 0 && (
        <p className="text-sm text-muted-foreground text-center py-16">
          No games found. Make sure the backend is running and has data.
        </p>
      )}
      {!loading && !error && games.length > 0 && (
        <div className="space-y-2">
          {games.map((game, i) => (
            <GameCard key={game.game_id} game={game} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
