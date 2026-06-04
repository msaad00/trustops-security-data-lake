"use client";

import { ExternalLink, FileCheck2, Layers } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import {
  useCrosswalk,
  useMappings,
  useReviewedCrosswalk,
} from "@/lib/api/hooks";

export default function CrosswalkPage() {
  const heuristic = useCrosswalk();
  const reviewed = useReviewedCrosswalk();
  const mappings = useMappings();

  const heuristicFrameworks = heuristic.data?.frameworks ?? [];
  const heuristicMatrix = heuristic.data?.matrix ?? [];
  const reviewedFrameworks = reviewed.data?.frameworks ?? [];
  const reviewedMatrix = reviewed.data?.matrix ?? [];

  return (
    <div className="grid min-w-0 gap-5 px-4 py-5 sm:px-5 lg:px-7">
      <PageHeader
        eyebrow="Crosswalk"
        title="Framework cross-mapping"
        description="Reviewed control_id ↔ source-article mappings live above. The heuristic shared-domain matrices below are the safety net when reviewed mappings are missing — every framework should aim for reviewed coverage."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="ready">
              <FileCheck2 className="mr-1 h-3 w-3" />{" "}
              {mappings.data?.length ?? 0} reviewed mappings
            </Badge>
            <Badge tone="info">
              <Layers className="mr-1 h-3 w-3" /> {heuristicFrameworks.length} ×{" "}
              {heuristicFrameworks.length} heuristic
            </Badge>
          </div>
        }
      />

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Reviewed control → article mappings</CardTitle>
          <CardDescription>
            Auditor-signed mappings from local <code>control_id</code> to the
            framework's official-source article. Click the source link to verify
            the article text at the regulator.
          </CardDescription>
        </CardHeader>
        <div className="grid gap-2 p-5 pt-0">
          {(mappings.data ?? []).length === 0 && (
            <div className="rounded-lg border border-dashed border-line p-3 text-xs text-muted">
              No reviewed mappings yet. Add records to{" "}
              <code>mappings/control_articles.json</code>.
            </div>
          )}
          {(mappings.data ?? []).map((mapping) =>
            mapping.articles.map((article) => (
              <div
                key={`${mapping.control_id}-${article.article_id}`}
                className="grid grid-cols-[auto_minmax(0,1fr)_minmax(0,1fr)] items-start gap-4 rounded-xl border border-line bg-white p-3 text-sm"
              >
                <FrameworkBadge
                  frameworkId={mapping.framework_id}
                  fallbackLabel={mapping.framework_id}
                  size={36}
                />
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="font-black text-ink">
                      {mapping.control_id}
                    </code>
                    <Badge>{mapping.framework_id}</Badge>
                  </div>
                  <div className="mt-1 text-xs text-muted">
                    {article.rationale}
                  </div>
                  <div className="mt-1 text-[10px] text-muted">
                    reviewed by{" "}
                    <b className="text-ink">{article.reviewed_by}</b> at{" "}
                    {article.reviewed_at}
                  </div>
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="font-black text-ink">
                      {article.article_id}
                    </code>
                    <Badge tone="ready">reviewed</Badge>
                  </div>
                  <div className="mt-1 truncate text-xs text-muted">
                    {article.title}
                  </div>
                  <a
                    href={article.official_source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-1 inline-flex items-center gap-1 text-[11px] text-brand hover:underline"
                  >
                    official source <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </div>
            )),
          )}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Reviewed framework × framework</CardTitle>
          <CardDescription>
            Cells list articles + controls shared between mapping tables.
            Diagonal is self.
          </CardDescription>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="min-w-[720px] w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="bg-slate-50 px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted">
                  Framework
                </th>
                {reviewedFrameworks.map((f) => (
                  <th
                    key={f}
                    className="border-l border-line bg-slate-50 px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted"
                  >
                    <span className="inline-flex items-center gap-1.5">
                      <FrameworkBadge
                        frameworkId={f}
                        fallbackLabel={f}
                        size={20}
                      />
                      {f}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reviewedMatrix.map((row) => (
                <tr key={row.framework_id} className="border-t border-line">
                  <th className="bg-slate-50 px-3 py-3 text-left text-xs font-black text-ink">
                    <span className="inline-flex items-center gap-1.5">
                      <FrameworkBadge
                        frameworkId={row.framework_id}
                        fallbackLabel={row.framework_id}
                        size={20}
                      />
                      {row.framework_id}
                    </span>
                    <div className="text-[10px] font-normal text-muted">
                      {row.mapping_count} mappings · {row.article_count}{" "}
                      articles
                    </div>
                  </th>
                  {row.cells.map((cell) => (
                    <td
                      key={cell.framework_id}
                      className={[
                        "border-l border-line p-3 align-top text-xs",
                        cell.is_self ? "bg-slate-100" : "bg-white",
                      ].join(" ")}
                    >
                      {cell.is_self ? (
                        <span className="text-muted">— self —</span>
                      ) : (
                        <div className="grid gap-2">
                          <div>
                            <div className="text-[10px] font-black uppercase tracking-wide text-muted">
                              articles
                            </div>
                            {cell.shared_articles.length === 0 ? (
                              <span className="text-muted">
                                no shared articles
                              </span>
                            ) : (
                              <div className="flex flex-wrap gap-1">
                                {cell.shared_articles.map((a) => (
                                  <Badge key={a}>{a}</Badge>
                                ))}
                              </div>
                            )}
                          </div>
                          <div>
                            <div className="text-[10px] font-black uppercase tracking-wide text-muted">
                              controls
                            </div>
                            {cell.shared_controls.length === 0 ? (
                              <span className="text-muted">
                                no shared controls
                              </span>
                            ) : (
                              <div className="flex flex-wrap gap-1">
                                {cell.shared_controls.map((c) => (
                                  <Badge tone="ready" key={c}>
                                    {c}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Heuristic safety net · shared risk domains</CardTitle>
          <CardDescription>
            Computed from the local control catalog (<code>risk_domain</code> +{" "}
            <code>owner</code>) when reviewed mappings are absent. Useful for
            sketching new framework support before reviewers sign off.
          </CardDescription>
        </CardHeader>
        <div className="overflow-x-auto">
          <table className="min-w-[720px] w-full border-collapse text-sm">
            <thead>
              <tr>
                <th className="bg-slate-50 px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted">
                  Framework
                </th>
                {heuristicFrameworks.map((f) => (
                  <th
                    key={f}
                    className="border-l border-line bg-slate-50 px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted"
                  >
                    <span className="inline-flex items-center gap-1.5">
                      <FrameworkBadge
                        frameworkId={f}
                        fallbackLabel={f}
                        size={20}
                      />
                      {f}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {heuristicMatrix.map((row) => (
                <tr key={row.framework_id} className="border-t border-line">
                  <th className="bg-slate-50 px-3 py-3 text-left text-xs font-black text-ink">
                    <span className="inline-flex items-center gap-1.5">
                      <FrameworkBadge
                        frameworkId={row.framework_id}
                        fallbackLabel={row.framework_id}
                        size={20}
                      />
                      {row.framework_id}
                    </span>
                  </th>
                  {row.cells.map((cell) => (
                    <td
                      key={cell.framework_id}
                      className={[
                        "border-l border-line p-3 align-top text-xs",
                        cell.is_self ? "bg-slate-100" : "bg-white",
                      ].join(" ")}
                    >
                      {cell.is_self ? (
                        <span className="text-muted">— self —</span>
                      ) : cell.shared_risk_domains.length === 0 ? (
                        <span className="text-muted">
                          no shared risk domains
                        </span>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {cell.shared_risk_domains.map((d) => (
                            <Badge key={d}>{d}</Badge>
                          ))}
                        </div>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
