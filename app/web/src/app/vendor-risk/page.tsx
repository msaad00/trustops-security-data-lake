"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/PageHeader";
import { QueryState } from "@/components/QueryState";
import {
  useCreateVendorAssessmentMutation,
  useSubmitVendorAssessmentMutation,
  useUpdateVendorAssessmentMutation,
  useVendorAssessment,
  useVendorAssessments,
  useVendorQuestionnaires,
} from "@/lib/api/hooks";
import type {
  VendorAnswer,
  VendorAssessment,
  VendorAssessmentStatus,
  VendorQuestionnaireQuestion,
  VendorRiskLevel,
} from "@/lib/api/types";

const inputClass =
  "rounded-lg border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-brand";

const STATUS_TONE: Record<
  VendorAssessmentStatus,
  "default" | "info" | "ready" | "attention" | "critical"
> = {
  draft: "default",
  in_review: "info",
  completed: "ready",
  rejected: "critical",
};

const RISK_TONE: Record<
  VendorRiskLevel,
  "default" | "ready" | "attention" | "critical"
> = {
  low: "ready",
  medium: "attention",
  high: "attention",
  critical: "critical",
};

const ANSWERS: VendorAnswer[] = ["yes", "partial", "no", "na"];

function fmtDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString();
}

function responseAnswer(
  responses: VendorAssessment["responses"],
  questionId: string,
): VendorAnswer | "" {
  const raw = responses[questionId];
  if (typeof raw === "string") return raw as VendorAnswer;
  if (raw && typeof raw === "object" && "answer" in raw) {
    return (raw.answer as VendorAnswer) || "";
  }
  return "";
}

function CreateAssessmentForm({
  defaultTemplateId,
}: {
  defaultTemplateId: string;
}) {
  const create = useCreateVendorAssessmentMutation();
  const [vendorName, setVendorName] = useState("");
  const [templateId, setTemplateId] = useState(defaultTemplateId);
  const [owner, setOwner] = useState("");

  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (!vendorName.trim() || !templateId) return;
        create.mutate(
          {
            vendor_name: vendorName.trim(),
            template_id: templateId,
            owner: owner.trim(),
          },
          {
            onSuccess: () => {
              setVendorName("");
              setOwner("");
            },
          },
        );
      }}
    >
      <label className="flex flex-col gap-1 text-xs text-muted">
        Vendor name
        <input
          className={inputClass}
          value={vendorName}
          onChange={(e) => setVendorName(e.target.value)}
          placeholder="Acme SaaS"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Template
        <input
          className={inputClass}
          value={templateId}
          onChange={(e) => setTemplateId(e.target.value)}
          placeholder="soc2-vendor-standard"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-muted">
        Owner (optional)
        <input
          className={inputClass}
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
          placeholder="security@company.com"
        />
      </label>
      <Button type="submit" variant="primary" disabled={create.isPending}>
        {create.isPending ? "Creating…" : "New assessment"}
      </Button>
    </form>
  );
}

function QuestionRow({
  question,
  value,
  disabled,
  onChange,
}: {
  question: VendorQuestionnaireQuestion;
  value: VendorAnswer | "";
  disabled: boolean;
  onChange: (answer: VendorAnswer) => void;
}) {
  return (
    <div className="space-y-2 rounded-lg border border-line px-3 py-3 text-sm">
      <p className="font-medium text-ink">
        {question.prompt}
        {question.required ? (
          <span className="ml-1 text-critical">*</span>
        ) : null}
      </p>
      <div className="flex flex-wrap gap-2">
        {ANSWERS.map((answer) => {
          if (answer === "na" && question.required) return null;
          const selected = value === answer;
          return (
            <button
              key={answer}
              type="button"
              disabled={disabled}
              onClick={() => onChange(answer)}
              className={`rounded-full border px-3 py-1 text-xs capitalize transition ${
                selected
                  ? "border-brand bg-brand/10 text-brand"
                  : "border-line text-muted hover:border-brand/40"
              }`}
            >
              {answer}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function AssessmentDetail({ assessmentId }: { assessmentId: string }) {
  const detail = useVendorAssessment(assessmentId);
  const update = useUpdateVendorAssessmentMutation(assessmentId);
  const submit = useSubmitVendorAssessmentMutation();
  const assessment = detail.data;
  const [draftResponses, setDraftResponses] = useState<
    Record<string, VendorAnswer>
  >({});

  const questions = useMemo(() => {
    const sections = assessment?.template?.sections ?? [];
    return sections.flatMap((section) =>
      (section.questions ?? []).map((q) => ({
        ...q,
        section_title: section.title,
      })),
    );
  }, [assessment?.template?.sections]);

  if (!assessment) {
    return <Card className="p-5 text-sm text-muted">Loading assessment…</Card>;
  }

  const locked = assessment.status === "completed";
  const responses = { ...assessment.responses };
  for (const [qid, answer] of Object.entries(draftResponses)) {
    responses[qid] = { answer };
  }

  return (
    <Card className="space-y-4 p-5">
      <CardHeader className="p-0">
        <CardTitle className="flex flex-wrap items-center gap-2">
          {assessment.vendor_name}
          <Badge tone={STATUS_TONE[assessment.status]}>
            {assessment.status}
          </Badge>
          {assessment.risk_level ? (
            <Badge tone={RISK_TONE[assessment.risk_level]}>
              {assessment.risk_level} risk
            </Badge>
          ) : null}
          {assessment.score != null ? (
            <span className="text-sm font-normal text-muted">
              Score {assessment.score}
            </span>
          ) : null}
        </CardTitle>
      </CardHeader>
      <p className="text-xs text-muted">
        Template {assessment.template_id} · due {fmtDate(assessment.due_at)} ·
        updated {fmtDate(assessment.updated_at)}
      </p>

      {questions.length ? (
        <div className="space-y-3">
          {questions.map((question) => (
            <QuestionRow
              key={question.question_id}
              question={question}
              value={
                draftResponses[question.question_id] ??
                responseAnswer(responses, question.question_id)
              }
              disabled={locked || update.isPending}
              onChange={(answer) =>
                setDraftResponses((prev) => ({
                  ...prev,
                  [question.question_id]: answer,
                }))
              }
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">Questionnaire template not loaded.</p>
      )}

      {!locked ? (
        <div className="flex flex-wrap gap-2">
          <Button
            variant="default"
            disabled={update.isPending || !Object.keys(draftResponses).length}
            onClick={() => {
              const payload: Record<string, { answer: string }> = {};
              for (const [qid, answer] of Object.entries(draftResponses)) {
                payload[qid] = { answer };
              }
              update.mutate(
                { responses: payload, status: "in_review" },
                { onSuccess: () => setDraftResponses({}) },
              );
            }}
          >
            {update.isPending ? "Saving…" : "Save responses"}
          </Button>
          <Button
            variant="primary"
            disabled={submit.isPending}
            onClick={() => submit.mutate(assessmentId)}
          >
            {submit.isPending ? "Scoring…" : "Submit & score"}
          </Button>
        </div>
      ) : null}
    </Card>
  );
}

function AssessmentRow({
  assessment,
  selected,
  onSelect,
}: {
  assessment: VendorAssessment;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-lg border px-3 py-3 text-left text-sm transition ${
        selected
          ? "border-brand bg-brand/5"
          : "border-line hover:border-brand/30"
      }`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-medium text-ink">{assessment.vendor_name}</span>
        <div className="flex flex-wrap gap-2">
          <Badge tone={STATUS_TONE[assessment.status]}>
            {assessment.status}
          </Badge>
          {assessment.risk_level ? (
            <Badge tone={RISK_TONE[assessment.risk_level]}>
              {assessment.risk_level}
            </Badge>
          ) : null}
        </div>
      </div>
      <p className="mt-1 text-xs text-muted">
        {assessment.template_id}
        {assessment.score != null ? ` · score ${assessment.score}` : ""}
      </p>
    </button>
  );
}

export default function VendorRiskPage() {
  const templates = useVendorQuestionnaires();
  const assessments = useVendorAssessments();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const defaultTemplateId =
    templates.data?.[0]?.template_id ?? "soc2-vendor-standard";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Third-party risk"
        title="Vendor risk questionnaires"
        description="Run standardized vendor diligence questionnaires, capture yes/partial/no answers, and score third-party readiness against SOC 2 vendor-risk controls."
      />

      <QueryState queries={[templates, assessments]} label="vendor risk">
        <Card className="p-5">
          <CardHeader className="p-0">
            <CardTitle>Questionnaire templates</CardTitle>
          </CardHeader>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {templates.data?.map((template) => (
              <div
                key={template.template_id}
                className="rounded-lg border border-line px-3 py-2 text-sm"
              >
                <p className="font-medium text-ink">{template.name}</p>
                <p className="text-xs text-muted">
                  {template.template_id} · {template.question_count} questions
                </p>
              </div>
            )) ?? <p className="text-sm text-muted">Loading templates…</p>}
          </div>
        </Card>

        <Card className="p-5">
          <CardHeader className="p-0">
            <CardTitle>New vendor assessment</CardTitle>
          </CardHeader>
          <div className="mt-3">
            <CreateAssessmentForm defaultTemplateId={defaultTemplateId} />
          </div>
        </Card>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="space-y-2">
            {assessments.data?.length ? (
              assessments.data.map((row) => (
                <AssessmentRow
                  key={row.id}
                  assessment={row}
                  selected={row.id === selectedId}
                  onSelect={() => setSelectedId(row.id)}
                />
              ))
            ) : (
              <p className="text-sm text-muted">No vendor assessments yet.</p>
            )}
          </div>
          <div>
            {selectedId ? (
              <AssessmentDetail assessmentId={selectedId} />
            ) : (
              <Card className="p-5 text-sm text-muted">
                Select an assessment to answer its questionnaire.
              </Card>
            )}
          </div>
        </div>
      </QueryState>
    </div>
  );
}
