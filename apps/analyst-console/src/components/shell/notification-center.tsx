import { useEffect, useMemo, useState } from "react";

import { Bell, MailPlus } from "lucide-react";

import { cn } from "@/lib/cn";
import {
  labelNotificationAudience,
  labelRole,
} from "@/lib/domain/access";
import type {
  ConsoleNotificationRecord,
  NotificationRecipientRole,
  QueueItem,
} from "@/lib/domain/types";
import { NavigatorSheet } from "./navigator-sheet";

type NotificationCenterProps = {
  authenticated: boolean;
  busy: boolean;
  notifications: ConsoleNotificationRecord[];
  profileName?: string | null;
  selectedItem: QueueItem | null;
  error: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSend: (payload: {
    recipient_role: NotificationRecipientRole;
    subject: string;
    message: string;
    event_id?: string;
    metadata?: Record<string, unknown>;
  }) => Promise<void> | void;
  onMarkRead: (notificationId: string) => Promise<void> | void;
};

type NotificationDraft = {
  recipient_role: NotificationRecipientRole;
  assignment_type: "review_now" | "corroborate" | "release_decision" | "registry_follow_up";
  due_window: "today" | "24h" | "48h";
  subject: string;
  message: string;
};

function createDraft(item: QueueItem | null): NotificationDraft {
  return {
    recipient_role: "analyst",
    assignment_type: "review_now",
    due_window: "24h",
    subject: item
      ? `Event update: ${item.headline}`
      : "Console workflow update",
    message: item
      ? `Please review changes on ${item.event_id} (${item.country || "Regional"}).`
      : "",
  };
}

const audienceOptions: NotificationRecipientRole[] = [
  "ra",
  "analyst",
  "admin",
];

const assignmentOptions: Array<{
  value: NotificationDraft["assignment_type"];
  label: string;
}> = [
  { value: "review_now", label: "Review now" },
  { value: "corroborate", label: "Corroborate" },
  { value: "release_decision", label: "Release" },
  { value: "registry_follow_up", label: "Registry" },
];

const dueWindowOptions: Array<{
  value: NotificationDraft["due_window"];
  label: string;
}> = [
  { value: "today", label: "Today" },
  { value: "24h", label: "24h" },
  { value: "48h", label: "48h" },
];

function formatMetadataBadge(value: unknown): string | null {
  if (value == null || value === "") {
    return null;
  }

  return String(value).replaceAll("_", " ");
}

export function NotificationCenter({
  authenticated,
  busy,
  notifications,
  profileName,
  selectedItem,
  error,
  open,
  onOpenChange,
  onSend,
  onMarkRead,
}: NotificationCenterProps) {
  const [draft, setDraft] = useState<NotificationDraft>(() =>
    createDraft(selectedItem),
  );
  const [query, setQuery] = useState("");

  useEffect(() => {
    setDraft((current) => {
      const next = createDraft(selectedItem);
      if (current.message.trim() || current.subject.trim()) {
        return {
          ...current,
          subject: next.subject,
        };
      }

      return next;
    });
  }, [selectedItem?.event_id]);

  const unreadCount = useMemo(
    () => notifications.filter((row) => !row.read_at).length,
    [notifications],
  );

  const filteredNotifications = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return notifications.filter((notification) => {
      if (!normalized) {
        return true;
      }

      return [
        notification.subject,
        notification.message,
        notification.sender_name,
        notification.event_id,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalized));
    });
  }, [notifications, query]);

  return (
    <div className="relative">
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        className={cn(
          "relative inline-flex h-10 items-center justify-center gap-2 rounded-full border px-3 text-sm font-medium transition-colors",
          open
            ? "border-[var(--console-accent)] bg-[var(--console-panel-2)] text-[var(--console-ink)]"
            : "border-[var(--console-line)] bg-[var(--console-panel)] text-[var(--console-muted)] hover:bg-[var(--console-panel-2)] hover:text-[var(--console-ink)]",
        )}
        onClick={() => onOpenChange(!open)}
        type="button"
      >
        <Bell aria-hidden="true" className="h-4 w-4" />
        {open ? <span>Inbox</span> : null}
        {unreadCount ? (
          <span className="absolute -right-1 -top-1 inline-flex min-w-5 items-center justify-center rounded-full bg-[var(--console-accent)] px-1.5 py-0.5 text-[10px] font-semibold text-[#071019]">
            {unreadCount}
          </span>
        ) : null}
        <span className="sr-only">Notifications and messages</span>
      </button>

      {open ? (
        <NavigatorSheet
          title="Notifications and messages"
          searchPlaceholder="Search notifications, users, or events"
          searchValue={query}
          onClose={() => onOpenChange(false)}
          onSearchChange={setQuery}
          leftPane={
            <>
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <div className="text-xs uppercase tracking-wide text-[var(--console-muted)]">
                    Inbox
                  </div>
                  <p className="mt-2 text-sm text-[var(--console-muted)]">
                    Route event changes to RAs, analysts, or admins.
                  </p>
                </div>
                <span className="rounded-full border border-[var(--console-line)] px-3 py-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  {unreadCount} unread
                </span>
              </div>

              {filteredNotifications.length ? (
                <ul className="space-y-2">
                  {filteredNotifications.map((notification) => (
                    <li
                      key={notification.notification_id || `${notification.subject}-${notification.created_at}`}
                      className="rounded-2xl border border-[var(--console-line)] bg-[var(--console-panel)] px-4 py-3"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                            To {labelNotificationAudience(notification.recipient_role)}
                          </div>
                          <div className="mt-1 text-sm font-medium text-[var(--console-ink)]">
                            {notification.subject}
                          </div>
                        </div>
                        {!notification.read_at && notification.notification_id ? (
                          <button
                            className="text-[11px] uppercase tracking-wide text-[var(--console-accent)]"
                            onClick={() => {
                              void onMarkRead(notification.notification_id as string);
                            }}
                            type="button"
                          >
                            Mark read
                          </button>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm text-[var(--console-muted)]">
                        {notification.message}
                      </p>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px]">
                        {[
                          formatMetadataBadge(
                            notification.metadata?.assignment_type,
                          ),
                          formatMetadataBadge(notification.metadata?.due_window),
                          formatMetadataBadge(notification.metadata?.country),
                        ]
                          .filter((value): value is string => !!value)
                          .map((value) => (
                            <span
                              key={`${notification.notification_id || notification.subject}-${value}`}
                              className="rounded-full border border-[var(--console-line)] px-2.5 py-1 uppercase tracking-wide text-[var(--console-muted)]"
                            >
                              {value}
                            </span>
                          ))}
                      </div>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-[var(--console-muted)]">
                        <span>{notification.sender_name || "Analyst"}</span>
                        {notification.sender_role ? (
                          <span className="rounded-full border border-[var(--console-line)] px-2.5 py-1 uppercase tracking-wide">
                            {labelRole(notification.sender_role)}
                          </span>
                        ) : null}
                        {notification.event_id ? (
                          <span>{notification.event_id}</span>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="rounded-2xl border border-dashed border-[var(--console-line)] px-4 py-4 text-sm text-[var(--console-muted)]">
                  No notifications yet.
                </div>
              )}
            </>
          }
          rightPane={
            <div className="rounded-[26px] border border-[var(--console-line)] bg-[var(--console-panel)] p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--console-muted)]">
                  <MailPlus aria-hidden="true" className="h-3.5 w-3.5" />
                  Notify team
                </div>
                <span className="rounded-full border border-[var(--console-line)] px-3 py-1 text-[11px] uppercase tracking-wide text-[var(--console-muted)]">
                  {authenticated ? profileName || "Signed in" : "Preview"}
                </span>
              </div>

              {!authenticated ? (
                <p className="rounded-2xl border border-[var(--console-line)] bg-[var(--console-panel-2)] px-4 py-4 text-sm text-[var(--console-muted)]">
                  Sign in to notify RAs, analysts, or admins about review changes.
                </p>
              ) : null}

              <form
                className="space-y-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  void (async () => {
                    try {
                      await onSend({
                        recipient_role: draft.recipient_role,
                        subject: draft.subject,
                        message: draft.message,
                        event_id: selectedItem?.event_id,
                        metadata: selectedItem
                          ? {
                              assignment_type: draft.assignment_type,
                              due_window: draft.due_window,
                              country: selectedItem.country,
                              headline: selectedItem.headline,
                              review_priority: selectedItem.review_priority,
                              workspace: "analyst-console",
                            }
                          : {
                              assignment_type: draft.assignment_type,
                              due_window: draft.due_window,
                              workspace: "analyst-console",
                            },
                      });
                      setDraft(createDraft(selectedItem));
                    } catch {
                      // Keep the current draft intact when the send fails.
                    }
                  })();
                }}
              >
                <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                  Audience
                  <select
                    className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                    disabled={!authenticated || busy}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        recipient_role: event.target.value as NotificationRecipientRole,
                      }))
                    }
                    value={draft.recipient_role}
                  >
                    {audienceOptions.map((role) => (
                      <option key={role} value={role}>
                        {labelNotificationAudience(role)}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                    Assignment
                    <select
                      className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                      disabled={!authenticated || busy}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          assignment_type:
                            event.target.value as NotificationDraft["assignment_type"],
                        }))
                      }
                      value={draft.assignment_type}
                    >
                      {assignmentOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                    Due
                    <select
                      className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                      disabled={!authenticated || busy}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          due_window:
                            event.target.value as NotificationDraft["due_window"],
                        }))
                      }
                      value={draft.due_window}
                    >
                      {dueWindowOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                  Subject
                  <input
                    className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                    disabled={!authenticated || busy}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        subject: event.target.value,
                      }))
                    }
                    type="text"
                    value={draft.subject}
                  />
                </label>

                <label className="grid gap-1 text-sm text-[var(--console-muted)]">
                  Message
                  <textarea
                    className="min-h-28 rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-2 text-sm text-[var(--console-ink)] outline-none"
                    disabled={!authenticated || busy}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        message: event.target.value,
                      }))
                    }
                    placeholder="Summarize what changed, what needs review, and who should act."
                    value={draft.message}
                  />
                </label>

                {selectedItem ? (
                  <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-3 text-xs text-[var(--console-muted)]">
                    Linked event:{" "}
                    <span className="text-[var(--console-ink)]">
                      {selectedItem.event_id} · {selectedItem.headline}
                    </span>
                  </div>
                ) : null}

                {error ? (
                  <p className="rounded-md border border-[var(--console-danger)]/40 bg-[var(--console-danger)]/10 px-3 py-3 text-sm text-[var(--console-danger)]">
                    {error}
                  </p>
                ) : null}

                <button
                  className="w-full rounded-full border border-[var(--console-accent)] bg-[var(--console-panel-2)] px-3 py-2.5 text-left text-sm font-medium text-[var(--console-ink)] disabled:cursor-not-allowed disabled:border-[var(--console-line)] disabled:text-[var(--console-muted)]"
                  disabled={
                    !authenticated ||
                    busy ||
                    !draft.subject.trim() ||
                    !draft.message.trim()
                  }
                  type="submit"
                >
                  {busy ? "Sending…" : "Send notification"}
                </button>
              </form>
            </div>
          }
        />
      ) : null}
    </div>
  );
}
