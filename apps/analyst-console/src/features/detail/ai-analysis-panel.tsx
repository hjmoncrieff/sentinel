import type { CouncilAnalysisEvent, QueueItem } from "@/lib/domain/types";

type AiAnalysisPanelProps = {
  item: QueueItem | null;
  analysis: CouncilAnalysisEvent | null;
  allowed: boolean;
};

function lensEntries(analysis: CouncilAnalysisEvent | null) {
  return Object.entries(analysis?.analyses ?? {});
}

export function AiAnalysisPanel({
  item,
  analysis,
  allowed,
}: AiAnalysisPanelProps) {
  if (!allowed) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          AI analysis
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          AI lens outputs and council synthesis are limited to analyst and admin roles.
        </p>
      </div>
    );
  }

  if (!item) {
    return (
      <div className="space-y-3 p-4">
        <h2 className="text-sm font-semibold text-[var(--console-ink)]">
          AI analysis
        </h2>
        <p className="text-sm text-[var(--console-muted)]">
          No queue item selected.
        </p>
      </div>
    );
  }

  const entries = lensEntries(analysis);

  return (
    <div className="space-y-4 p-4">
      <div>
        <div className="text-xs uppercase tracking-wide text-[var(--console-muted)]">
          {item.country || "Regional"}
        </div>
        <h2 className="mt-2 text-xl font-semibold text-[var(--console-ink)]">
          AI analysis
        </h2>
        <p className="mt-1 text-sm text-[var(--console-muted)]">
          Council lens outputs, synthesis, and forward watchpoints for the selected event.
        </p>
      </div>

      {entries.length > 0 ? (
        <div className="space-y-3">
          {entries.map(([code, lens]) => (
            <section
              key={code}
              className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-4"
            >
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-semibold text-[var(--console-ink)]">
                  {code.replaceAll("_", " ")}
                </h3>
                {lens.risk_level ? (
                  <span className="rounded-md border border-[var(--console-line)] px-2 py-0.5 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    {lens.risk_level}
                  </span>
                ) : null}
                {typeof lens.confidence === "number" ? (
                  <span className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                    {Math.round(lens.confidence * 100)}% confidence
                  </span>
                ) : null}
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--console-ink)]">
                {lens.public_analysis || lens.assessment || "No AI reading recorded for this lens."}
              </p>
              {lens.public_takeaways ? (
                <ul className="mt-3 space-y-2 text-sm text-[var(--console-muted)]">
                  {Object.entries(lens.public_takeaways)
                    .filter(([, value]) => value)
                    .slice(0, 3)
                    .map(([key, value]) => (
                      <li key={key}>
                        <span className="text-[var(--console-ink)]">
                          {key.replaceAll("_", " ")}:
                        </span>{" "}
                        {value}
                      </li>
                    ))}
                </ul>
              ) : null}
            </section>
          ))}
        </div>
      ) : (
        <p className="rounded-md border border-dashed border-[var(--console-line)] px-3 py-3 text-sm text-[var(--console-muted)]">
          No council analysis is available for this event yet.
        </p>
      )}
    </div>
  );
}
