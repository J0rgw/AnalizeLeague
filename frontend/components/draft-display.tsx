import { Badge } from "@/components/ui/badge";
import { cn, formatDuration } from "@/lib/utils";
import type { GameDigest, DraftSide } from "@/types/digest";

const ROLE_LABELS: Record<string, string> = {
  top: "TOP",
  jng: "JNG",
  mid: "MID",
  bot: "BOT",
  sup: "SUP",
};

const ROLES = ["top", "jng", "mid", "bot", "sup"] as const;

interface DraftSideProps {
  label: string;
  champions: DraftSide;
  bans: string[];
  isAnalyzed: boolean;
  result?: "win" | "loss";
}

function DraftSidePanel({ label, champions, bans, isAnalyzed, result }: DraftSideProps) {
  const sideClass = label === "BLUE" ? "side-blue" : "side-red";
  const borderClass = label === "BLUE" ? "border-blue-500/20" : "border-red-500/20";

  return (
    <div className={cn("rounded-lg border p-4 flex-1", borderClass)}>
      <div className="flex items-center justify-between mb-3">
        <span className={cn("text-xs font-bold tracking-widest", sideClass)}>
          {label} SIDE
        </span>
        {isAnalyzed && (
          result ? (
            <Badge variant={result === "win" ? "win" : "loss"}>
              {result === "win" ? "WIN" : "LOSS"}
            </Badge>
          ) : (
            <span className="text-xs text-muted-foreground">ANALYZED</span>
          )
        )}
      </div>

      {/* Champions */}
      <div className="space-y-1.5">
        {ROLES.map((role) => (
          <div key={role} className="flex items-center gap-2">
            <span className="w-8 text-xs font-mono text-muted-foreground">
              {ROLE_LABELS[role]}
            </span>
            <span className="text-sm font-medium text-foreground">
              {champions[role]}
            </span>
          </div>
        ))}
      </div>

      {/* Bans */}
      <div className="mt-3 pt-3 border-t border-border">
        <p className="text-xs text-muted-foreground mb-1.5">BANS</p>
        <div className="flex flex-wrap gap-1">
          {bans.map((ban, i) => (
            <span
              key={i}
              className="rounded px-1.5 py-0.5 text-xs bg-muted text-muted-foreground line-through"
            >
              {ban}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

interface DraftDisplayProps {
  digest: GameDigest;
}

export function DraftDisplay({ digest }: DraftDisplayProps) {
  const { meta, draft } = digest;

  return (
    <div className="space-y-3">
      {/* Game metadata strip */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span className="font-mono">{meta.game_id}</span>
        <span>·</span>
        <span>Patch {meta.patch}</span>
        <span>·</span>
        <span>{formatDuration(meta.duration_s)}</span>
        <span>·</span>
        <span className={meta.side === "blue" ? "side-blue" : "side-red"}>
          {meta.side.charAt(0).toUpperCase() + meta.side.slice(1)} side
        </span>
      </div>

      {/* Draft panels */}
      <div className="flex gap-4">
        <DraftSidePanel
          label="BLUE"
          champions={draft.blue}
          bans={draft.bans.blue}
          isAnalyzed={meta.side === "blue"}
          result={meta.side === "blue" ? meta.result : undefined}
        />

        {/* VS divider */}
        <div className="flex flex-col items-center justify-center gap-1 px-2">
          <div className="h-full w-px bg-border" />
          <span className="text-xs font-bold text-muted-foreground bg-background px-1">VS</span>
          <div className="h-full w-px bg-border" />
        </div>

        <DraftSidePanel
          label="RED"
          champions={draft.red}
          bans={draft.bans.red}
          isAnalyzed={meta.side === "red"}
          result={meta.side === "red" ? meta.result : undefined}
        />
      </div>
    </div>
  );
}
