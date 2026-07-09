"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, FileKey2, PlugZap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { QueryState } from "@/components/QueryState";
import { ConnectorMark } from "@/components/connectors/ConnectorMark";
import { useConnectors } from "@/lib/api/hooks";
import type { ConnectorView } from "@/lib/api/types";

function isContractOnly(connector: ConnectorView) {
  return !connector.is_implemented;
}

export function ConnectorRegistryGapStrip({
  onSelect,
}: {
  onSelect?: (connector: ConnectorView) => void;
}) {
  const connectors = useConnectors();
  const [expanded, setExpanded] = useState(false);
  const contractOnly = useMemo(
    () =>
      (connectors.data ?? [])
        .filter(isContractOnly)
        .sort((a, b) => a.name.localeCompare(b.name)),
    [connectors.data],
  );

  if (contractOnly.length === 0) {
    return null;
  }

  const visible = expanded ? contractOnly : contractOnly.slice(0, 4);

  return (
    <QueryState queries={[connectors]} label="connector registry gap">
      <Card>
        <CardContent className="grid gap-3 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <PlugZap className="h-4 w-4 text-brand" />
                <span className="text-sm font-black text-ink">
                  Registry gap — access contracts awaiting adapters
                </span>
                <Badge tone="attention">
                  {contractOnly.length} contract-only
                </Badge>
              </div>
              <p className="mt-1 text-xs leading-5 text-muted">
                Read-only access contracts are probe-gated today; collection
                adapters ship in-repo (no runtime plugin marketplace). Test
                configuration now, enable sync when the adapter lands.
              </p>
            </div>
            {contractOnly.length > 4 ? (
              <button
                type="button"
                onClick={() => setExpanded((value) => !value)}
                className="inline-flex items-center gap-1 text-xs font-bold text-brand hover:underline"
              >
                {expanded ? "Show fewer" : `Show all ${contractOnly.length}`}
                {expanded ? (
                  <ChevronUp className="h-3.5 w-3.5" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5" />
                )}
              </button>
            ) : null}
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            {visible.map((connector) => (
              <button
                key={connector.connector_id}
                type="button"
                onClick={() => onSelect?.(connector)}
                className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)] items-start gap-3 rounded-xl border border-dashed border-amber-200/90 bg-amber-50/40 p-3 text-left transition-colors hover:border-brand hover:bg-white"
              >
                <ConnectorMark
                  connectorId={connector.connector_id}
                  name={connector.name}
                  category={connector.category}
                  size="sm"
                />
                <span className="min-w-0">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="truncate text-sm font-black text-ink">
                      {connector.name}
                    </span>
                    <Badge tone="attention">contract only</Badge>
                  </span>
                  <span className="mt-1 block text-[11px] font-bold uppercase tracking-wide text-muted">
                    {connector.category.replace(/_/g, " ")}
                  </span>
                  <span className="mt-1 line-clamp-2 text-xs leading-5 text-muted">
                    {connector.description ?? connector.setup_hint}
                  </span>
                  {connector.setup_hint ? (
                    <span className="mt-2 inline-flex items-center gap-1 text-[11px] font-bold text-brand">
                      <FileKey2 className="h-3 w-3" />
                      {connector.setup_hint}
                    </span>
                  ) : null}
                </span>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>
    </QueryState>
  );
}
