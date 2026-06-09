"use client";

import { useMemo, useState } from "react";
import type { ToolbarFilters } from "@/components/Toolbar";

const initial: ToolbarFilters = {
  query: "",
  framework: "all",
  severity: "all",
  freshness: "all",
};

export function useToolbar() {
  const [filters, setFilters] = useState<ToolbarFilters>(initial);
  return useMemo(() => ({ filters, setFilters }), [filters]);
}
