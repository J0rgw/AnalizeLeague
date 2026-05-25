"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  ReferenceDot,
  Tooltip,
  type TooltipProps,
} from "recharts";
import type { GameDigest, ObjectiveType, Side } from "@/types/digest";
import { formatGold, minuteFromSeconds } from "@/lib/utils";

// ────────────────────────────────────────────────────────────
// Colours per objective type
// ────────────────────────────────────────────────────────────

const OBJECTIVE_COLORS: Record<ObjectiveType, string> = {
  baron:     "#a78bfa", // violet
  dragon:    "#fb923c", // orange
  herald:    "#34d399", // emerald
  tower:     "#64748b", // slate
  inhibitor: "#8b5cf6", // purple
};

function objectiveColor(type: ObjectiveType): string {
  return OBJECTIVE_COLORS[type] ?? "#94a3b8";
}

// ────────────────────────────────────────────────────────────
// Custom tooltip
// ────────────────────────────────────────────────────────────

interface ChartEntry {
  min: number;
  diff: number;
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const diff = payload[0]?.value ?? 0;
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 text-xs shadow-lg">
      <p className="text-muted-foreground mb-0.5">Minute {label}</p>
      <p className={diff >= 0 ? "text-amber-400 font-medium" : "text-red-400 font-medium"}>
        {formatGold(diff)} gold
      </p>
    </div>
  );
}

// ────────────────────────────────────────────────────────────
// Legend dots
// ────────────────────────────────────────────────────────────

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1 text-xs text-muted-foreground">
      <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

// ────────────────────────────────────────────────────────────
// Main chart
// ────────────────────────────────────────────────────────────

interface GoldChartProps {
  digest: GameDigest;
}

export function GoldChart({ digest }: GoldChartProps) {
  const { team_gold_diff_by_min, objectives, fights, meta } = digest;

  const data: ChartEntry[] = team_gold_diff_by_min.map((diff, min) => ({
    min,
    diff,
  }));

  const lineColor = meta.side === "blue" ? "#60a5fa" : "#f87171";

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex flex-wrap gap-3 px-1">
        <LegendDot color={lineColor} label="Team gold diff" />
        <LegendDot color={OBJECTIVE_COLORS.baron}   label="Baron" />
        <LegendDot color={OBJECTIVE_COLORS.dragon}  label="Dragon" />
        <LegendDot color={OBJECTIVE_COLORS.herald}  label="Herald" />
        <LegendDot color={OBJECTIVE_COLORS.tower}   label="Tower" />
        <LegendDot color="#facc15"                  label="Fight" />
      </div>

      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 4% 13%)" vertical={false} />

          <XAxis
            dataKey="min"
            tick={{ fontSize: 10, fill: "hsl(215 13% 52%)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => `${v}m`}
            interval={4}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "hsl(215 13% 52%)" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => formatGold(v)}
            width={52}
          />

          <Tooltip content={<CustomTooltip />} />

          {/* Zero line */}
          <ReferenceLine y={0} stroke="hsl(215 13% 52%)" strokeDasharray="4 4" strokeWidth={1} />

          {/* Main line */}
          <Line
            type="monotone"
            dataKey="diff"
            stroke={lineColor}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: lineColor }}
          />

          {/* Objectives */}
          {objectives.map((obj) => {
            const min = minuteFromSeconds(obj.t);
            const y = team_gold_diff_by_min[min] ?? 0;
            const fill = objectiveColor(obj.type);
            const isOurs = obj.team === meta.side;
            return (
              <ReferenceDot
                key={`obj-${obj.t}`}
                x={min}
                y={y}
                r={5}
                fill={fill}
                stroke={isOurs ? "#fff" : "transparent"}
                strokeWidth={1.5}
              />
            );
          })}

          {/* Fights */}
          {fights.map((fight) => {
            const min = minuteFromSeconds(fight.t);
            const y = team_gold_diff_by_min[min] ?? 0;
            const isWon = fight.kills_for > fight.kills_against;
            return (
              <ReferenceDot
                key={`fight-${fight.t}`}
                x={min}
                y={y}
                r={4}
                fill={isWon ? "#facc15" : "#ef4444"}
                stroke="transparent"
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>

      <p className="text-center text-xs text-muted-foreground">
        Positive = analyzed team ({meta.side} side) ahead · Dots: objectives (outlined = ours) · Yellow/red dots: fights (won/lost)
      </p>
    </div>
  );
}
