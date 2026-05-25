"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import dynamic from "next/dynamic";
import Link from "next/link";
import { ArrowLeft, AlertCircle, RefreshCw, Loader2 } from "lucide-react";
import { DraftDisplay } from "@/components/draft-display";
import { ReviewAgenda } from "@/components/review-agenda";
import { LaneStatesTable } from "@/components/lane-states-table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { getDigest, getAgenda } from "@/lib/api";
import type { GameDigest } from "@/types/digest";
import type { AgendaItem } from "@/lib/api";

// Gold chart uses recharts — client only, no SSR
const GoldChart = dynamic(
  () => import("@/components/gold-chart").then((m) => ({ default: m.GoldChart })),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[260px] w-full" />,
  }
);

// ────────────────────────────────────────────────────────────
// Loading / error states
// ────────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-44 w-full" />
      <Skeleton className="h-9 w-64" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-16 text-center">
      <AlertCircle className="h-8 w-8 text-destructive" />
      <div>
        <p className="text-sm font-medium">Failed to load game</p>
        <p className="text-xs text-muted-foreground mt-1">{message}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="h-3.5 w-3.5" />
        Retry
      </Button>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Main page
// ────────────────────────────────────────────────────────────

export default function GameDetailPage() {
  const params = useParams();
  const gameId = decodeURIComponent(params.id as string);

  const [digest, setDigest] = useState<GameDigest | null>(null);
  const [agenda, setAgenda] = useState<AgendaItem[]>([]);
  const [agendaLoading, setAgendaLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    setAgendaLoading(true);

    // Fetch digest and agenda in parallel
    Promise.all([getDigest(gameId), getAgenda(gameId)])
      .then(([d, a]) => {
        setDigest(d);
        setAgenda(a);
      })
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Unknown error")
      )
      .finally(() => {
        setLoading(false);
        setAgendaLoading(false);
      });
  };

  useEffect(() => {
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId]);

  return (
    <div className="mx-auto max-w-screen-xl px-6 py-6">
      {/* Back */}
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground mb-5"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to games
      </Link>

      {loading && <DetailSkeleton />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && digest && (
        <div className="space-y-6">
          {/* Draft header */}
          <Card>
            <CardContent className="p-5">
              <DraftDisplay digest={digest} />
            </CardContent>
          </Card>

          {/* Tabbed content */}
          <Tabs defaultValue="agenda">
            <TabsList>
              <TabsTrigger value="agenda">Review Agenda</TabsTrigger>
              <TabsTrigger value="chart">Game Shape</TabsTrigger>
              <TabsTrigger value="lanes">Lane States</TabsTrigger>
            </TabsList>

            {/* ── REVIEW AGENDA ── */}
            <TabsContent value="agenda">
              <Card>
                <CardHeader>
                  <CardTitle>Review Agenda</CardTitle>
                </CardHeader>
                <CardContent>
                  {agendaLoading ? (
                    <div className="flex items-center gap-2 py-8 justify-center text-muted-foreground text-sm">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Generating agenda…
                    </div>
                  ) : (
                    <ReviewAgenda items={agenda} />
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* ── GOLD CHART ── */}
            <TabsContent value="chart">
              <Card>
                <CardHeader>
                  <CardTitle>Team Gold Difference</CardTitle>
                </CardHeader>
                <CardContent>
                  <GoldChart digest={digest} />

                  {/* Objectives & fights summary */}
                  <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {/* Objectives */}
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
                        Objectives
                      </p>
                      <div className="space-y-1">
                        {digest.objectives.map((obj) => {
                          const min = Math.floor(obj.t / 60);
                          const sec = obj.t % 60;
                          const ts = `${min}:${sec.toString().padStart(2, "0")}`;
                          const isOurs = obj.team === digest.meta.side;
                          return (
                            <div key={obj.t} className="flex items-center gap-2 text-xs">
                              <span className="font-mono text-muted-foreground w-10">{ts}</span>
                              <span className={isOurs ? "text-foreground" : "text-muted-foreground"}>
                                {obj.type.charAt(0).toUpperCase() + obj.type.slice(1)}
                                {obj.subtype ? ` (${obj.subtype})` : ""}
                              </span>
                              <span className="text-muted-foreground">→</span>
                              <span className={isOurs ? "text-primary" : "text-destructive"}>
                                {isOurs ? "Ours" : "Theirs"}
                              </span>
                              {obj.tradeoff && (
                                <span className="text-muted-foreground italic truncate">
                                  · {obj.tradeoff}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Fights */}
                    <div>
                      <p className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
                        Fights
                      </p>
                      <div className="space-y-1">
                        {digest.fights.map((fight) => {
                          const min = Math.floor(fight.t / 60);
                          const sec = fight.t % 60;
                          const ts = `${min}:${sec.toString().padStart(2, "0")}`;
                          const won = fight.kills_for > fight.kills_against;
                          return (
                            <div key={fight.t} className="flex items-center gap-2 text-xs">
                              <span className="font-mono text-muted-foreground w-10">{ts}</span>
                              <span className="text-muted-foreground capitalize">
                                {fight.where.replace(/_/g, " ")}
                              </span>
                              <span className={won ? "text-amber-400" : "text-red-400"}>
                                {fight.kills_for}-{fight.kills_against}
                              </span>
                              {fight.led_to && (
                                <span className="text-muted-foreground italic">
                                  → {fight.led_to.replace(/_/g, " ")}
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* ── LANE STATES ── */}
            <TabsContent value="lanes">
              <Card>
                <CardHeader>
                  <CardTitle>Lane States by Checkpoint</CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <LaneStatesTable laneStates={digest.lane_states} />
                  <p className="text-xs text-muted-foreground mt-3">
                    Positive values = analyzed team ({digest.meta.side} side) ahead.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}
