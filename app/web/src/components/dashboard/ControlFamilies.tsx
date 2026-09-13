"use client";

import Link from "next/link";
import { useFrameworkEquivalence } from "@/lib/api/hooks";
import { CollapsibleCard } from "@/components/ui/collapsible-card";
import {
  ControlFamilyIcon,
  controlFamily,
} from "@/components/framework/ControlFamilyIcon";
import { frameworkDetailHref } from "@/lib/framework-links";

export function ControlFamilies({ embedded = false }: { embedded?: boolean }) {
  const query = useFrameworkEquivalence();
  const groups = query.data?.groups ?? [];
  const domains = [...new Set(groups.map((group) => group.risk_domain))].sort();
  return (
    <CollapsibleCard
      embedded={embedded}
      title="Control families"
      storageKey="dashboard-control-families"
      defaultOpen={false}
      description={`${domains.length} families · ${groups.length} mapping groups`}
      contentClassName="max-h-[360px] overflow-y-auto px-5 py-2"
    >
      {query.isError ? (
        <p className="py-3 text-sm text-muted">
          Unable to load control mappings.
        </p>
      ) : query.isPending ? (
        <p className="py-3 text-sm text-muted">Loading control mappings…</p>
      ) : (
        <div className="grid gap-x-8 2xl:grid-cols-2">
          {domains.map((domain) => {
            const members = groups.filter(
              (group) => group.risk_domain === domain,
            );
            const controls = new Set(
              members.flatMap((group) =>
                group.controls.map((control) => control.control_id),
              ),
            );
            return (
              <details
                key={domain}
                className="min-w-0 border-b border-line py-3"
              >
                <summary className="flex cursor-pointer items-center gap-3 rounded focus-visible:outline-brand">
                  <ControlFamilyIcon domain={domain} />
                  <span className="min-w-0 flex-1 text-sm font-semibold text-ink">
                    {controlFamily(domain).label}
                    <span className="mt-0.5 block text-xs font-normal text-muted">
                      {controls.size} mapped controls
                    </span>
                  </span>
                  <span className="text-xs text-muted">Expand</span>
                </summary>
                <div className="space-y-3 py-3 pl-12">
                  {members.map((group) => (
                    <div key={group.group_id}>
                      <div className="text-xs font-semibold text-ink">
                        {group.label}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {group.controls.map((control) => (
                          <Link
                            key={control.control_id}
                            href={frameworkDetailHref(
                              control.framework_id,
                              control.control_id,
                            )}
                            className="text-xs text-brand hover:underline"
                          >
                            {control.control_id}
                          </Link>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </details>
            );
          })}
        </div>
      )}
    </CollapsibleCard>
  );
}
