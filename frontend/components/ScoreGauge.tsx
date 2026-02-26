"use client";

interface ScoreGaugeProps {
  score: number | null;
  size?: number;
}

function scoreColor(score: number | null): string {
  if (score === null) return "#94a3b8";
  if (score >= 80) return "#22c55e";
  if (score >= 60) return "#eab308";
  if (score >= 40) return "#f97316";
  return "#ef4444";
}

export default function ScoreGauge({ score, size = 80 }: ScoreGaugeProps) {
  const radius = (size - 10) / 2;
  const circumference = Math.PI * radius; // half circle
  const pct = score !== null ? Math.min(100, Math.max(0, score)) / 100 : 0;
  const offset = circumference * (1 - pct);
  const color = scoreColor(score);

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        width={size}
        height={size / 2 + 10}
        viewBox={`0 0 ${size} ${size / 2 + 10}`}
      >
        {/* Background arc */}
        <path
          d={`M 5,${size / 2} A ${radius},${radius} 0 0,1 ${size - 5},${size / 2}`}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={8}
          strokeLinecap="round"
        />
        {/* Score arc */}
        <path
          d={`M 5,${size / 2} A ${radius},${radius} 0 0,1 ${size - 5},${size / 2}`}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text
          x={size / 2}
          y={size / 2 + 2}
          textAnchor="middle"
          fontSize={size * 0.22}
          fontWeight="bold"
          fill={color}
        >
          {score !== null ? Math.round(score) : "—"}
        </text>
      </svg>
    </div>
  );
}
