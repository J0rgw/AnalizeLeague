import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, formatGold } from "@/lib/utils";
import type { LaneState, Lane } from "@/types/digest";

const LANES: Lane[] = ["top", "jng", "mid", "bot", "sup"];
const LANE_LABELS: Record<Lane, string> = {
  top: "Top",
  jng: "Jungle",
  mid: "Mid",
  bot: "Bot",
  sup: "Support",
};

function DiffCell({ value, unit = "g" }: { value: number; unit?: string }) {
  const color =
    value > 0 ? "text-amber-400" : value < 0 ? "text-red-400" : "text-muted-foreground";
  const sign = value > 0 ? "+" : "";
  return (
    <span className={cn("font-mono text-xs", color)}>
      {sign}
      {unit === "g" && Math.abs(value) >= 1000
        ? formatGold(value)
        : `${sign}${value}`}
    </span>
  );
}

interface LaneStatesTableProps {
  laneStates: LaneState[];
}

export function LaneStatesTable({ laneStates }: LaneStatesTableProps) {
  // Get available time snapshots, sorted
  const checkpoints = Array.from(new Set(laneStates.map((ls) => ls.at_min))).sort(
    (a, b) => a - b
  );

  // Index: lane → at_min → LaneState
  const index: Record<string, Record<number, LaneState>> = {};
  for (const ls of laneStates) {
    if (!index[ls.lane]) index[ls.lane] = {};
    index[ls.lane][ls.at_min] = ls;
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-20">Lane</TableHead>
          {checkpoints.map((min) => (
            <TableHead key={min} colSpan={3} className="text-center border-l border-border">
              Min {min}
            </TableHead>
          ))}
        </TableRow>
        <TableRow>
          <TableHead />
          {checkpoints.map((min) => (
            <React.Fragment key={min}>
              <TableHead className="text-right border-l border-border text-muted-foreground/70">
                Gold
              </TableHead>
              <TableHead className="text-right text-muted-foreground/70">CS</TableHead>
              <TableHead className="text-right text-muted-foreground/70">XP</TableHead>
            </React.Fragment>
          ))}
        </TableRow>
      </TableHeader>

      <TableBody>
        {LANES.map((lane) => (
          <TableRow key={lane}>
            <TableCell className="font-medium text-xs">{LANE_LABELS[lane]}</TableCell>
            {checkpoints.map((min) => {
              const ls = index[lane]?.[min];
              if (!ls) {
                return (
                  <React.Fragment key={min}>
                    <TableCell className="border-l border-border text-center text-muted-foreground">—</TableCell>
                    <TableCell className="text-center text-muted-foreground">—</TableCell>
                    <TableCell className="text-center text-muted-foreground">—</TableCell>
                  </React.Fragment>
                );
              }
              return (
                <React.Fragment key={min}>
                  <TableCell className="text-right border-l border-border">
                    <DiffCell value={ls.gold_diff} unit="g" />
                  </TableCell>
                  <TableCell className="text-right">
                    <DiffCell value={ls.cs_diff} unit="cs" />
                  </TableCell>
                  <TableCell className="text-right">
                    <DiffCell value={ls.xp_diff} unit="xp" />
                  </TableCell>
                </React.Fragment>
              );
            })}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
