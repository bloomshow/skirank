"use client";

import dynamic from "next/dynamic";

const MapboxMap = dynamic(() => import("./MapboxMap"), {
  ssr: false,
  loading: () => (
    <div
      className="w-full rounded-xl border border-slate-200 bg-slate-100 animate-pulse"
      style={{ height: 560 }}
    />
  ),
});

interface MapResort {
  slug: string;
  name: string;
  latitude: number;
  longitude: number;
  region: string;
  score: number | null;
}

interface MapViewProps {
  resorts: MapResort[];
}

export default function MapView({ resorts }: MapViewProps) {
  const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? "";

  if (!token) {
    return (
      <div
        className="w-full rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-center text-slate-400 text-sm"
        style={{ height: 560 }}
      >
        Set NEXT_PUBLIC_MAPBOX_TOKEN in .env to enable the map.
      </div>
    );
  }

  return <MapboxMap resorts={resorts} token={token} />;
}
