"use client";

import { useMemo, useState } from "react";
import {
  ExternalLink,
  FileCheck2,
  GitCompareArrows,
  Layers,
  Search,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { ControlFamilyIcon } from "@/components/framework/ControlFamilyIcon";
import { FrameworkBadge } from "@/components/framework/FrameworkBadge";
import {
  useCrosswalk,
  useFrameworkEquivalence,
  useMappings,
  useReviewedCrosswalk,
} from "@/lib/api/hooks";

const PAGE_SIZE = 25;
const CHIP_LIMIT = 6;

function CappedChips({
  items,
  tone,
}: {
  items: string[];
  tone?: "info" | "ready";
}) {
  const hidden = items.length - CHIP_LIMIT;
  return (
    <>
      {items.slice(0, CHIP_LIMIT).map((item) => (
        <Badge tone={tone} key={item}>
          {item}
        </Badge>
      ))}
      {hidden > 0 ? (
        <Badge title={items.slice(CHIP_LIMIT).join(", ")}>+{hidden} more</Badge>
      ) : null}
    </>
  );
}

export default function CrosswalkPage() {
  const heuristic = useCrosswalk();
  const reviewed = useReviewedCrosswalk();
  const equivalence = useFrameworkEquivalence();
  const mappings = useMappings();
  const [query, setQuery] = useState("");
  const [framework, setFramework] = useState("all");
  const [page, setPage] = useState(0);

  const heuristicFrameworks = heuristic.data?.frameworks ?? [];
  const heuristicMatrix = heuristic.data?.matrix ?? [];
  const reviewedFrameworks = reviewed.data?.frameworks ?? [];
  const reviewedMatrix = reviewed.data?.matrix ?? [];
  const mappingRows = useMemo(
    () =>
      (mappings.data ?? []).flatMap((mapping) =>
        mapping.articles.map((article) => ({
          ...article,
          control_id: mapping.control_id,
          framework_id: mapping.framework_id,
        })),
      ),
    [mappings.data],
  );
  const frameworkOptions = useMemo(
    () =>
      Array.from(new Set(mappingRows.map((row) => row.framework_id))).sort(),
    [mappingRows],
  );
  const filteredRows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return mappingRows.filter((row) => {
      if (framework !== "all" && row.framework_id !== framework) return false;
      if (!needle) return true;
      return [
        row.framework_id,
        row.control_id,
        row.article_id,
        row.title,
        row.rationale,
        row.reviewed_by,
      ]
        .join(" ")
        .toLowerCase()
        .includes(needle);
    });
  }, [mappingRows, framework, query]);
  const pageCount = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const currentPage = Math.min(page, pageCount - 1);
  const pageRows = filteredRows.slice(
    currentPage * PAGE_SIZE,
    (currentPage + 1) * PAGE_SIZE,
  );
  const reviewedControlCount = new Set(mappingRows.map((row) => row.control_id))
    .size;
  const reviewedArticleCount = new Set(
    mappingRows.map((row) => `${row.framework_id}:${row.article_id}`),
  ).size;
  const equivalenceGroups = equivalence.data?.groups ?? [];

  return (
    <div className="page-shell grid gap-5">
      <PageHeader
        eyebrow="Crosswalk"
        title="Control mapping coverage"
        description="Reviewed control mappings and framework overlap."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="ready">
              <FileCheck2 className="mr-1 h-3 w-3" />{" "}
              {mappings.data?.length ?? 0} reviewed mappings
            </Badge>
            <Badge tone="info">
              <GitCompareArrows className="mr-1 h-3 w-3" />{" "}
              {equivalenceGroups.length} equivalence groups
            </Badge>
            <Badge tone="info">
              <Layers className="mr-1 h-3 w-3" /> {heuristicFrameworks.length} ×{" "}
              {heuristicFrameworks.length} heuristic
            </Badge>
          </div>
        }
      />

      <Card className="overflow-hidden border-brand/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitCompareArrows className="h-5 w-5 text-brand" />
            Cross-framework control equivalence
          </CardTitle>
          <CardDescription>
            Reviewed groups of related controls.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3">
          {equivalenceGroups.map((group) => (
            <div
              key={group.group_id}
              className="rounded-lg border border-line bg-surfaceMuted p-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <ControlFamilyIcon domain={group.risk_domain} />
                <span className="text-sm font-black text-ink">
                  {group.label}
                </span>
                <Badge tone="info">{group.risk_domain}</Badge>
                <Badge>{group.controls.length} controls</Badge>
              </div>
              <p className="mt-2 text-xs leading-5 text-muted">
                {group.rationale}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {group.controls.map((ref) => (
                  <span
                    key={ref.control_id}
                    className="inline-flex items-center gap-1 rounded-full border border-line bg-surface px-2 py-0.5 text-[11px] font-bold text-ink"
                  >
                    <FrameworkBadge
                      frameworkId={ref.framework_id}
                      fallbackLabel={ref.framework_id}
                      size={24}
                      variant="mark-only"
                    />
                    {ref.control_id}
                  </span>
                ))}
              </div>
            </div>
          ))}
          {equivalenceGroups.length === 0 && (
            <p className="text-sm text-muted">No equivalence groups loaded.</p>
          )}
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Reviewed mappings</CardTitle>
          <CardDescription>
            Signed control-to-article links that support framework overlap,
            evidence requests, and trust-center exports.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-3 rounded-lg border border-line bg-surfaceMuted p-3 lg:grid-cols-[minmax(240px,1fr)_220px_auto] lg:items-center">
            <label className="flex min-w-0 items-center gap-2 rounded-lg border border-line bg-surface px-3 py-2 text-sm">
              <Search className="h-4 w-4 text-muted" />
              <input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setPage(0);
                }}
                placeholder="Search control, article, rationale, reviewer"
                className="min-w-0 flex-1 bg-transparent text-ink outline-none placeholder:text-muted"
              />
            </label>
            <select
              aria-label="Filter crosswalk by framework"
              value={framework}
              onChange={(event) => {
                setFramework(event.target.value);
                setPage(0);
              }}
              className="h-10 rounded-lg border border-line bg-surface px-3 text-sm font-bold text-ink outline-none"
            >
              <option value="all">All frameworks</option>
              {frameworkOptions.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            <div className="flex flex-wrap gap-2 lg:justify-end">
              <Badge tone="ready">{reviewedControlCount} controls</Badge>
              <Badge tone="info">{reviewedArticleCount} articles</Badge>
              <Badge>{filteredRows.length} rows</Badge>
            </div>
          </div>

          {mappingRows.length === 0 ? (
            <div className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
              No reviewed mappings found in{" "}
              <code>mappings/control_articles.json</code>.
            </div>
          ) : filteredRows.length === 0 ? (
            <div className="rounded-lg border border-dashed border-line p-4 text-sm text-muted">
              No mappings match the current filters.
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full min-w-[960px] border-collapse text-sm">
                <thead>
                  <tr className="border-b border-line bg-surfaceMuted text-left text-[11px] font-black uppercase tracking-wide text-muted">
                    <th className="px-3 py-2">Framework</th>
                    <th className="px-3 py-2">Control</th>
                    <th className="px-3 py-2">Source article</th>
                    <th className="px-3 py-2">Why it maps</th>
                    <th className="px-3 py-2">Review</th>
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((row) => (
                    <tr
                      key={`${row.framework_id}-${row.control_id}-${row.article_id}`}
                      className="border-b border-line last:border-0"
                    >
                      <td className="px-3 py-3 align-top">
                        <FrameworkBadge
                          frameworkId={row.framework_id}
                          fallbackLabel={row.framework_id}
                          size={30}
                        />
                      </td>
                      <td className="px-3 py-3 align-top">
                        <code className="font-black text-ink">
                          {row.control_id}
                        </code>
                      </td>
                      <td className="max-w-[280px] px-3 py-3 align-top">
                        <div className="flex flex-wrap items-center gap-2">
                          <code className="font-black text-ink">
                            {row.article_id}
                          </code>
                          <Badge tone="ready">reviewed</Badge>
                        </div>
                        <div className="mt-1 text-xs leading-5 text-muted">
                          {row.title}
                        </div>
                        <a
                          href={row.official_source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex items-center gap-1 text-[11px] font-bold text-brand hover:underline"
                        >
                          official source <ExternalLink className="h-3 w-3" />
                        </a>
                      </td>
                      <td className="max-w-[360px] px-3 py-3 align-top text-xs leading-5 text-muted">
                        {row.rationale}
                      </td>
                      <td className="px-3 py-3 align-top text-xs text-muted">
                        <b className="block text-ink">{row.reviewed_by}</b>
                        {row.reviewed_at}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line bg-surfaceMuted px-3 py-2 text-xs text-muted">
                <span>
                  Showing {currentPage * PAGE_SIZE + 1}–
                  {currentPage * PAGE_SIZE + pageRows.length} of{" "}
                  {filteredRows.length} mappings
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="default"
                    aria-label="Previous page"
                    disabled={currentPage === 0}
                    onClick={() => setPage(currentPage - 1)}
                  >
                    Previous
                  </Button>
                  <span>
                    Page {currentPage + 1} of {pageCount}
                  </span>
                  <Button
                    size="sm"
                    variant="default"
                    aria-label="Next page"
                    disabled={currentPage >= pageCount - 1}
                    onClick={() => setPage(currentPage + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <details className="overflow-hidden rounded-xl border border-line bg-surface shadow-card">
        <summary className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 text-sm font-black text-ink">
          Reviewed framework overlap matrix
          <Badge tone="info">{reviewedFrameworks.length} frameworks</Badge>
        </summary>
        <div className="overflow-x-auto border-t border-line">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr>
                <th className="bg-surfaceMuted px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted">
                  Framework
                </th>
                {reviewedFrameworks.map((f) => (
                  <th
                    key={f}
                    className="border-l border-line bg-surfaceMuted px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted"
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
                  <th className="bg-surfaceMuted px-3 py-3 text-left text-xs font-black text-ink">
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
                      articles · {row.domain_count} domains
                    </div>
                  </th>
                  {row.cells.map((cell) => (
                    <td
                      key={cell.framework_id}
                      className={[
                        "border-l border-line p-3 align-top text-xs",
                        cell.is_self ? "bg-surfaceMuted" : "bg-surface",
                      ].join(" ")}
                    >
                      {cell.is_self ? (
                        <span className="text-muted">self</span>
                      ) : (
                        <div className="grid gap-2">
                          <div className="flex flex-wrap gap-1">
                            <CappedChips
                              items={cell.shared_domains}
                              tone="info"
                            />
                            <CappedChips items={cell.shared_articles} />
                            <CappedChips
                              items={cell.shared_controls}
                              tone="ready"
                            />
                            {cell.shared_domains.length === 0 &&
                              cell.shared_articles.length === 0 &&
                              cell.shared_controls.length === 0 && (
                                <span className="text-muted">none</span>
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
      </details>

      <details className="overflow-hidden rounded-xl border border-line bg-surface shadow-card">
        <summary className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 text-sm font-black text-ink">
          Heuristic domain overlap matrix
          <Badge>{heuristicFrameworks.length} frameworks</Badge>
        </summary>
        <div className="overflow-x-auto border-t border-line">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead>
              <tr>
                <th className="bg-surfaceMuted px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted">
                  Framework
                </th>
                {heuristicFrameworks.map((f) => (
                  <th
                    key={f}
                    className="border-l border-line bg-surfaceMuted px-3 py-2 text-left text-[11px] font-black uppercase tracking-wide text-muted"
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
                  <th className="bg-surfaceMuted px-3 py-3 text-left text-xs font-black text-ink">
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
                        cell.is_self ? "bg-surfaceMuted" : "bg-surface",
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
                          <CappedChips items={cell.shared_risk_domains} />
                        </div>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
