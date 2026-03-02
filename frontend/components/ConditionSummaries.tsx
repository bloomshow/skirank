"use client";

import { useState } from "react";
import type { SummaryInfo } from "../lib/types";

interface ConditionSummariesProps {
  summary: SummaryInfo;
}

const TABS = [
  { key: "today" as const, label: "Today" },
  { key: "next_3d" as const, label: "3 Days" },
  { key: "next_7d" as const, label: "7 Days" },
  { key: "next_14d" as const, label: "14 Days" },
];

export default function ConditionSummaries({ summary }: ConditionSummariesProps) {
  const [active, setActive] = useState<"today" | "next_3d" | "next_7d" | "next_14d">("today");

  const text = summary[active];

  return (
    <div className="space-y-4">
      {/* Headline */}
      <p className="text-base font-semibold text-slate-800 leading-snug italic">
        &ldquo;{summary.headline}&rdquo;
      </p>

      {/* Horizon tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActive(tab.key)}
            className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors ${
              active === tab.key
                ? "bg-white text-slate-800 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Summary text */}
      <p className="text-sm text-slate-600 leading-relaxed min-h-[4rem]">{text}</p>

      <p className="text-xs text-slate-400">
        AI summary · Generated {new Date(summary.generated_at).toLocaleDateString("en-GB", {
          day: "numeric", month: "short", year: "numeric",
        })} · Powered by Claude
      </p>
    </div>
  );
}
