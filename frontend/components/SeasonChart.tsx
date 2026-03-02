"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import type { DepthPoint, ForecastDay } from "../lib/types";

interface SeasonChartProps {
  depthHistory: DepthPoint[];
  forecast: ForecastDay[];
}

const POWDER_THRESHOLD = 10; // cm

export default function SeasonChart({ depthHistory, forecast }: SeasonChartProps) {
  // Build unified series: historical depth + cumulative forecast projection
  const historicalData = depthHistory.map((d) => ({
    date: d.date,
    depth: d.depth_cm,
    type: "history" as const,
    label: new Date(d.date + "T12:00:00").toLocaleDateString("en-GB", {
      month: "short",
      day: "numeric",
    }),
  }));

  // Project future depth by adding forecast snowfall cumulatively to last known depth
  const lastDepth = depthHistory.length > 0
    ? (depthHistory[depthHistory.length - 1].depth_cm ?? 0)
    : 0;

  let runningDepth = lastDepth;
  const forecastData = forecast.slice(0, 14).map((f) => {
    // Simple model: add snowfall, subtract ~2cm/day settling
    const snowfall = f.snowfall_cm ?? 0;
    runningDepth = Math.max(0, runningDepth + snowfall - 1.5);
    return {
      date: String(f.forecast_date),
      depth: Math.round(runningDepth * 10) / 10,
      snowfall: f.snowfall_cm ?? 0,
      type: "forecast" as const,
      label: new Date(String(f.forecast_date) + "T12:00:00").toLocaleDateString("en-GB", {
        month: "short",
        day: "numeric",
      }),
    };
  });

  const allData = [...historicalData, ...forecastData];

  // Find today boundary index
  const todayStr = new Date().toISOString().split("T")[0];
  const todayIndex = allData.findIndex((d) => d.date >= todayStr);

  if (allData.length === 0) {
    return <p className="text-sm text-slate-400">No depth data available.</p>;
  }

  const maxDepth = Math.max(...allData.map((d) => d.depth ?? 0), 50);

  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={allData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="depthGradientHistory" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="depthGradientForecast" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#a5b4fc" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#a5b4fc" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            interval={Math.floor(allData.length / 6)}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${v}cm`}
            domain={[0, Math.ceil(maxDepth / 50) * 50]}
            width={45}
          />
          <Tooltip
            contentStyle={{
              background: "white",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            formatter={(value: number, name: string) => [
              `${value} cm`,
              name === "depth" ? "Base depth" : name,
            ]}
            labelFormatter={(label) => label}
          />
          {todayIndex > 0 && (
            <ReferenceLine
              x={allData[todayIndex]?.label}
              stroke="#94a3b8"
              strokeDasharray="4 4"
              label={{ value: "Today", position: "top", fontSize: 10, fill: "#94a3b8" }}
            />
          )}
          <Area
            type="monotone"
            dataKey="depth"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#depthGradientHistory)"
            dot={false}
            activeDot={{ r: 4, fill: "#3b82f6" }}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
      <p className="text-xs text-slate-400 mt-1 text-center">
        Historical base depth (solid) · Projected trajectory (dashed boundary = today)
      </p>
    </div>
  );
}
