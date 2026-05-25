"use client";

import { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { GameCard } from "@/components/game-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { listGames } from "@/lib/api";
import type { GameSummary } from "@/lib/api";

function LoadingSkeleton() {
  return (
    <div className="border-t border-border animate-fade-in">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="flex items-center gap-4 border-b border-border py-4">
          <Skeleton className="h-3 w-6 shrink-0" />
          <div className="flex shrink-0 gap-1.5">
            <Skeleton className="h-5 w-7 rounded-sm" />
            <Skeleton className="h-5 w-10 rounded-sm" />
          </div>
          <div className="flex-1 space-y-1.5">
            <Skeleton className="h-3.5 w-40" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-3 w-12 shrink-0" />
          <Skeleton className="h-3 w-10 shrink-0" />
          <Skeleton className="h-4 w-4 shrink-0 rounded" />
        </div>
      ))}
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-16 text-center animate-fade-in">
      <AlertCircle className="h-7 w-7 text-destructive" />
      <div>
        <p className="text-sm font-medium text-foreground">Failed to load games</p>
        <p className="mt-1 text-xs text-muted-foreground">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="h-3.5 w-3.5" />
        Retry
      </Button>
    </div>
  );
}

export default function AppPage() {
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

  const wins   = games.filter((g) => g.result === "win").length;
  const losses = games.filter((g) => g.result === "loss").length;

  return (
    <div className="mx-auto max-w-screen-lg px-6 py-8">
      <div className="mb-8 flex items-start justify-between animate-fade-in">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Scrim Library</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Find what's worth reviewing.
          </p>
          {!loading && !error && games.length > 0 && (
            <p className="mt-3 text-xs text-muted-foreground">
              {games.length} games
              <span className="mx-2 text-border" aria-hidden>·</span>
              <span className="text-win">{wins}W</span>
              <span className="mx-1.5 text-muted-foreground/40" aria-hidden>–</span>
              <span className="text-loss">{losses}L</span>
            </p>
          )}
        </div>
        {!loading && (
          <Button variant="ghost" size="sm" onClick={load} className="-mr-1 mt-0.5">
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>

      {loading && <LoadingSkeleton />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}
      {!loading && !error && games.length === 0 && (
        <div className="py-16 text-center animate-fade-in">
          <p className="text-sm font-medium text-muted-foreground">No games found</p>
          <p className="mt-1 text-xs text-muted-foreground/60">
            Make sure the backend is running and has scrim data.
          </p>
        </div>
      )}
      {!loading && !error && games.length > 0 && (
        <div className="border-t border-border">
          {games.map((game, i) => (
            <GameCard key={game.game_id} game={game} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
