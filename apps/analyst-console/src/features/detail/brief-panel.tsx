import { useEffect, useMemo, useState } from "react";

import { cn } from "@/lib/cn";
import type {
  CountryMonitorRecord,
  CouncilAnalysisEvent,
  QueueItem,
} from "@/lib/domain/types";

type BriefPanelProps = {
  item: QueueItem | null;
  loadError?: string | null;
  analysis?: CouncilAnalysisEvent | null;
  countryBrief?: CountryMonitorRecord | null;
};

function formatBriefDate(value?: string | null): string {
  if (!value) {
    return "Undated";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function getPreviewText(item: QueueItem): string {
  const summary = item.summary?.trim();

  if (summary) {
    return summary;
  }

  const reportDescription = item.provenance?.linked_reports?.find(
    (report) => report.description?.trim(),
  )?.description;

  if (reportDescription?.trim()) {
    return reportDescription.trim();
  }

  const parts = [item.source_primary, item.publication_reason]
    .map((value) => value?.replaceAll("_", " ").trim())
    .filter(Boolean);

  return parts.join(" · ") || "No event brief is recorded for this queue item yet.";
}

function formatStageLabel(value?: string | null): string | null {
  if (!value) {
    return null;
  }

  return value.replaceAll("_", " ");
}

function getAnalysisSummary(
  analysis?: CouncilAnalysisEvent | null,
): string | null {
  const firstLens = Object.values(analysis?.analyses ?? {}).find(
    (lens) => lens?.public_analysis || lens?.assessment,
  );

  return firstLens?.public_analysis ?? firstLens?.assessment ?? null;
}

export function BriefPanel({
  item,
  loadError = null,
  analysis = null,
  countryBrief = null,
}: BriefPanelProps) {
  const [showEvidence, setShowEvidence] = useState(false);

  useEffect(() => {
    setShowEvidence(false);
  }, [item?.event_id]);

  const linkedReports = item?.provenance?.linked_reports ?? [];
  const previewText = useMemo(() => (item ? getPreviewText(item) : ""), [item]);
  const analysisSummary = useMemo(() => getAnalysisSummary(analysis), [analysis]);

  if (loadError) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Event brief
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          Brief unavailable while the review queue failed to load.
        </p>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Event brief
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          No visible queue item selected.
        </p>
      </div>
    );
  }

  const evidenceId = `brief-evidence-${item.event_id}`;
  const priorityTone =
    item.review_priority === "high"
      ? "border-[var(--console-danger)]/40 bg-[var(--console-danger)]/12 text-[var(--console-danger)]"
      : item.review_priority === "medium"
        ? "border-[var(--console-warn)]/40 bg-[var(--console-warn)]/12 text-[var(--console-warn)]"
        : "border-[var(--console-success)]/35 bg-[var(--console-success)]/10 text-[var(--console-success)]";
  const salienceTone =
    item.salience === "high"
      ? "border-[var(--console-danger)]/40 bg-[var(--console-danger)]/12 text-[var(--console-danger)]"
      : item.salience === "medium"
        ? "border-[var(--console-warn)]/40 bg-[var(--console-warn)]/12 text-[var(--console-warn)]"
        : "border-[var(--console-success)]/35 bg-[var(--console-success)]/10 text-[var(--console-success)]";
  const confidenceTone =
    item.confidence === "low"
      ? "border-[var(--console-danger)]/40 bg-[var(--console-danger)]/12 text-[var(--console-danger)]"
      : item.confidence === "medium"
        ? "border-[var(--console-warn)]/40 bg-[var(--console-warn)]/12 text-[var(--console-warn)]"
        : "border-[var(--console-success)]/35 bg-[var(--console-success)]/10 text-[var(--console-success)]";
  const eventDateLabel = formatBriefDate(item.event_date);
  const sourceCount = linkedReports.length || (item.source_primary ? 1 : 0);
  const latestTimelineEntry =
    item.provenance?.timeline?.find((entry) => entry.label || entry.stage || entry.status) ??
    null;
  const countryRisk =
    countryBrief?.predictive_summary ?? countryBrief?.public_summary ?? null;
  const watchpoints =
    countryRisk?.watchpoints?.slice(0, 2) ??
    (countryBrief?.public_context?.country_watch
      ? [countryBrief.public_context.country_watch]
      : []);

  return (
    <div className="flex h-full min-h-0 flex-col p-3.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            <span>{item.country || "Regional"}</span>
            <span className="text-[var(--console-line-strong)]">/</span>
            <span>{eventDateLabel}</span>
          </div>
          <h2 className="mt-1.5 text-[19px] font-semibold leading-8 text-[var(--console-ink)]">
            {item.headline}
          </h2>
        </div>
        <div
          className={cn(
            "shrink-0 rounded-lg border px-3 py-2 text-right",
            priorityTone,
          )}
        >
          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Priority
          </div>
          <div className="mt-1 text-sm font-semibold">
            {item.review_priority}
          </div>
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-2 gap-2.5 text-sm xl:grid-cols-4">
        <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
          <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Event
          </dt>
          <dd className="mt-1 text-[var(--console-ink)]">
            {item.event_type || "Uncoded"}
          </dd>
        </div>
        <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2">
          <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Date
          </dt>
          <dd className="mt-1 text-[var(--console-ink)]">
            {eventDateLabel}
          </dd>
        </div>
        <div className={cn("rounded-lg border px-3 py-2", salienceTone)}>
          <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Salience
          </dt>
          <dd className="mt-1 font-medium">
            {item.salience || "Unscored"}
          </dd>
        </div>
        <div className={cn("rounded-lg border px-3 py-2", confidenceTone)}>
          <dt className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Confidence
          </dt>
          <dd className="mt-1 font-medium">
            {item.confidence || "Unscored"}
          </dd>
        </div>
      </dl>

      <div className="mt-3 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3.5 py-3">
        <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
          Brief
        </div>
        <p className="mt-2 text-sm leading-6 text-[var(--console-ink)]">
          {previewText}
        </p>
      </div>

      <div className="mt-3 grid gap-2.5 xl:grid-cols-2">
        <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] p-3.5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[var(--console-ink)]">
                AI provenance
              </h3>
              <p className="mt-1 text-sm text-[var(--console-muted)]">
                What the current event inherited from AI review and source routing.
              </p>
            </div>
            {item.provenance?.source_type ? (
              <span className="rounded-full border border-[var(--console-line)] px-2.5 py-1 text-[10px] uppercase tracking-wide text-[var(--console-muted)]">
                {formatStageLabel(item.provenance.source_type)}
              </span>
            ) : null}
          </div>
          <div className="mt-3 grid gap-2 text-sm text-[var(--console-muted)]">
            {analysisSummary ? (
              <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2.5">
                <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  AI summary
                </div>
                <p className="mt-1.5 leading-6 text-[var(--console-ink)]">
                  {analysisSummary}
                </p>
              </div>
            ) : null}
            <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2.5">
              <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                Review chain
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="text-[var(--console-ink)]">
                  {latestTimelineEntry?.label ||
                    formatStageLabel(latestTimelineEntry?.stage) ||
                    "No workflow stage logged"}
                </span>
                {latestTimelineEntry?.status ? (
                  <span className="rounded-full border border-[var(--console-line)] px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--console-muted)]">
                    {formatStageLabel(latestTimelineEntry.status)}
                  </span>
                ) : null}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] p-3.5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[var(--console-ink)]">
                Country watch
              </h3>
              <p className="mt-1 text-sm text-[var(--console-muted)]">
                Live country posture that frames the selected event.
              </p>
            </div>
            {countryRisk?.overall_risk_level ? (
              <span className="rounded-full border border-[var(--console-line)] px-2.5 py-1 text-[10px] uppercase tracking-wide text-[var(--console-muted)]">
                {countryRisk.overall_risk_level}
              </span>
            ) : null}
          </div>
          {countryRisk ? (
            <div className="mt-3 space-y-2">
              <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] px-3 py-2.5">
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  {countryRisk.leading_label ? <span>{countryRisk.leading_label}</span> : null}
                  {countryRisk.leading_trend ? (
                    <span className="rounded-full border border-[var(--console-line)] px-2 py-0.5">
                      {countryRisk.leading_trend}
                    </span>
                  ) : null}
                </div>
                <p className="mt-1.5 leading-6 text-[var(--console-ink)]">
                  {countryRisk.summary_text || "No country watch summary is available yet."}
                </p>
              </div>
              {watchpoints.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {watchpoints.map((watchpoint) => (
                    <span
                      key={`${item.event_id}-${watchpoint}`}
                      className="rounded-full border border-[var(--console-line)] bg-[var(--console-panel-2)] px-2.5 py-1 text-[11px] text-[var(--console-muted)]"
                    >
                      {watchpoint}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-3 rounded-lg border border-dashed border-[var(--console-line)] px-3 py-3 text-sm text-[var(--console-muted)]">
              No country watch summary is available for this event yet.
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] p-3.5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-[var(--console-ink)]">
              AI verification cues
            </h3>
            <p className="mt-1 text-sm text-[var(--console-muted)]">
              Shared annotations that help classify, verify, and route this event.
            </p>
          </div>
          {item.council_disagreement_summary ? (
            <span className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel-2)] px-2 py-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              AI {item.council_disagreement_summary}
            </span>
          ) : null}
        </div>

        <div className="mt-3 grid gap-2.5 xl:grid-cols-2">
          <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
            <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              Queue posture
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {item.reviewed_by_human === false ? (
                <span className="rounded-full border border-[var(--console-danger)]/35 bg-[var(--console-danger)]/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--console-danger)]">
                  human review pending
                </span>
              ) : null}
              {(item.qa_flag_count ?? 0) > 0 ? (
                <span className="rounded-full border border-[var(--console-warn)]/35 bg-[var(--console-warn)]/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--console-warn)]">
                  {item.qa_flag_count} QA flag{item.qa_flag_count === 1 ? "" : "s"}
                </span>
              ) : null}
              {(item.duplicate_candidate_count ?? 0) > 0 ? (
                <span className="rounded-full border border-[var(--console-info)]/35 bg-[var(--console-info)]/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--console-info)]">
                  duplicate check
                </span>
              ) : null}
              {(item.registry_issue_count ?? 0) > 0 ? (
                <span className="rounded-full border border-[var(--console-warn)]/35 bg-[var(--console-warn)]/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--console-warn)]">
                  registry follow-up
                </span>
              ) : null}
              {!item.qa_flag_count &&
              !item.duplicate_candidate_count &&
              !item.registry_issue_count &&
              item.reviewed_by_human !== false ? (
                <span className="rounded-full border border-[var(--console-success)]/35 bg-[var(--console-success)]/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-[var(--console-success)]">
                  no active warning
                </span>
              ) : null}
            </div>
          </div>

          <div className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3">
            <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              AI recommended actions
            </div>
            {item.council_recommended_actions?.length ? (
              <ul className="mt-2 space-y-1.5">
                {item.council_recommended_actions.slice(0, 3).map((action, index) => (
                  <li
                    key={`${item.event_id}-action-${index}`}
                    className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-[var(--console-ink)]">
                        {(action.code || "follow_up").replaceAll("_", " ")}
                      </span>
                      {action.priority ? (
                        <span
                          className={cn(
                            "rounded-md border px-2 py-0.5 text-[10px] uppercase tracking-wide",
                            action.priority === "high"
                              ? "border-[var(--console-danger)]/35 bg-[var(--console-danger)]/10 text-[var(--console-danger)]"
                              : action.priority === "medium"
                                ? "border-[var(--console-warn)]/35 bg-[var(--console-warn)]/10 text-[var(--console-warn)]"
                                : "border-[var(--console-success)]/35 bg-[var(--console-success)]/10 text-[var(--console-success)]",
                          )}
                        >
                          {action.priority}
                        </span>
                      ) : null}
                    </div>
                    {action.reason ? (
                      <p className="mt-1 text-sm text-[var(--console-muted)]">
                        {action.reason}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-[var(--console-muted)]">
                No AI follow-up recommendations are recorded for this event yet.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button
          aria-controls={evidenceId}
          aria-expanded={showEvidence}
          className="rounded-full border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-1.5 text-sm text-[var(--console-ink)] transition-colors hover:border-[var(--console-accent)]/40 hover:bg-[var(--console-panel)]/80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--console-accent)]"
          onClick={() => setShowEvidence((value) => !value)}
          type="button"
        >
          {showEvidence ? "Hide sources" : `Sources · ${sourceCount}`}
        </button>
      </div>

      {showEvidence ? (
        <div
          id={evidenceId}
          className="mt-3 rounded-lg border border-[var(--console-line)] bg-[var(--console-panel)] p-3.5"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[var(--console-ink)]">
                Source dossier
              </h3>
              <p className="mt-1 text-sm text-[var(--console-muted)]">
                Linked reporting stays attached to the current queue item so
                deeper evidence does not displace the selected event.
              </p>
            </div>
            <div className="rounded-full border border-[var(--console-line)] px-2.5 py-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
              {sourceCount} source{sourceCount === 1 ? "" : "s"}
            </div>
          </div>

          {linkedReports.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {linkedReports.slice(0, 3).map((report, index) => (
                <li
                  key={report.article_id ?? `${item.event_id}-${index}`}
                  className="rounded-lg border border-[var(--console-line)] bg-[var(--console-panel-2)] p-3"
                >
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    <span>{report.source_name || report.link_domain || "Report"}</span>
                    {report.report_role ? <span>{report.report_role}</span> : null}
                  </div>
                  <p className="mt-2 text-sm font-medium text-[var(--console-ink)]">
                    {report.headline || item.headline}
                  </p>
                  {report.description ? (
                    <p className="mt-2 text-sm leading-6 text-[var(--console-muted)]">
                      {report.description}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 rounded-md border border-dashed border-[var(--console-line)] px-3 py-3 text-sm text-[var(--console-muted)]">
              {item.source_primary
                ? `Primary source: ${item.source_primary}`
                : "No linked reports are recorded for this event yet."}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}
