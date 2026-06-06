"use client";

import { Search } from "lucide-react";
import type { Severity } from "@/lib/api/types";

export interface ToolbarFilters {
  query: string;
  framework: string;
  severity: Severity | "all";
}

interface Props {
  filters: ToolbarFilters;
  frameworks: string[];
  onChange: (next: ToolbarFilters) => void;
  placeholder?: string;
}

const SEVERITIES: Array<Severity | "all"> = [
  "all",
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

export function Toolbar({ filters, frameworks, onChange, placeholder }: Props) {
  return (
    <div className="grid min-w-0 gap-2 rounded-xl border border-line bg-white p-2.5 shadow-card md:grid-cols-[minmax(180px,1fr)_minmax(140px,180px)_minmax(130px,170px)]">
      <div className="relative min-w-0">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          value={filters.query}
          onChange={(e) => onChange({ ...filters, query: e.target.value })}
          placeholder={placeholder ?? "Search controls, assets, evidence…"}
          className="w-full rounded-lg border border-line bg-white py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-brand"
        />
      </div>
      <select
        value={filters.framework}
        onChange={(e) => onChange({ ...filters, framework: e.target.value })}
        className="min-w-0 rounded-lg border border-line bg-white px-3 py-2 text-sm font-extrabold focus:outline-none focus:ring-1 focus:ring-brand"
      >
        <option value="all">All frameworks</option>
        {frameworks.map((f) => (
          <option key={f} value={f}>
            {f}
          </option>
        ))}
      </select>
      <select
        value={filters.severity}
        onChange={(e) =>
          onChange({
            ...filters,
            severity: e.target.value as ToolbarFilters["severity"],
          })
        }
        className="min-w-0 rounded-lg border border-line bg-white px-3 py-2 text-sm font-extrabold focus:outline-none focus:ring-1 focus:ring-brand"
      >
        {SEVERITIES.map((s) => (
          <option key={s} value={s}>
            {s === "all" ? "All severities" : s}
          </option>
        ))}
      </select>
    </div>
  );
}

export function matchesQuery<T extends object>(row: T, query: string): boolean {
  if (!query) return true;
  return JSON.stringify(row).toLowerCase().includes(query.toLowerCase());
}
