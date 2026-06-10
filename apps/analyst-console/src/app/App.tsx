import { Suspense, lazy, useEffect, useMemo, useReducer, useState } from "react";

import { AccessManager } from "@/components/shell/access-manager";
import { AuthBanner } from "@/components/shell/auth-banner";
import { CenterTabBar } from "@/components/shell/center-tab-bar";
import { FilterManager } from "@/components/shell/filter-manager";
import { NotificationCenter } from "@/components/shell/notification-center";
import { TopOperationsBar } from "@/components/shell/top-operations-bar";
import { WorkspaceTabBar } from "@/components/shell/workspace-tab-bar";
import { WorkspaceFrame } from "@/components/shell/workspace-frame";
import { QueuePanel } from "@/features/queue/queue-panel";
import { loadEventEdits, loadRecentRegistryEdits } from "@/lib/api/audit-reads";
import {
  getSessionProfile,
  hasConsoleRecoveryToken,
  requestConsolePasswordReset,
  signInConsoleUser,
  signOutConsoleUser,
  subscribeToAuthChanges,
  updateConsolePassword,
} from "@/lib/api/console-auth";
import {
  inviteConsoleUser,
  loadConsoleInvites,
} from "@/lib/api/console-invites";
import {
  loadConsoleNotifications,
  markConsoleNotificationRead,
  sendConsoleNotification,
} from "@/lib/api/console-notifications";
import { loadConsoleWorkspace } from "@/lib/api/load-console-workspace";
import {
  createManualEvent,
  markEventReadyForRelease,
  saveEventEdit,
  saveRegistryEdit,
  withholdEventFromRelease,
} from "@/lib/api/review-actions";
import {
  canAdministerAccess,
  canPublish,
  canSeeRestrictedIntel,
} from "@/lib/domain/access";
import { getQueueHealth, getVisibleQueue } from "@/lib/domain/queue";
import type {
  ConsoleWorkspaceData,
  ConsoleUserInviteRecord,
  EventEditRecord,
  ConsoleNotificationRecord,
  QueueItem,
  RegistryEditRecord,
  SessionState,
} from "@/lib/domain/types";
import {
  consoleReducer,
  initialConsoleState,
} from "@/lib/state/console-reducer";

const ActionPanel = lazy(async () => ({
  default: (await import("@/features/actions/action-panel")).ActionPanel,
}));
const AuditPanel = lazy(async () => ({
  default: (await import("@/features/actions/audit-panel")).AuditPanel,
}));
const RegistryPanel = lazy(async () => ({
  default: (await import("@/features/actions/registry-panel")).RegistryPanel,
}));
const ReleasePanel = lazy(async () => ({
  default: (await import("@/features/actions/release-panel")).ReleasePanel,
}));
const AiAnalysisPanel = lazy(async () => ({
  default: (await import("@/features/detail/ai-analysis-panel")).AiAnalysisPanel,
}));
const BriefPanel = lazy(async () => ({
  default: (await import("@/features/detail/brief-panel")).BriefPanel,
}));
const CountryBriefPanel = lazy(async () => ({
  default: (await import("@/features/detail/country-brief-panel")).CountryBriefPanel,
}));
const DataPanel = lazy(async () => ({
  default: (await import("@/features/detail/data-panel")).DataPanel,
}));

const emptyWorkspaceData: ConsoleWorkspaceData = {
  queue: [],
  councilByEvent: {},
  countriesByName: {},
  registryActors: [],
  source: "local",
};

type HeaderFilterChip = {
  key: string;
  label: string;
  onClear: () => void;
};

function PanelLoadingFallback({ label }: { label: string }) {
  return (
    <div className="space-y-3 p-4">
      <h2 className="text-sm font-semibold text-[var(--console-ink)]">{label}</h2>
      <div className="rounded-md border border-[var(--console-line)] bg-[var(--console-panel)] px-3 py-3 text-sm text-[var(--console-muted)]">
        Loading panel…
      </div>
    </div>
  );
}

export function App() {
  const [state, dispatch] = useReducer(consoleReducer, initialConsoleState);
  const [recoveryMode, setRecoveryMode] = useState(() =>
    hasConsoleRecoveryToken(),
  );
  const [session, setSession] = useState<SessionState>({
    busy: true,
    error: null,
    profile: null,
  });
  const [authInfo, setAuthInfo] = useState<string | null>(null);
  const [workspaceData, setWorkspaceData] =
    useState<ConsoleWorkspaceData>(emptyWorkspaceData);
  const [eventEdits, setEventEdits] = useState<EventEditRecord[]>([]);
  const [registryEdits, setRegistryEdits] = useState<RegistryEditRecord[]>([]);
  const [notifications, setNotifications] = useState<ConsoleNotificationRecord[]>([]);
  const [invites, setInvites] = useState<ConsoleUserInviteRecord[]>([]);
  const [panelBusy, setPanelBusy] = useState(false);
  const [panelError, setPanelError] = useState<string | null>(null);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [notificationBusy, setNotificationBusy] = useState(false);
  const [notificationError, setNotificationError] = useState<string | null>(null);
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [utilityPanel, setUtilityPanel] = useState<
    "access" | "filters" | "notifications" | null
  >(null);
  const [manualEventBusy, setManualEventBusy] = useState(false);
  const [manualEventError, setManualEventError] = useState<string | null>(null);
  const [manualEventOpen, setManualEventOpen] = useState(false);

  useEffect(() => {
    let active = true;

    void getSessionProfile()
      .then((profile) => {
        if (!active) {
          return;
        }

        if (recoveryMode) {
          setSession({ busy: false, error: null, profile: null });
          return;
        }

        setSession({ busy: false, error: null, profile });
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        setSession({
          busy: false,
          error:
            error instanceof Error
              ? error.message
              : "Failed to connect analyst session.",
          profile: null,
        });
      });

    const unsubscribe = subscribeToAuthChanges((profile, event) => {
      if (!active) {
        return;
      }

      if (event === "PASSWORD_RECOVERY") {
        setRecoveryMode(true);
        setAuthInfo("Recovery session verified. Set a new password to continue.");
      }

      setSession((current) => ({
        ...current,
        busy: false,
        error: null,
        profile: event === "PASSWORD_RECOVERY" ? null : profile,
      }));
    });

    return () => {
      active = false;
      unsubscribe();
    };
  }, [recoveryMode]);

  useEffect(() => {
    if (!session.profile) {
      setWorkspaceData(emptyWorkspaceData);
      dispatch({ type: "queueLoaded", payload: [] });
      return;
    }

    let active = true;

    void loadConsoleWorkspace(session.profile)
      .then((data) => {
        if (!active) {
          return;
        }

        setWorkspaceData(data);
        dispatch({ type: "queueLoaded", payload: data.queue });
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        const message =
          error instanceof Error
            ? error.message
            : "Failed to load review workspace.";
        dispatch({ type: "loadFailed", payload: message });
      });

    return () => {
      active = false;
    };
  }, [session.profile]);

  const visibleQueue = getVisibleQueue(state.queue, {
    search: state.search,
    priorityFilter: state.priorityFilter,
    queueScope: state.queueScope,
    worklistFilter: state.worklistFilter,
    countryFilter: state.countryFilter,
    categoryFilter: state.categoryFilter,
    sortOrder: state.sortOrder,
  });
  const queueHealth = useMemo(
    () =>
      getQueueHealth(
        getVisibleQueue(state.queue, {
          search: state.search,
          priorityFilter: state.priorityFilter,
          queueScope: "all",
          worklistFilter: "all",
          countryFilter: state.countryFilter,
          categoryFilter: state.categoryFilter,
          sortOrder: state.sortOrder,
        }),
      ),
    [
      state.categoryFilter,
      state.countryFilter,
      state.priorityFilter,
      state.queue,
      state.search,
      state.sortOrder,
    ],
  );
  const selectedItem =
    visibleQueue.find((row) => row.event_id === state.selectedId) ??
    visibleQueue[0] ??
    null;
  const availableCountries = useMemo(
    () =>
      Array.from(
        new Set(
          state.queue
            .map((row) => row.country?.trim())
            .filter((value): value is string => !!value),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [state.queue],
  );
  const availableCategories = useMemo(
    () =>
      Array.from(
        new Set(
          state.queue
            .map((row) => row.event_type?.trim())
            .filter((value): value is string => !!value),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [state.queue],
  );
  const activeHeaderFilters = useMemo(
    (): HeaderFilterChip[] =>
      [
        state.search.trim()
          ? {
              key: "search",
              label: `Search: ${state.search.trim()}`,
              onClear: () => dispatch({ type: "searchChanged", payload: "" }),
            }
          : null,
        state.queueScope !== "all"
          ? {
              key: "scope",
              label: "Review now",
              onClear: () => dispatch({ type: "queueScopeChanged", payload: "all" }),
            }
          : null,
        state.worklistFilter !== "all"
          ? {
              key: "worklist",
              label:
                state.worklistFilter === "publish-ready"
                  ? "Worklist: publish ready"
                  : state.worklistFilter === "corroborate"
                    ? "Worklist: corroborate"
                    : state.worklistFilter === "registry"
                      ? "Worklist: registry"
                      : "Worklist: duplicates",
              onClear: () =>
                dispatch({ type: "worklistFilterChanged", payload: "all" }),
            }
          : null,
        state.priorityFilter !== "all"
          ? {
              key: "priority",
              label: `Priority: ${state.priorityFilter}`,
              onClear: () => dispatch({ type: "priorityChanged", payload: "all" }),
            }
          : null,
        state.countryFilter !== "all"
          ? {
              key: "country",
              label: `Country: ${state.countryFilter}`,
              onClear: () =>
                dispatch({ type: "countryFilterChanged", payload: "all" }),
            }
          : null,
        state.categoryFilter !== "all"
          ? {
              key: "category",
              label: `Category: ${state.categoryFilter}`,
              onClear: () =>
                dispatch({ type: "categoryFilterChanged", payload: "all" }),
            }
          : null,
        state.sortOrder !== "priority"
          ? {
              key: "sort",
              label: "Sort: most recent",
              onClear: () => dispatch({ type: "sortOrderChanged", payload: "priority" }),
            }
          : null,
      ].filter((value): value is HeaderFilterChip => value !== null),
    [
      state.categoryFilter,
      state.countryFilter,
      state.priorityFilter,
      state.queueScope,
      state.worklistFilter,
      state.search,
      state.sortOrder,
    ],
  );

  useEffect(() => {
    if (!selectedItem || !session.profile) {
      setEventEdits([]);
      setAuditError(null);
      return;
    }

    let active = true;
    setAuditError(null);

    void loadEventEdits(selectedItem.event_id)
      .then((rows) => {
        if (active) {
          setEventEdits(rows);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setAuditError(
            error instanceof Error ? error.message : "Failed to load event edits.",
          );
          setEventEdits([]);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedItem?.event_id, session.profile]);

  useEffect(() => {
    if (!session.profile) {
      setRegistryEdits([]);
      return;
    }

    let active = true;
    void loadRecentRegistryEdits()
      .then((rows) => {
        if (active) {
          setRegistryEdits(rows);
        }
      })
      .catch(() => {
        if (active) {
          setRegistryEdits([]);
        }
      });

    return () => {
      active = false;
    };
  }, [session.profile]);

  useEffect(() => {
    if (!session.profile) {
      setNotifications([]);
      setNotificationError(null);
      return;
    }

    let active = true;
    setNotificationError(null);

    void loadConsoleNotifications()
      .then((rows) => {
        if (active) {
          setNotifications(rows);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setNotificationError(
            error instanceof Error
              ? error.message
              : "Failed to load notifications.",
          );
          setNotifications([]);
        }
      });

    return () => {
      active = false;
    };
  }, [session.profile]);

  useEffect(() => {
    if (!canAdministerAccess(session.profile?.role)) {
      setInvites([]);
      setInviteError(null);
      return;
    }

    let active = true;
    setInviteError(null);

    void loadConsoleInvites()
      .then((rows) => {
        if (active) {
          setInvites(rows);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setInviteError(
            error instanceof Error ? error.message : "Failed to load invitations.",
          );
          setInvites([]);
        }
      });

    return () => {
      active = false;
    };
  }, [session.profile]);

  const accessAdminVisible = canAdministerAccess(session.profile?.role);
  const restrictedIntelVisible = canSeeRestrictedIntel(session.profile?.role);
  const publishAllowed = canPublish(session.profile?.role);
  const selectedAnalysis = selectedItem
    ? workspaceData.councilByEvent[selectedItem.event_id] ?? null
    : null;
  const selectedCountryBrief = selectedItem?.country
    ? workspaceData.countriesByName[selectedItem.country.toLowerCase()] ?? null
    : null;

  function mapManualEventToQueueItem(row: {
    submission_id: string;
    headline: string;
    country?: string | null;
    event_date?: string | null;
    event_type?: string | null;
    summary?: string | null;
    source_primary?: string | null;
    confidence?: string | null;
    salience?: string | null;
    review_priority?: string | null;
    editor_name?: string | null;
    created_at?: string | null;
    status?: string | null;
  }): QueueItem {
    const reviewPriority =
      row.review_priority === "high" || row.review_priority === "low"
        ? row.review_priority
        : "medium";
    const salience =
      row.salience === "high" || row.salience === "low"
        ? row.salience
        : "medium";

    return {
      event_id: `manual-${row.submission_id.slice(0, 12)}`,
      headline: row.headline,
      country: row.country ?? "Regional",
      event_date: row.event_date ?? row.created_at?.slice(0, 10) ?? null,
      event_type: row.event_type ?? "other",
      summary: row.summary ?? "Manual event submission awaiting review.",
      source_primary: row.source_primary ?? "Manual submission",
      confidence:
        row.confidence === "high" || row.confidence === "low"
          ? row.confidence
          : "medium",
      review_status: row.status ?? "manual_submitted",
      review_priority: reviewPriority,
      publication_status: "withheld" as const,
      publication_label: "Manual submission",
      publication_reason: "manual_event_submission",
      salience,
      publication_ready: false,
      reviewed_by_human: false,
      qa_flag_count: 0,
      duplicate_candidate_count: 0,
      registry_issue_count: 0,
      supervision_reasons: ["manual_submission"],
      provenance: {
        source_type: "manual_submission",
        linked_reports: [],
        timeline: [
          {
            stage: "manual_submission",
            label: `Submitted by ${row.editor_name ?? "Analyst"}`,
            status: row.status ?? "manual_submitted",
            at: row.created_at ?? null,
          },
        ],
      },
    };
  }

  async function runPanelAction(task: () => Promise<void>) {
    setPanelBusy(true);
    setPanelError(null);

    try {
      await task();
    } catch (error: unknown) {
      setPanelError(
        error instanceof Error ? error.message : "Failed to save analyst action.",
      );
    } finally {
      setPanelBusy(false);
    }
  }

  const centerPanel = useMemo(() => {
    switch (state.middleTab) {
      case "ai-analysis":
        return (
          <AiAnalysisPanel
            allowed={restrictedIntelVisible}
            analysis={selectedAnalysis}
            item={selectedItem}
          />
        );
      case "country-brief":
        return (
          <CountryBriefPanel
            allowed={restrictedIntelVisible}
            countryBrief={selectedCountryBrief}
            item={selectedItem}
          />
        );
      case "data":
        return (
          <DataPanel
            analysis={selectedAnalysis}
            countryBrief={selectedCountryBrief}
            editHistory={eventEdits}
            item={selectedItem}
          />
        );
      case "briefing":
      default:
        return (
          <BriefPanel
            analysis={selectedAnalysis}
            countryBrief={selectedCountryBrief}
            item={selectedItem}
            loadError={state.loadError}
          />
        );
    }
  }, [
    eventEdits,
    restrictedIntelVisible,
    selectedAnalysis,
    selectedCountryBrief,
    selectedItem,
    state.loadError,
    state.middleTab,
  ]);

  const rightPanel = useMemo(() => {
    switch (state.workspace) {
      case "release":
        return (
          <ReleasePanel
            authenticated={!!session.profile}
            busy={panelBusy}
            canPublish={publishAllowed}
            item={selectedItem}
            onReady={({ eventId, comment }) =>
              runPanelAction(async () => {
                await markEventReadyForRelease({
                  event_id: eventId,
                  comment,
                });
                dispatch({
                  type: "queueItemPatched",
                  payload: {
                    eventId,
                    patch: {
                      publication_status: "draft",
                      publication_label: "Ready for release",
                      publication_ready: true,
                      reviewed_by_human: true,
                      review_status: "analyst_reviewed",
                    },
                  },
                });
                const edits = session.profile
                  ? await loadEventEdits(eventId)
                  : [];
                setEventEdits(edits);
              })
            }
            onWithhold={({ eventId, comment }) =>
              runPanelAction(async () => {
                await withholdEventFromRelease({
                  event_id: eventId,
                  comment,
                });
                dispatch({
                  type: "queueItemPatched",
                  payload: {
                    eventId,
                    patch: {
                      publication_status: "withheld",
                      publication_label: "Withheld",
                      publication_ready: false,
                      reviewed_by_human: true,
                    },
                  },
                });
                const edits = session.profile
                  ? await loadEventEdits(eventId)
                  : [];
                setEventEdits(edits);
              })
            }
            saveError={panelError}
          />
        );
      case "audit":
        return (
          <AuditPanel
            editHistory={eventEdits}
            item={selectedItem}
            loadError={auditError}
          />
        );
      case "registry":
        return (
          <RegistryPanel
            actors={workspaceData.registryActors}
            authenticated={!!session.profile}
            busy={panelBusy}
            item={selectedItem}
            onSubmit={(payload) =>
              runPanelAction(async () => {
                await saveRegistryEdit(payload);
                if (session.profile) {
                  const rows = await loadRecentRegistryEdits();
                  setRegistryEdits(rows);
                }
              })
            }
            recentEdits={registryEdits}
            saveError={panelError}
          />
        );
      case "review":
      default:
        return (
          <ActionPanel
            authenticated={!!session.profile}
            busy={panelBusy}
            item={selectedItem}
            onSave={({ eventId, patch, comment }) =>
              runPanelAction(async () => {
                await saveEventEdit({
                  event_id: eventId,
                  comment,
                  patch,
                });
                dispatch({
                  type: "queueItemPatched",
                  payload: {
                    eventId,
                    patch: {
                      ...patch,
                      reviewed_by_human: true,
                    },
                  },
                });
                const edits = session.profile
                  ? await loadEventEdits(eventId)
                  : [];
                setEventEdits(edits);
              })
            }
            saveError={panelError}
          />
        );
    }
  }, [
    auditError,
    eventEdits,
    panelBusy,
    panelError,
    publishAllowed,
    registryEdits,
    selectedItem,
    session.profile,
    state.workspace,
    workspaceData.registryActors,
  ]);

  async function handleSignIn(payload: { email: string; password: string }) {
    setSession((current) => ({ ...current, busy: true, error: null }));
    setAuthInfo(null);

    try {
      await signInConsoleUser(payload.email, payload.password);
      const profile = await getSessionProfile();
      setSession({ busy: false, error: null, profile });
    } catch (error: unknown) {
      setSession({
        busy: false,
        error: error instanceof Error ? error.message : "Failed to sign in.",
        profile: null,
      });
    }
  }

  async function handleSignOut() {
    setSession((current) => ({ ...current, busy: true, error: null }));
    setAuthInfo(null);
    setRecoveryMode(false);

    try {
      await signOutConsoleUser();
      setSession({ busy: false, error: null, profile: null });
    } catch (error: unknown) {
      setSession((current) => ({
        ...current,
        busy: false,
        error: error instanceof Error ? error.message : "Failed to sign out.",
      }));
    }
  }

  async function handleForgotPassword(email: string) {
    const normalizedEmail = email.trim();

    if (!normalizedEmail) {
      setSession((current) => ({
        ...current,
        error: "Enter your email address first, then request a password reset.",
      }));
      return;
    }

    setSession((current) => ({ ...current, busy: true, error: null }));
    setAuthInfo(null);

    try {
      await requestConsolePasswordReset(
        normalizedEmail,
        `${window.location.origin}${window.location.pathname}`,
      );
      setSession((current) => ({ ...current, busy: false, error: null }));
      setAuthInfo(
        "Password reset sent. Check your email and open the recovery link to set a new password.",
      );
    } catch (error: unknown) {
      setSession((current) => ({
        ...current,
        busy: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to send password reset email.",
      }));
    }
  }

  async function handleUpdatePassword(payload: { password: string }) {
    setSession((current) => ({ ...current, busy: true, error: null }));
    setAuthInfo(null);

    try {
      await updateConsolePassword(payload.password);
      const profile = await getSessionProfile();
      setRecoveryMode(false);
      setSession({ busy: false, error: null, profile });
      setAuthInfo("Password updated.");
    } catch (error: unknown) {
      setSession((current) => ({
        ...current,
        busy: false,
        error:
          error instanceof Error ? error.message : "Failed to update password.",
      }));
    }
  }

  async function handleSendNotification(payload: {
    recipient_role: "ra" | "analyst" | "admin";
    subject: string;
    message: string;
    event_id?: string;
    metadata?: Record<string, unknown>;
  }) {
    if (!session.profile) {
      return;
    }

    setNotificationBusy(true);
    setNotificationError(null);

    try {
      await sendConsoleNotification(payload);
      const rows = await loadConsoleNotifications();
      setNotifications(rows);
    } catch (error: unknown) {
      setNotificationError(
        error instanceof Error ? error.message : "Failed to send notification.",
      );
      throw error;
    } finally {
      setNotificationBusy(false);
    }
  }

  async function handleMarkNotificationRead(notificationId: string) {
    if (!session.profile) {
      return;
    }

    setNotificationBusy(true);
    setNotificationError(null);

    try {
      await markConsoleNotificationRead(notificationId);
      setNotifications((current) =>
        current.map((row) =>
          row.notification_id === notificationId
            ? { ...row, read_at: new Date().toISOString() }
            : row,
        ),
      );
    } catch (error: unknown) {
      setNotificationError(
        error instanceof Error
          ? error.message
          : "Failed to update notification.",
      );
      throw error;
    } finally {
      setNotificationBusy(false);
    }
  }

  async function handleCreateManualEvent(payload: {
    headline: string;
    country: string;
    event_date: string;
    event_type: string;
    summary: string;
    source_primary: string;
    salience: string;
    confidence: string;
    review_priority: string;
    location: string;
    note: string;
  }) {
    setManualEventBusy(true);
    setManualEventError(null);

    try {
      const response = await createManualEvent(payload);
      const manualEvent = response.manual_event as
        | {
            submission_id: string;
            headline: string;
            country?: string | null;
            event_date?: string | null;
            event_type?: string | null;
            summary?: string | null;
            source_primary?: string | null;
            confidence?: string | null;
            salience?: string | null;
            review_priority?: string | null;
            editor_name?: string | null;
            created_at?: string | null;
            status?: string | null;
          }
        | undefined;

      if (!manualEvent) {
        throw new Error("Manual event was created, but no queue row was returned.");
      }

      dispatch({
        type: "queueItemInserted",
        payload: mapManualEventToQueueItem(manualEvent),
      });
      setManualEventOpen(false);
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to add manual event.";
      setManualEventError(message);
      throw error;
    } finally {
      setManualEventBusy(false);
    }
  }

  async function handleInviteConsoleUser(payload: {
    email: string;
    display_name?: string;
    role: "ra" | "analyst" | "admin";
  }) {
    setInviteBusy(true);
    setInviteError(null);

    try {
      await inviteConsoleUser(payload);
      const rows = await loadConsoleInvites();
      setInvites(rows);
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to send invitation.";
      setInviteError(message);
      throw error;
    } finally {
      setInviteBusy(false);
    }
  }

  if (!session.profile || recoveryMode) {
    return (
      <div className="flex h-screen overflow-hidden bg-[var(--console-bg)] text-[var(--console-ink)]">
        <AuthBanner
          busy={session.busy}
          error={session.error}
          info={authInfo}
          recoveryMode={recoveryMode}
          onForgotPassword={handleForgotPassword}
          onSignIn={handleSignIn}
          onUpdatePassword={handleUpdatePassword}
        />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--console-bg)] text-[var(--console-ink)]">
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopOperationsBar
          activeFilters={activeHeaderFilters}
          onSearchChange={(value) =>
            dispatch({ type: "searchChanged", payload: value })
          }
          onSignOut={() => {
            void handleSignOut();
          }}
          profile={session.profile}
          search={state.search}
          utilitySlot={
            <div className="flex items-center gap-2">
              <FilterManager
                availableCategories={availableCategories}
                availableCountries={availableCountries}
                categoryFilter={state.categoryFilter}
                countryFilter={state.countryFilter}
                onOpenChange={(open) =>
                  setUtilityPanel(open ? "filters" : null)
                }
                onCategoryFilterChange={(category) =>
                  dispatch({ type: "categoryFilterChanged", payload: category })
                }
                onCountryFilterChange={(country) =>
                  dispatch({ type: "countryFilterChanged", payload: country })
                }
                onPriorityFilterChange={(priority) =>
                  dispatch({ type: "priorityChanged", payload: priority })
                }
                onQueueScopeChange={(scope) =>
                  dispatch({ type: "queueScopeChanged", payload: scope })
                }
                onWorklistFilterChange={(worklist) =>
                  dispatch({
                    type: "worklistFilterChanged",
                    payload: worklist,
                  })
                }
                onSortOrderChange={(sort) =>
                  dispatch({ type: "sortOrderChanged", payload: sort })
                }
                open={utilityPanel === "filters"}
                priorityFilter={state.priorityFilter}
                queueScope={state.queueScope}
                worklistFilter={state.worklistFilter}
                sortOrder={state.sortOrder}
              />
              {accessAdminVisible ? (
                <AccessManager
                  busy={inviteBusy}
                  error={inviteError}
                  invites={invites}
                  onOpenChange={(open) =>
                    setUtilityPanel(open ? "access" : null)
                  }
                  onInvite={(payload) => {
                    void handleInviteConsoleUser(payload);
                  }}
                  open={utilityPanel === "access"}
                />
              ) : null}
              <NotificationCenter
                authenticated={!!session.profile}
                busy={notificationBusy}
                error={notificationError}
                notifications={notifications}
                onMarkRead={(notificationId) => {
                  void handleMarkNotificationRead(notificationId);
                }}
                onOpenChange={(open) =>
                  setUtilityPanel(open ? "notifications" : null)
                }
                onSend={(payload) => {
                  void handleSendNotification(payload);
                }}
                open={utilityPanel === "notifications"}
                profileName={session.profile?.display_name}
                selectedItem={selectedItem}
              />
            </div>
          }
        />
        <WorkspaceFrame
          actions={
            <Suspense fallback={<PanelLoadingFallback label="Review actions" />}>
              {rightPanel}
            </Suspense>
          }
          actionsHeader={
            <WorkspaceTabBar
              activeWorkspace={state.workspace}
              onWorkspaceChange={(workspace) =>
                dispatch({ type: "workspaceChanged", payload: workspace })
              }
            />
          }
          brief={
            <Suspense fallback={<PanelLoadingFallback label="Event brief" />}>
              {centerPanel}
            </Suspense>
          }
          briefHeader={
            <CenterTabBar
              activeTab={state.middleTab}
              onTabChange={(tab) =>
                dispatch({ type: "middleTabChanged", payload: tab })
              }
              restrictedIntelVisible={restrictedIntelVisible}
            />
          }
          queue={
            <QueuePanel
              createOpen={manualEventOpen}
              createBusy={manualEventBusy}
              createError={manualEventError}
              loadError={state.loadError}
              onCreateOpenChange={setManualEventOpen}
              onCreateManualEvent={(payload) => handleCreateManualEvent(payload)}
              onQueueScopeChange={(scope) =>
                dispatch({ type: "queueScopeChanged", payload: scope })
              }
              onWorklistFilterChange={(worklist) =>
                dispatch({
                  type: "worklistFilterChanged",
                  payload: worklist,
                })
              }
              onSelect={(id) => dispatch({ type: "selected", payload: id })}
              queueHealth={{
                publishReady: queueHealth.publishReady,
                corroborate: queueHealth.corroborate,
                registry: queueHealth.registry,
              }}
              queueScope={state.queueScope}
              worklistFilter={state.worklistFilter}
              rows={visibleQueue}
              selectedId={selectedItem?.event_id ?? null}
            />
          }
        />
      </div>
    </div>
  );
}
