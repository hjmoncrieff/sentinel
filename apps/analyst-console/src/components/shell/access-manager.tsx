import { useMemo, useState } from "react";

import { ShieldPlus, UserPlus } from "lucide-react";

import { cn } from "@/lib/cn";
import { labelInviteRole, labelRole } from "@/lib/domain/access";
import type { ConsoleUserInviteRecord, InviteRole } from "@/lib/domain/types";
import { NavigatorSheet } from "./navigator-sheet";

type AccessManagerProps = {
  busy: boolean;
  error: string | null;
  invites: ConsoleUserInviteRecord[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onInvite: (payload: {
    email: string;
    display_name?: string;
    role: InviteRole;
  }) => Promise<void> | void;
};

type InviteDraft = {
  email: string;
  display_name: string;
  role: InviteRole;
};

const defaultDraft: InviteDraft = {
  email: "",
  display_name: "",
  role: "ra",
};

function formatInviteTime(value?: string | null): string {
  if (!value) {
    return "Pending";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Pending";
  }

  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function AccessManager({
  busy,
  error,
  invites,
  open,
  onOpenChange,
  onInvite,
}: AccessManagerProps) {
  const [draft, setDraft] = useState<InviteDraft>(defaultDraft);
  const [query, setQuery] = useState("");

  const recentInvites = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const filtered = invites.filter((invite) => {
      if (!normalized) {
        return true;
      }

      return [
        invite.invited_display_name,
        invite.invited_email,
        invite.status,
        invite.inviter_name,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalized));
    });

    return filtered.slice(0, 12);
  }, [invites, query]);

  return (
    <div className="relative">
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label="Access and invitations"
        className={cn(
          "inline-flex h-10 items-center justify-center gap-2 rounded-full border px-3 text-sm font-medium transition-colors",
          open
            ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
            : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
        )}
        onClick={() => onOpenChange(!open)}
        type="button"
      >
        <ShieldPlus aria-hidden="true" className="h-4 w-4" />
        {open ? <span>Access</span> : null}
      </button>

      {open ? (
        <NavigatorSheet
          title="Access and invitations"
          searchPlaceholder="Search invites, users, or roles"
          searchValue={query}
          onClose={() => onOpenChange(false)}
          onSearchChange={setQuery}
          leftPane={
            <>
              <div className="mb-4">
                <div className="text-xs uppercase tracking-wide text-[var(--console-muted)]">
                  Recent invites
                </div>
                <p className="mt-2 text-sm text-[var(--console-muted)]">
                  Admins provision invited RAs, analysts, and other admins here.
                </p>
              </div>

              {recentInvites.length ? (
                <ul className="space-y-2">
                  {recentInvites.map((invite) => (
                    <li
                      key={invite.invite_id || invite.invited_email}
                      className="rounded-2xl border border-[var(--console-line)] bg-[var(--console-panel)] px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-medium text-[var(--console-ink)]">
                            {invite.invited_display_name || invite.invited_email}
                          </div>
                          <div className="mt-1 text-xs text-[var(--console-muted)]">
                            {invite.invited_email}
                          </div>
                        </div>
                        <span className="rounded-full border border-[var(--console-line)] px-2.5 py-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                          {labelInviteRole(invite.invited_role)}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-[var(--console-muted)]">
                        <span>{invite.status || "invited"}</span>
                        <span>{formatInviteTime(invite.last_sent_at || invite.invited_at)}</span>
                        {invite.inviter_name ? (
                          <span>
                            {invite.inviter_name}
                            {invite.inviter_role
                              ? ` · ${labelRole(invite.inviter_role)}`
                              : ""}
                          </span>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="rounded-2xl border border-dashed border-[var(--console-line)] px-4 py-4 text-sm text-[var(--console-muted)]">
                  No invitations recorded yet.
                </div>
              )}
            </>
          }
          rightPane={
            <div className="rounded-[26px] border border-[var(--console-line)] bg-[var(--console-panel)] p-5">
              <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--console-muted)]">
                <UserPlus aria-hidden="true" className="h-3.5 w-3.5" />
                Invite user
              </div>

              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  void (async () => {
                    try {
                      await onInvite({
                        email: draft.email,
                        display_name: draft.display_name || undefined,
                        role: draft.role,
                      });
                      setDraft(defaultDraft);
                    } catch {
                      // Keep the draft intact on failure.
                    }
                  })();
                }}
              >
                <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                  Email
                  <input
                    className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                    disabled={busy}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        email: event.target.value,
                      }))
                    }
                    placeholder="name@sentinel.app"
                    type="email"
                    value={draft.email}
                  />
                </label>

                <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                  Display name
                  <input
                    className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                    disabled={busy}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        display_name: event.target.value,
                      }))
                    }
                    placeholder="Optional"
                    type="text"
                    value={draft.display_name}
                  />
                </label>

                <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                  Role
                  <select
                    className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                    disabled={busy}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        role: event.target.value as InviteRole,
                      }))
                    }
                    value={draft.role}
                  >
                    <option value="ra">RA</option>
                    <option value="analyst">Analyst</option>
                    <option value="admin">Admin</option>
                  </select>
                </label>

                {error ? (
                  <p className="rounded-md border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
                    {error}
                  </p>
                ) : null}

                <button
                  className="w-full rounded-full border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2.5 text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={busy || !draft.email.trim()}
                  type="submit"
                >
                  {busy ? "Sending…" : "Send invitation"}
                </button>
              </form>
            </div>
          }
        />
      ) : null}
    </div>
  );
}
