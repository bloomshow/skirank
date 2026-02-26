"use client";

import { useState, useEffect, useCallback } from "react";
import type { RankingEntry } from "../lib/types";
import { fetchRankings } from "../lib/api";
import { useAppContext } from "../context/AppContext";
import ResortCard from "./ResortCard";

const PER_PAGE = 50;

export default function RankingsList() {
  const { filters } = useAppContext();
  const [entries, setEntries] = useState<RankingEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (p: number) => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchRankings(filters, p, PER_PAGE);
        setEntries(data.results);
        setTotal(data.meta.total);
        setPage(p);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load rankings");
      } finally {
        setLoading(false);
      }
    },
    [filters]
  );

  useEffect(() => {
    load(1);
  }, [load]);

  const totalPages = Math.ceil(total / PER_PAGE);

  if (error) {
    return (
      <div className="text-center py-16 text-red-500">
        <p className="text-lg font-medium">Error loading rankings</p>
        <p className="text-sm text-slate-500 mt-1">{error}</p>
        <button
          onClick={() => load(page)}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Results count */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">
          {loading ? "Loading…" : `${total.toLocaleString()} resorts`}
        </p>
      </div>

      {/* List */}
      <div className="space-y-3">
        {loading
          ? Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="h-36 bg-slate-100 rounded-xl animate-pulse" />
            ))
          : entries.map((entry) => <ResortCard key={entry.resort.id} entry={entry} />)}
      </div>

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          <button
            disabled={page <= 1}
            onClick={() => load(page - 1)}
            className="px-4 py-2 rounded-lg border border-slate-200 text-sm disabled:opacity-40 hover:bg-slate-50 transition"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-sm text-slate-600">
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => load(page + 1)}
            className="px-4 py-2 rounded-lg border border-slate-200 text-sm disabled:opacity-40 hover:bg-slate-50 transition"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
