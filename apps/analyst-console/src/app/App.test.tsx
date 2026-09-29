import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getSessionProfile,
  hasConsoleRecoveryToken,
  requestConsolePasswordReset,
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
import { loadEventEdits, loadRecentRegistryEdits } from "@/lib/api/audit-reads";
import { loadConsoleWorkspace } from "@/lib/api/load-console-workspace";
import {
  createManualEvent,
  markEventReadyForRelease,
  saveEventEdit,
  saveRegistryEdit,
  withholdEventFromRelease,
} from "@/lib/api/review-actions";
import { App } from "./App";

vi.mock("@/lib/api/console-auth", () => ({
  getSessionProfile: vi.fn(),
  hasConsoleRecoveryToken: vi.fn(),
  registerConsoleUser: vi.fn(),
  requestConsolePasswordReset: vi.fn(),
  signInConsoleUser: vi.fn(),
  signOutConsoleUser: vi.fn(),
  subscribeToAuthChanges: vi.fn(),
  updateConsolePassword: vi.fn(),
}));

vi.mock("@/lib/api/console-invites", () => ({
  loadConsoleInvites: vi.fn(),
  inviteConsoleUser: vi.fn(),
}));

vi.mock("@/lib/api/load-console-workspace", () => ({
  loadConsoleWorkspace: vi.fn(),
}));

vi.mock("@/lib/api/console-notifications", () => ({
  loadConsoleNotifications: vi.fn(),
  sendConsoleNotification: vi.fn(),
  markConsoleNotificationRead: vi.fn(),
}));

vi.mock("@/lib/api/audit-reads", () => ({
  loadEventEdits: vi.fn(),
  loadRecentRegistryEdits: vi.fn(),
}));

vi.mock("@/lib/api/review-actions", () => ({
  saveEventEdit: vi.fn(),
  createManualEvent: vi.fn(),
  markEventReadyForRelease: vi.fn(),
  withholdEventFromRelease: vi.fn(),
  saveRegistryEdit: vi.fn(),
}));

const reviewRows = [
  {
    event_id: "evt-1",
    headline: "Alpha review item",
    country: "Colombia",
    event_date: "2026-06-01",
    event_type: "reform",
    summary:
      "Alpha summary keeps the review decision surface anchored in the active event.",
    source_primary: "InSight Crime",
    review_priority: "high" as const,
    publication_status: "withheld" as const,
    publication_label: "Withheld",
    publication_reason: "low_confidence_requires_human_review",
    publication_ready: false,
    reviewed_by_human: false,
    qa_flag_count: 1,
    duplicate_candidate_count: 0,
    council_disagreement_summary: "aligned",
    supervision_reasons: [
      "qa_flags",
      "high_salience_unreviewed",
      "publication_corroboration_needed",
    ],
    council_recommended_actions: [
      {
        code: "human_corroboration",
        priority: "high" as const,
        reason: "Low-confidence event should be corroborated before publication.",
      },
    ],
    qa_flags: [
      {
        flag_id: "flag-1",
        severity: "high",
        code: "missing_url",
        message: "Primary source URL is missing.",
      },
    ],
    provenance: {
      linked_reports: [
        {
          article_id: "article-1",
          source_name: "InSight Crime",
          report_role: "primary",
          headline: "Alpha review item corroboration brief",
          description:
            "Source dossier material for the selected Alpha event remains inline in the brief panel.",
        },
      ],
      timeline: [
        {
          stage: "ingestion",
          label: "Source ingestion",
          status: "completed",
          at: "2026-06-01T05:00:00Z",
        },
      ],
    },
  },
  {
    event_id: "evt-2",
    headline: "Beta review item",
    country: "Mexico",
    event_date: "2026-06-02",
    event_type: "aid",
    review_priority: "low" as const,
    publication_status: "published" as const,
    publication_label: "Published",
  },
];

const workspacePayload = {
  queue: reviewRows,
  councilByEvent: {
    "evt-1": {
      event_id: "evt-1",
      country: "Colombia",
      analyses: {
        synthesis: {
          assessment: "AI synthesis assessment for Colombia.",
          public_analysis: "AI synthesis public analysis for the selected event.",
          risk_level: "high",
          confidence: 0.81,
        },
      },
    },
  },
  countriesByName: {
    colombia: {
      country: "Colombia",
      predictive_summary: {
        overall_risk_level: "guarded",
        overall_risk_score: 48.1,
        leading_label: "Regime Vulnerability",
        leading_trend: "rising",
        summary_text: "Country brief summary for Colombia.",
        watchpoints: ["Watchpoint one", "Watchpoint two"],
      },
      monitors: [
        {
          code: "cmr_balance",
          label: "Civil-Military Stress",
          goal: "Track military political influence.",
          composite_score: 44.3,
          trend_label: "rising",
        },
      ],
      risk_constructs: [
        {
          code: "regime_vulnerability",
          label: "Regime Vulnerability",
          score: 52.4,
          level: "guarded",
          summary_text: "Construct summary.",
        },
      ],
    },
  },
  registryActors: [
    {
      registry_id: "actor-colombia-army",
      canonical_name: "National Army of Colombia",
      canonical_type: "state_actor",
      primary_country: "Colombia",
      registry_status: "registry_confirmed",
    },
  ],
  source: "supabase" as const,
};

describe("App shell bootstrap", () => {
  beforeEach(() => {
    vi.mocked(getSessionProfile).mockResolvedValue({
      id: "user-1",
      display_name: "Analyst One",
      email: "analyst@example.com",
      role: "analyst",
      active: true,
    });
    vi.mocked(hasConsoleRecoveryToken).mockReturnValue(false);
    vi.mocked(subscribeToAuthChanges).mockReturnValue(() => {});
    vi.mocked(loadConsoleWorkspace).mockResolvedValue(workspacePayload);
    vi.mocked(loadEventEdits).mockResolvedValue([
      {
        edit_id: "edit-1",
        event_id: "evt-1",
        editor_name: "Analyst One",
        editor_role: "analyst",
        edited_at: "2026-06-05T12:00:00Z",
        status: "saved",
        comment: "Saved for audit.",
      },
    ]);
    vi.mocked(loadRecentRegistryEdits).mockResolvedValue([
      {
        registry_edit_id: "reg-1",
        action: "upsert_registry_entry",
        editor_name: "Analyst One",
        editor_role: "analyst",
        created_at: "2026-06-05T12:10:00Z",
      },
    ]);
    vi.mocked(loadConsoleNotifications).mockResolvedValue([
      {
        notification_id: "note-1",
        event_id: "evt-1",
        recipient_role: "ra",
        subject: "Queue item updated",
        message: "Please verify the source and actor coding.",
        sender_name: "Analyst One",
        sender_role: "analyst",
        created_at: "2026-06-05T12:15:00Z",
        read_at: null,
      },
    ]);
    vi.mocked(loadConsoleInvites).mockResolvedValue([
      {
        invite_id: "invite-1",
        invited_email: "ra-1@example.com",
        invited_display_name: "RA One",
        invited_role: "ra",
        inviter_name: "Analyst One",
        inviter_role: "admin",
        status: "invited",
        invited_at: "2026-06-05T11:00:00Z",
        last_sent_at: "2026-06-05T11:00:00Z",
      },
    ]);
    vi.mocked(saveEventEdit).mockResolvedValue({ ok: true });
    vi.mocked(createManualEvent).mockResolvedValue({
      ok: true,
      manual_event: {
        submission_id: "manual-submission-1",
        headline: "Manual draft event",
        country: "Peru",
        event_date: "2026-06-05",
        event_type: "reform",
        summary: "Manual queue draft.",
        source_primary: "Manual submission",
        confidence: "medium",
        salience: "medium",
        review_priority: "high",
        editor_name: "Analyst One",
        created_at: "2026-06-05T13:00:00Z",
        status: "manual_submitted",
      },
    });
    vi.mocked(markEventReadyForRelease).mockResolvedValue({ ok: true });
    vi.mocked(withholdEventFromRelease).mockResolvedValue({ ok: true });
    vi.mocked(saveRegistryEdit).mockResolvedValue({ ok: true });
    vi.mocked(sendConsoleNotification).mockResolvedValue({ ok: true });
    vi.mocked(markConsoleNotificationRead).mockResolvedValue({ ok: true });
    vi.mocked(inviteConsoleUser).mockResolvedValue({ ok: true });
    vi.mocked(requestConsolePasswordReset).mockResolvedValue(undefined);
    vi.mocked(signOutConsoleUser).mockResolvedValue(undefined);
    vi.mocked(updateConsolePassword).mockResolvedValue(undefined);
  });

  it("renders the operable console shell with active navigation and tabs", async () => {
    render(<App />);

    expect(
      await screen.findByRole("banner", { name: /sentinel analyst console/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("search", { name: /console search/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("main", { name: /analyst workspace/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /ai analysis/i }),
    ).toBeEnabled();
    expect(
      screen.getByRole("button", { name: /country brief/i }),
    ).toBeEnabled();
  });

  it("moves the session profile into the left rail account badge", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(await screen.findByRole("button", { name: /open profile/i }));

    const profilePanel = screen.getByRole("region", { name: /user profile/i });
    expect(within(profilePanel).getByText(/analyst one/i)).toBeInTheDocument();
    expect(within(profilePanel).getByText(/analyst@example.com/i)).toBeInTheDocument();
    expect(within(profilePanel).getByText(/^analyst$/i)).toBeInTheDocument();

    await user.click(within(profilePanel).getByRole("button", { name: /sign out/i }));

    await waitFor(() => {
      expect(signOutConsoleUser).toHaveBeenCalledTimes(1);
    });
  });

  it("shows an authentication gate before the console for signed-out users", async () => {
    vi.mocked(getSessionProfile).mockResolvedValueOnce(null);

    render(<App />);

    expect(await screen.findByText(/restricted workspace/i)).toBeInTheDocument();
    expect(screen.getByText(/^sentinel$/i)).toBeInTheDocument();
    expect(screen.getByText(/^analyst console$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /forgot password/i })).toBeInTheDocument();
    expect(screen.getByText(/contact a sentinel admin for an invitation/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^register$/i })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/display name/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("main", { name: /analyst workspace/i })).not.toBeInTheDocument();
  });

  it("sends a password reset email from the auth gate", async () => {
    vi.mocked(getSessionProfile).mockResolvedValueOnce(null);

    const user = userEvent.setup();
    render(<App />);

    await user.type(
      await screen.findByPlaceholderText(/email/i),
      "analyst@example.com",
    );
    await user.click(screen.getByRole("button", { name: /forgot password/i }));

    await waitFor(() => {
      expect(requestConsolePasswordReset).toHaveBeenCalledWith(
        "analyst@example.com",
        expect.any(String),
      );
    });
  });

  it("keeps the brief aligned with the filtered queue selection", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(await screen.findByRole("button", { name: /beta review item/i }));

    expect(screen.getByRole("region", { name: /event brief/i })).toHaveTextContent(
      "Beta review item",
    );

    await user.clear(screen.getByPlaceholderText(/search events, countries, ids/i));
    await user.type(
      screen.getByPlaceholderText(/search events, countries, ids/i),
      "colombia",
    );

    expect(
      screen.queryByRole("button", { name: /beta review item/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: /event brief/i })).toHaveTextContent(
      "Alpha review item",
    );
  });

  it("shows AI analysis and country brief for elevated roles", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(await screen.findByRole("button", { name: /ai analysis/i }));
    expect(
      await within(
        screen.getByRole("region", { name: /event brief/i }),
      ).findByText(/ai synthesis public analysis/i),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /country brief/i }));
    expect(
      await within(
        screen.getByRole("region", { name: /event brief/i }),
      ).findByText(/country brief summary for colombia/i),
    ).toBeInTheDocument();
  });

  it("shows queue-wide review-now filtering and shared AI verification cues", async () => {
    const user = userEvent.setup();

    render(<App />);

    expect(await screen.findByText(/AI verification cues/i)).toBeInTheDocument();
    expect(screen.getByText(/human review pending/i)).toBeInTheDocument();
    expect(screen.getByText(/human corroboration/i)).toBeInTheDocument();

    const queueRegion = screen.getByRole("complementary", { name: /review queue/i });
    await user.click(within(queueRegion).getAllByRole("button", { name: /review now/i })[0]);

    expect(screen.queryByRole("button", { name: /beta review item/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /alpha review item/i })).toBeInTheDocument();
  });

  it("saves event edits through the review workspace", async () => {
    const user = userEvent.setup();

    render(<App />);

    const actionsRegion = (
      await screen.findAllByRole("region", { name: /review actions/i })
    )[0];
    const panel = within(actionsRegion).getByText(/review edits/i).closest("section");

    expect(panel).not.toBeNull();

    const headlineInput = (panel as HTMLElement).querySelector(
      'input[type="text"]',
    ) as HTMLInputElement | null;

    expect(headlineInput).not.toBeNull();

    await user.click(headlineInput as HTMLInputElement);
    await user.keyboard("{Meta>}a{/Meta}{Backspace}");
    await user.type(
      headlineInput as HTMLInputElement,
      "Retitled Alpha event",
    );
    await user.type(
      within(panel as HTMLElement).getByLabelText(/analyst note/i),
      "Updated title.",
    );
    await user.click(
      within(panel as HTMLElement).getByRole("button", { name: /save event edit/i }),
    );

    await waitFor(() => {
      expect(saveEventEdit).toHaveBeenCalledTimes(1);
    });

    const payload = vi.mocked(saveEventEdit).mock.calls[0]?.[0];
    expect(payload?.event_id).toBe("evt-1");
    expect(payload?.comment).toBe("Updated title.");
    expect(String((payload?.patch as Record<string, unknown>)?.headline || "")).toContain(
      "Retitled Alpha event",
    );
  });

  it("gates release decisions for RA users while still allowing navigation", async () => {
    vi.mocked(getSessionProfile).mockResolvedValueOnce({
      id: "user-ra",
      display_name: "RA User",
      email: "ra@example.com",
      role: "ra",
      active: true,
    });

    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: /release/i }));

    expect(
      await within(
        screen.getByRole("region", { name: /review actions/i }),
      ).findByText(/release decisions are limited to analysts and admins/i),
    ).toBeInTheDocument();
    expect(markEventReadyForRelease).not.toHaveBeenCalled();
  });

  it("keeps release ready actions disabled until the publish checklist is complete", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: /release/i }));

    const releaseRegion = screen.getByRole("region", { name: /review actions/i });
    expect(await within(releaseRegion).findByText(/publish checklist/i)).toBeInTheDocument();
    expect(
      within(releaseRegion).getByText(/finish the checklist in edit, audit, or registry/i),
    ).toBeInTheDocument();
    expect(
      within(releaseRegion).getByRole("button", { name: /mark ready for release/i }),
    ).toBeDisabled();
  });

  it("opens the registry workspace and submits a registry request", async () => {
    const user = userEvent.setup();

    render(<App />);

    const registryButtons = await screen.findAllByRole("button", {
      name: /^registry$/i,
    });
    await user.click(registryButtons.at(-1) as HTMLButtonElement);

    const region = screen.getByRole("region", { name: /review actions/i });
    await user.type(
      await within(region).findByLabelText(/canonical name/i),
      "Army Intelligence Directorate",
    );
    await user.type(
      within(region).getByLabelText(/request note/i),
      "Needs durable registry entry.",
    );
    await user.click(within(region).getByRole("button", { name: /submit registry request/i }));

    await waitFor(() => {
      expect(saveRegistryEdit).toHaveBeenCalledWith(
        expect.objectContaining({
          action: "upsert_registry_entry",
          canonical_name: "Army Intelligence Directorate",
          primary_country: "Colombia",
          note: "Needs durable registry entry.",
        }),
      );
    });
  });

  it("adds a manual event into the review queue", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(await screen.findByRole("button", { name: /^add$/i }));
    const createPanel = screen.getByText(/add manual event/i).closest("form");

    expect(createPanel).not.toBeNull();

    await user.type(
      within(createPanel as HTMLElement).getByLabelText(/headline/i),
      "Manual draft event",
    );
    await user.type(
      within(createPanel as HTMLElement).getByLabelText(/^country$/i),
      "Peru",
    );
    await user.type(
      within(createPanel as HTMLElement).getByLabelText(/^summary$/i),
      "Manual queue draft.",
    );
    await user.selectOptions(
      within(createPanel as HTMLElement).getByLabelText(/^priority$/i),
      "high",
    );
    await user.click(
      within(createPanel as HTMLElement).getByRole("button", {
        name: /add to queue/i,
      }),
    );

    await waitFor(() => {
      expect(createManualEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          headline: "Manual draft event",
          country: "Peru",
          summary: "Manual queue draft.",
          review_priority: "high",
        }),
      );
    });

    expect(screen.getByRole("button", { name: /manual draft event/i })).toBeInTheDocument();
  });

  it("opens notifications and sends an event-linked message", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /notifications and messages/i }),
    );

    const dialog = screen.getByRole("region", {
      name: /notifications and messages/i,
    });

    await user.selectOptions(within(dialog).getByLabelText(/audience/i), "ra");
    await user.selectOptions(within(dialog).getByLabelText(/assignment/i), "corroborate");
    await user.selectOptions(within(dialog).getByLabelText(/^due$/i), "today");
    await user.clear(within(dialog).getByLabelText(/subject/i));
    await user.type(
      within(dialog).getByLabelText(/subject/i),
      "Please review the updated Colombia event",
    );
    await user.clear(within(dialog).getByRole("textbox", { name: /^message$/i }));
    await user.type(
      within(dialog).getByRole("textbox", { name: /^message$/i }),
      "Headline and summary changed after corroboration.",
    );
    await user.click(
      within(dialog).getByRole("button", { name: /send notification/i }),
    );

    await waitFor(() => {
        expect(sendConsoleNotification).toHaveBeenCalledWith(
          expect.objectContaining({
            recipient_role: "ra",
            event_id: "evt-1",
            subject: "Please review the updated Colombia event",
            message: "Headline and summary changed after corroboration.",
            metadata: expect.objectContaining({
              assignment_type: "corroborate",
              due_window: "today",
              country: "Colombia",
            }),
          }),
        );
    });
  });

  it("lets admins send invitation emails from the access manager", async () => {
    vi.mocked(getSessionProfile).mockResolvedValueOnce({
      id: "user-admin",
      display_name: "Admin User",
      email: "admin@example.com",
      role: "admin",
      active: true,
    });

    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /access and invitations/i }),
    );

    const dialog = screen.getByRole("region", {
      name: /access and invitations/i,
    });

    expect(within(dialog).getByText(/ra one/i)).toBeInTheDocument();

    await user.type(within(dialog).getByLabelText(/^email$/i), "new-ra@example.com");
    await user.type(within(dialog).getByLabelText(/display name/i), "New RA");
    await user.selectOptions(within(dialog).getByLabelText(/^role$/i), "ra");
    await user.click(
      within(dialog).getByRole("button", { name: /send invitation/i }),
    );

    await waitFor(() => {
      expect(inviteConsoleUser).toHaveBeenCalledWith(
        expect.objectContaining({
          email: "new-ra@example.com",
          display_name: "New RA",
          role: "ra",
        }),
      );
    });
  });

  it("opens queue filters from the header and applies review-now, country, and category filters", async () => {
    const user = userEvent.setup();

    render(<App />);

    await user.click(await screen.findByRole("button", { name: /open filters/i }));

    const dialog = screen.getByRole("region", { name: /queue filters/i });
    await user.click(within(dialog).getByRole("button", { name: /review now/i }));
    await user.click(within(dialog).getByRole("button", { name: /^Colombia$/i }));
    await user.click(within(dialog).getByRole("button", { name: /^reform$/i }));

    expect(
      screen.queryByRole("button", { name: /beta review item/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /alpha review item/i })).toBeInTheDocument();
    const header = screen.getByRole("banner", { name: /sentinel analyst console/i });
    expect(within(header).getByText(/active filters/i)).toBeInTheDocument();
    expect(
      within(header).getByRole("button", { name: /country: colombia/i }),
    ).toBeInTheDocument();
    expect(
      within(header).getByRole("button", { name: /category: reform/i }),
    ).toBeInTheDocument();
  });

  it("surfaces AI provenance and country watch context in the brief", async () => {
    render(<App />);

    expect(await screen.findByText(/ai provenance/i)).toBeInTheDocument();
    expect(screen.getByText(/ai synthesis public analysis for the selected event/i)).toBeInTheDocument();
    expect(screen.getByText(/country watch/i)).toBeInTheDocument();
    expect(screen.getByText(/country brief summary for colombia/i)).toBeInTheDocument();
    expect(screen.getByText(/watchpoint one/i)).toBeInTheDocument();
  });

  it("shows pending edit diff feedback while analysts edit a record", async () => {
    const user = userEvent.setup();

    render(<App />);

    const actionsRegion = (
      await screen.findAllByRole("region", { name: /review actions/i })
    )[0];
    const panel = within(actionsRegion).getByText(/review edits/i).closest("section");

    expect(panel).not.toBeNull();

    expect(within(panel as HTMLElement).getByText(/no unsaved field changes yet/i)).toBeInTheDocument();

    const headlineInput = within(panel as HTMLElement).getByLabelText(
      /^headline$/i,
    );

    await user.click(headlineInput);
    await user.clear(headlineInput);
    await user.type(headlineInput, "Reframed Alpha event");

    expect(within(panel as HTMLElement).getByText(/pending edit diff/i)).toBeInTheDocument();
    expect(within(panel as HTMLElement).getByText(/reframed alpha event/i)).toBeInTheDocument();
  });

  it("keeps access and notifications mutually exclusive", async () => {
    vi.mocked(getSessionProfile).mockResolvedValueOnce({
      id: "user-admin",
      display_name: "Admin User",
      email: "admin@example.com",
      role: "admin",
      active: true,
    });

    const user = userEvent.setup();
    render(<App />);

    await user.click(
      await screen.findByRole("button", { name: /access and invitations/i }),
    );
    expect(
      screen.getByRole("region", { name: /access and invitations/i }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /notifications and messages/i }));

    expect(
      screen.getByRole("region", { name: /notifications and messages/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: /access and invitations/i }),
    ).not.toBeInTheDocument();
  });

  it("keeps filters and notifications mutually exclusive", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(await screen.findByRole("button", { name: /open filters/i }));
    expect(screen.getByRole("region", { name: /queue filters/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /notifications and messages/i }));

    expect(
      screen.getByRole("region", { name: /notifications and messages/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("region", { name: /queue filters/i }),
    ).not.toBeInTheDocument();
  });

  it("surfaces queue load errors in the queue region", async () => {
    vi.mocked(loadConsoleWorkspace).mockRejectedValue(
      new Error("Failed to load review workspace: 503"),
    );

    render(<App />);

    expect(
      await screen.findByText("Failed to load review workspace: 503"),
    ).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: /review queue/i })).toHaveTextContent(
      "Failed to load review workspace: 503",
    );
  });
});
