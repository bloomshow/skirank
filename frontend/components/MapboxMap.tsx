"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

interface MapResort {
  slug: string;
  name: string;
  latitude: number;
  longitude: number;
  region: string;
  score: number | null;
}

interface Props {
  resorts: MapResort[];
  token: string;
}

export default function MapboxMap({ resorts, token }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    mapboxgl.accessToken = token;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/outdoors-v12",
      center: [10, 46],
      zoom: 3,
    });
    mapRef.current = map;

    map.on("load", () => {
      map.addSource("resorts", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: resorts.map((r) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: [r.longitude, r.latitude] },
            properties: { name: r.name, slug: r.slug, score: r.score },
          })),
        },
        cluster: true,
        clusterMaxZoom: 8,
        clusterRadius: 50,
      });

      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "resorts",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": "#3b82f6",
          "circle-radius": ["step", ["get", "point_count"], 16, 10, 22, 50, 28],
          "circle-opacity": 0.8,
        },
      });

      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "resorts",
        filter: ["has", "point_count"],
        layout: {
          "text-field": "{point_count_abbreviated}",
          "text-size": 11,
          "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
        },
        paint: { "text-color": "#fff" },
      });

      map.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "resorts",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-radius": 8,
          "circle-color": [
            "interpolate", ["linear"], ["coalesce", ["get", "score"], -1],
            -1, "#94a3b8",
            40, "#ef4444",
            60, "#f97316",
            80, "#eab308",
            100, "#22c55e",
          ],
          "circle-stroke-width": 1.5,
          "circle-stroke-color": "#fff",
        },
      });

      const popup = new mapboxgl.Popup({ closeButton: false, closeOnClick: false, offset: 12 });

      map.on("mouseenter", "unclustered-point", (e) => {
        map.getCanvas().style.cursor = "pointer";
        const feature = e.features![0];
        const coords = (feature.geometry as GeoJSON.Point).coordinates.slice() as [number, number];
        const { name, score } = feature.properties as { name: string; score: number | null };
        popup
          .setLngLat(coords)
          .setHTML(`<strong>${name}</strong><br/>Score: ${score !== null ? Math.round(score) : "—"}`)
          .addTo(map);
      });

      map.on("mouseleave", "unclustered-point", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });

      map.on("click", "unclustered-point", (e) => {
        const slug = (e.features![0].properties as { slug: string }).slug;
        window.location.href = `/resort/${slug}`;
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [resorts, token]);

  return <div ref={containerRef} style={{ width: "100%", height: 560 }} className="rounded-xl overflow-hidden border border-slate-200" />;
}
