import { useMemo, useState } from "react";

import { LogOut, Shield, UserRound } from "lucide-react";

import { cn } from "@/lib/cn";
import {
  canPublish,
  canSeeRestrictedIntel,
  labelRole,
} from "@/lib/domain/access";
import type { SessionProfile } from "@/lib/domain/types";

type AccountBadgeMenuProps = {
  profile: SessionProfile;
  onSignOut: () => void;
};

export function AccountBadgeMenu({
  profile,
  onSignOut,
}: AccountBadgeMenuProps) {
  const [open, setOpen] = useState(false);

  const initials = useMemo(() => {
    const source = profile.display_name?.trim() || profile.email?.trim() || "User";
    const segments = source
      .replace(/@.*$/, "")
      .split(/[\s._-]+/)
      .filter(Boolean)
      .slice(0, 2);

    return segments.map((segment) => segment[0]?.toUpperCase()).join("") || "U";
  }, [profile.display_name, profile.email]);

  return (
    <div className="relative">
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Open profile"
        className={cn(
          "inline-flex h-10 items-center gap-2 rounded-full border px-2.5 py-1.5 text-left transition-colors",
          open
            ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
            : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-ink)] hover:bg-[var(--console-panel-2)]",
        )}
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <span className="relative flex h-7 w-7 items-center justify-center rounded-full bg-[var(--console-panel-3)] text-[11px] font-semibold tracking-[0.08em]">
          {initials}
          <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border border-[var(--console-panel)] bg-[var(--console-success)]" />
        </span>
        <span className="min-w-0 pr-1">
          <span className="flex items-center gap-1 text-[10px] uppercase tracking-[0.16em] text-[var(--console-muted)]">
            <span className="font-semibold text-[var(--console-ink)]">Sentinel</span>
            <span>/</span>
            <span className="truncate">Analyst Console</span>
          </span>
        </span>
      </button>

      {open ? (
        <section
          aria-label="User profile"
          className="absolute left-0 top-14 z-30 w-[280px] rounded-xl border border-[var(--console-line)] bg-[var(--console-bg-soft)] shadow-2xl"
        >
          <div className="border-b border-[var(--console-line)] px-4 py-4">
            <div className="flex items-start gap-3">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-[var(--console-panel-3)] text-sm font-semibold text-[var(--console-ink)]">
                {initials}
              </div>
              <div className="min-w-0">
                <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--console-muted)]">
                  Signed in
                </div>
                <div className="mt-1 truncate text-sm font-semibold text-[var(--console-ink)]">
                  {profile.display_name || "Sentinel user"}
                </div>
                <div className="mt-1 truncate text-xs text-[var(--console-muted)]">
                  {profile.email || "No email on file"}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4 px-4 py-4">
            <div className="rounded-xl border border-[var(--console-line)] bg-[var(--console-panel)] p-3">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                <UserRound aria-hidden="true" className="h-3.5 w-3.5" />
                Profile
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-[var(--console-line)] px-2.5 py-1 text-[11px] uppercase tracking-wide text-[var(--console-ink)]">
                  {labelRole(profile.role)}
                </span>
                <span className="rounded-full border border-[var(--console-success)]/35 bg-[var(--console-success)]/10 px-2.5 py-1 text-[11px] uppercase tracking-wide text-[var(--console-success)]">
                  {profile.active ? "Active" : "Restricted"}
                </span>
              </div>
              <div className="mt-3 space-y-2 text-xs text-[var(--console-muted)]">
                <div className="flex items-center justify-between gap-3">
                  <span>Can publish</span>
                  <span className="text-[var(--console-ink)]">
                    {canPublish(profile.role) ? "Yes" : "No"}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span>Intel access</span>
                  <span className="text-[var(--console-ink)]">
                    {canSeeRestrictedIntel(profile.role) ? "Extended" : "Limited"}
                  </span>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-[var(--console-line)] bg-[var(--console-panel)] p-3">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                <Shield aria-hidden="true" className="h-3.5 w-3.5" />
                Access posture
              </div>
              <p className="mt-2 text-xs leading-5 text-[var(--console-muted)]">
                Invited accounts enter directly into the workspace. Analysts and admins can
                publish release decisions.
              </p>
            </div>

            <button
              className="inline-flex w-full items-center justify-center gap-2 rounded-full border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm font-medium text-[var(--console-ink)] transition-colors hover:bg-[var(--console-panel-2)]"
              onClick={onSignOut}
              type="button"
            >
              <LogOut aria-hidden="true" className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
