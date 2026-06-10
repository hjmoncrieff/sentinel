import { useMemo, useState } from "react";

import {
  BookOpenText,
  Database,
  LogOut,
  Shield,
  Send,
  ShieldCheck,
  UserRound,
} from "lucide-react";

import { cn } from "@/lib/cn";
import {
  canPublish,
  canSeeRestrictedIntel,
  labelRole,
} from "@/lib/domain/access";
import type { ConsoleWorkspace, SessionProfile } from "@/lib/domain/types";

const items = [
  { key: "review", label: "Review", icon: BookOpenText },
  { key: "release", label: "Release", icon: Send },
  { key: "audit", label: "Audit", icon: ShieldCheck },
  { key: "registry", label: "Registry", icon: Database },
] satisfies Array<{ key: ConsoleWorkspace; label: string; icon: typeof BookOpenText }>;

type GlobalRailProps = {
  activeWorkspace: ConsoleWorkspace;
  onWorkspaceChange: (workspace: ConsoleWorkspace) => void;
  profile: SessionProfile;
  onSignOut: () => void;
};

export function GlobalRail({
  activeWorkspace,
  onWorkspaceChange,
  profile,
  onSignOut,
}: GlobalRailProps) {
  const [profileOpen, setProfileOpen] = useState(false);

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
    <nav
      aria-label="Global workspace"
      className="relative flex h-screen w-[72px] shrink-0 flex-col items-center gap-2 border-r border-[var(--console-line)] bg-[var(--console-bg-soft)] px-2 py-3"
    >
      <div className="mb-2">
        <button
          aria-expanded={profileOpen}
          aria-haspopup="dialog"
          aria-label="Open profile"
          className={cn(
            "relative flex h-11 w-11 items-center justify-center rounded-md border text-xs font-semibold tracking-[0.08em] transition-colors",
            profileOpen
              ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
              : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:border-[var(--console-accent)]/30 hover:text-[var(--console-ink)]",
          )}
          onClick={() => setProfileOpen((current) => !current)}
          type="button"
        >
          {initials}
          <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border border-[var(--console-bg-soft)] bg-[var(--console-success)]" />
        </button>

        {profileOpen ? (
          <section
            aria-label="User profile"
            className="absolute left-full top-3 z-30 ml-3 w-[264px] rounded-md border border-[var(--console-line)] bg-[var(--console-bg-soft)] shadow-2xl"
          >
            <div className="border-b border-[var(--console-line)] px-4 py-4">
              <div className="flex items-start gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] text-sm font-semibold text-[var(--console-ink)]">
                  {initials}
                </div>
                <div className="min-w-0">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--console-muted)]">
                    Analyst Console
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
              <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  <UserRound aria-hidden="true" className="h-3.5 w-3.5" />
                  Profile
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className="rounded-md border border-[var(--console-line)] px-2 py-0.5 text-[11px] uppercase tracking-wide text-[var(--console-ink)]">
                    {labelRole(profile.role)}
                  </span>
                  <span className="rounded-md border border-[var(--console-success)]/35 bg-[var(--console-success)]/10 px-2 py-0.5 text-[11px] uppercase tracking-wide text-[var(--console-success)]">
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

              <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] p-3">
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  <Shield aria-hidden="true" className="h-3.5 w-3.5" />
                  Access posture
                </div>
                <p className="mt-2 text-xs leading-5 text-[var(--console-muted)]">
                  Invited accounts enter directly into the restricted workspace. Admins manage
                  invitations; analysts and admins can publish release decisions.
                </p>
              </div>

              <button
                className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm font-medium text-[var(--console-ink)] transition-colors hover:bg-[var(--console-panel-2)]"
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
      {items.map((item) => {
        const Icon = item.icon;

        return (
          <button
            key={item.key}
            aria-current={activeWorkspace === item.key ? "page" : undefined}
            aria-label={item.label}
            className={cn(
              "flex h-11 w-11 items-center justify-center rounded-md border transition-colors",
              activeWorkspace === item.key
                ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
                : "border-transparent bg-[var(--console-panel)] text-[var(--console-muted)] hover:border-[var(--console-line)] hover:text-[var(--console-ink)]",
            )}
            onClick={() => {
              setProfileOpen(false);
              onWorkspaceChange(item.key);
            }}
            title={item.label}
            type="button"
          >
            <Icon aria-hidden="true" className="h-4 w-4" />
            <span className="sr-only">{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
