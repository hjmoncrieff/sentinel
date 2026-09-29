import type { CountryMonitorRecord, QueueItem } from "@/lib/domain/types";

type CountryBriefPanelProps = {
  item: QueueItem | null;
  countryBrief: CountryMonitorRecord | null;
  allowed: boolean;
};

function renderSparklinePath(values: number[], width: number, height: number): string {
  if (values.length < 2) {
    return "";
  }
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / range) * height;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function PredictiveSparkline({
  scores,
}: {
  scores: number[];
}) {
  if (scores.length < 2) {
    return null;
  }

  const path = renderSparklinePath(scores, 132, 28);
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 132 28"
      className="h-7 w-full overflow-visible"
      preserveAspectRatio="none"
    >
      <path
        d={path}
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CountryBriefPanel({
  item,
  countryBrief,
  allowed,
}: CountryBriefPanelProps) {
  if (!allowed) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Country brief
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          Country monitor briefs are limited to analyst and admin roles.
        </p>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Country brief
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          No queue item selected.
        </p>
      </div>
    );
  }

  if (!countryBrief) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          Country brief
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          No country monitor summary is available for {item.country || "this event"}.
        </p>
      </div>
    );
  }

  const summary = countryBrief.predictive_summary ?? countryBrief.public_summary;
  const leadingMonitors = (countryBrief.monitors ?? []).slice(0, 3);
  const constructs = (countryBrief.risk_constructs ?? []).slice(0, 2);
  const structuralCards = (countryBrief.public_structural_cards ?? []).slice(0, 4);
  const predictiveSeries = (countryBrief.public_predictive_series ?? []).slice(0, 3);
  const context = countryBrief.public_context;

  return (
    <div className="space-y-4 p-4">
      <div>
        <div className="text-xs uppercase tracking-wide text-[var(--console-muted)]">
          {countryBrief.country}
        </div>
        <h2 className="mt-2 text-xl font-semibold text-[var(--console-ink)]">
          Country brief
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Country-level structural baseline and monitor watchpoints adjacent to the selected event.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3">
          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Overall risk
          </div>
          <div className="mt-1 text-lg font-semibold text-[var(--console-ink)]">
            {summary?.overall_risk_level || "Unknown"}
          </div>
          <div className="text-sm text-[var(--console-muted)]">
            {summary?.overall_risk_score ?? "—"}
          </div>
        </div>
        <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3">
          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
            Leading construct
          </div>
          <div className="mt-1 text-lg font-semibold text-[var(--console-ink)]">
            {summary?.leading_label || "Unknown"}
          </div>
          <div className="text-sm text-[var(--console-muted)]">
            {summary?.leading_trend || "No trend"}
          </div>
        </div>
      </div>

      <p className="text-sm leading-6 text-[var(--console-ink)]">
        {summary?.summary_text || "No predictive summary recorded for this country yet."}
      </p>

      {context?.country_watch ? (
        <section className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Country watch
          </h3>
          <p className="mt-2 text-sm leading-6 text-[var(--console-muted)]">
            {context.country_watch}
          </p>
        </section>
      ) : null}

      {summary?.watchpoints?.length ? (
        <section className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Watchpoints
          </h3>
          <ul className="mt-3 space-y-2 text-sm text-[var(--console-muted)]">
            {summary.watchpoints.slice(0, 3).map((watchpoint) => (
              <li key={watchpoint}>{watchpoint}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {structuralCards.length ? (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Structural context
          </h3>
          <div className="grid gap-3 md:grid-cols-2">
            {structuralCards.map((card) => (
              <div
                key={card.code || card.label}
                className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4"
              >
                <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  {card.label || card.code || "Indicator"}
                </div>
                <div className="mt-2 text-lg font-semibold text-[var(--console-ink)]">
                  {card.display_value || card.current_value || "—"}
                </div>
                <div className="mt-1 text-sm text-[var(--console-muted)]">
                  {card.as_of_year ? `As of ${card.as_of_year}` : "Published dossier metric"}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {predictiveSeries.length ? (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Predictive trajectories
          </h3>
          <div className="grid gap-3 md:grid-cols-3">
            {predictiveSeries.map((series) => {
              const trendPoints = (series.trend_series ?? []).filter(
                (point): point is { year?: number | null; score?: number | null } =>
                  typeof point?.score === "number",
              );
              const sparkScores = trendPoints
                .map((point) => point.score)
                .filter((score): score is number => typeof score === "number");
              const firstScore = trendPoints[0]?.score ?? null;
              const lastScore =
                trendPoints[trendPoints.length - 1]?.score ?? null;
              const delta =
                typeof firstScore === "number" && typeof lastScore === "number"
                  ? lastScore - firstScore
                  : null;
              const firstYear = trendPoints[0]?.year ?? null;
              const lastYear = trendPoints[trendPoints.length - 1]?.year ?? series.as_of_year ?? null;
              return (
                <div
                  key={series.code || series.label}
                  className="group rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4 transition-colors hover:border-[var(--console-line-strong)] hover:bg-[var(--console-panel-2)]"
                >
                  <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    {series.label || series.code || "Construct"}
                  </div>
                  <div className="mt-2 text-lg font-semibold text-[var(--console-ink)]">
                    {series.display_score || series.current_score || "—"}
                  </div>
                  <div className="mt-1 text-sm text-[var(--console-muted)]">
                    {series.trend_label || series.level || "trajectory"}
                  </div>
                  <div className="mt-2 text-xs text-[var(--console-muted)] group-hover:text-[var(--console-ink)]">
                    {firstYear && lastYear
                      ? `Hover for ${firstYear}–${lastYear}`
                      : `Hover for trajectory`}
                  </div>
                  <div className="mt-3 max-h-0 overflow-hidden opacity-0 transition-all duration-200 group-hover:max-h-20 group-hover:opacity-100 group-focus-within:max-h-20 group-focus-within:opacity-100">
                    <div className="text-[var(--console-accent)]">
                      <PredictiveSparkline scores={sparkScores} />
                    </div>
                    <div className="mt-2 text-xs text-[var(--console-muted)]">
                      {delta === null
                        ? `As of ${series.as_of_year || "latest"}`
                        : `${delta > 0 ? "+" : ""}${delta.toFixed(1)} across ${firstYear ?? "earliest"}-${lastYear ?? series.as_of_year ?? "latest"}`}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {leadingMonitors.length ? (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Monitor stack
          </h3>
          {leadingMonitors.map((monitor) => (
            <div
              key={monitor.code || monitor.label}
              className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-[var(--console-ink)]">
                    {monitor.label || monitor.code || "Monitor"}
                  </div>
                  <div className="text-sm text-[var(--console-muted)]">
                    {monitor.goal}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-[var(--console-ink)]">
                    {monitor.composite_score ?? "—"}
                  </div>
                  <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    {monitor.trend_label || "stable"}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </section>
      ) : null}

      {constructs.length ? (
        <section className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--console-ink)]">
            Risk constructs
          </h3>
          {constructs.map((construct) => (
            <div
              key={construct.code || construct.label}
              className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-[var(--console-ink)]">
                    {construct.label || construct.code || "Construct"}
                  </div>
                  <div className="text-sm text-[var(--console-muted)]">
                    {construct.summary_text}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-[var(--console-ink)]">
                    {construct.score ?? "—"}
                  </div>
                  <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    {construct.level || "unknown"}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </section>
      ) : null}
    </div>
  );
}
