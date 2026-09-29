import { withSupabase } from "npm:@supabase/server";
import { createClient } from "npm:@supabase/supabase-js@2";

import { corsHeaders } from "../_shared/cors.ts";

type JsonObject = Record<string, unknown>;
type ProfileRow = {
  display_name: string | null;
  role: string | null;
  active: boolean;
  email: string | null;
};

const EVENT_EDIT_SELECT =
  "edit_id,event_id,editor_name,editor_role,edited_at,status,comment,patch,actor_patches";
const QA_RESOLUTION_SELECT =
  "resolution_id,flag_id,event_id,editor_name,editor_role,resolved_at,status,comment,resolution_type";
const DUPLICATE_RESOLUTION_SELECT =
  "resolution_id,candidate_id,keeper_event_id,merged_event_ids,event_ids,reason_code,manual,keeper_patch,editor_name,editor_role,resolved_at,status,comment";
const REGISTRY_EDIT_SELECT =
  "registry_edit_id,action,payload,editor_name,editor_role,created_at";
const MANUAL_EVENT_SELECT =
  "submission_id,headline,country,event_date,event_type,summary,source_primary,confidence,salience,review_priority,location,status,editor_name,editor_role,created_at";
const NOTIFICATION_SELECT =
  "notification_id,event_id,recipient_role,subject,message,sender_name,sender_role,created_at,read_at,metadata";
const INVITE_SELECT =
  "invite_id,invited_user_id,invited_email,invited_display_name,invited_role,inviter_name,inviter_role,status,redirect_to,invited_at,last_sent_at,accepted_at,metadata";
const RELEASE_STATUSES = new Set([
  "ready_for_release",
  "withheld",
  "published",
  "release_approved",
]);
const NOTIFICATION_RECIPIENT_ROLES = new Set([
  "ra",
  "analyst",
  "coordinator",
  "admin",
]);
const INVITE_ROLES = new Set([
  "ra",
  "analyst",
  "admin",
]);

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function isObject(value: unknown): value is JsonObject {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function asObject(value: unknown): JsonObject {
  return isObject(value) ? value : {};
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function asEmail(value: unknown): string | null {
  const email = asString(value)?.toLowerCase() ?? null;
  if (!email || !email.includes("@")) {
    return null;
  }
  return email;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
}

function asBoolean(value: unknown): boolean {
  return value === true;
}

function asNullableJsonObject(value: unknown): JsonObject {
  return isObject(value) ? value : {};
}

function asJsonArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function canPublishRole(role: string | null): boolean {
  return role === "analyst" || role === "coordinator" || role === "admin";
}

function canAdministerAccessRole(role: string | null): boolean {
  return role === "admin";
}

function createAdminSupabaseClient() {
  const url = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!url || !serviceRoleKey) {
    throw new Error("missing_service_role_config");
  }

  return createClient(url, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}

function touchesReleaseState(payload: JsonObject): boolean {
  const status = asString(payload.status);
  const patch = asObject(payload.patch);

  if (status && RELEASE_STATUSES.has(status)) {
    return true;
  }

  if (asString(patch.publication_status) || patch.publication_ready !== undefined) {
    return true;
  }

  return false;
}

Deno.serve(
  withSupabase({ auth: "user" }, async (req, ctx) => {
    if (req.method === "OPTIONS") {
      return new Response("ok", { headers: corsHeaders });
    }

    if (req.method === "GET") {
      return json({
        ok: true,
        function: "review-action",
        supported_actions: [
          "event_edit",
          "qa_resolution",
          "duplicate_resolution",
          "registry_edit",
          "manual_event",
          "invite_console_user",
          "send_notification",
          "notification_read",
        ],
      });
    }

    if (req.method !== "POST") {
      return json({ error: "method_not_allowed" }, 405);
    }

    const userId = ctx.userClaims?.id;
    if (!userId) {
      return json({ error: "authentication_required" }, 401);
    }

    const supabase = ctx.supabase as any;
    const { data: profileData, error: profileError, status: profileStatus } = await supabase
      .from("profiles")
      .select("display_name, role, active, email")
      .eq("id", userId)
      .maybeSingle();
    const profile = (profileData as ProfileRow | null) || null;
    if (profileError && profileStatus !== 406) {
      return json({ error: profileError.message }, 500);
    }
    if (!profile?.active) {
      return json({ error: "inactive_profile" }, 403);
    }

    const body = asObject(await req.json().catch(() => ({})));
    const action = asString(body.action);
    const payload = asObject(body.payload);
    const editorName =
      asString(profile.display_name) ||
      asString(profile.email) ||
      asString(ctx.userClaims?.email) ||
      "Analyst";
    const editorRole = asString(profile.role) || "analyst";
    const nowIso = new Date().toISOString();

    if (!action) {
      return json({ error: "missing_action" }, 400);
    }

    if (action === "event_edit") {
      if (touchesReleaseState(payload) && !canPublishRole(editorRole)) {
        return json({ error: "insufficient_publish_permissions" }, 403);
      }

      const row = {
        event_id: asString(payload.event_id),
        editor_user_id: userId,
        editor_name: editorName,
        editor_role: editorRole,
        edited_at: nowIso,
        status: asString(payload.status) || "saved",
        comment: asString(payload.comment),
        patch: asNullableJsonObject(payload.patch),
        actor_patches: asJsonArray(payload.actor_patches),
      };
      if (!row.event_id) {
        return json({ error: "missing_event_id" }, 400);
      }
      const { data, error } = await supabase
        .from("event_edits")
        .insert(row)
        .select(EVENT_EDIT_SELECT)
        .single();
      if (error) {
        return json({ error: error.message }, 400);
      }
      return json({ ok: true, edit: data, warnings: [] }, 201);
    }

    if (action === "qa_resolution") {
      const row = {
        flag_id: asString(payload.flag_id),
        event_id: asString(payload.event_id),
        editor_user_id: userId,
        editor_name: editorName,
        editor_role: editorRole,
        resolved_at: nowIso,
        status: asString(payload.status) || "resolved",
        comment: asString(payload.comment),
        resolution_type: asString(payload.resolution_type) || "manual_fix",
      };
      if (!row.flag_id || !row.event_id) {
        return json({ error: "missing_resolution_fields" }, 400);
      }
      const { data, error } = await supabase
        .from("qa_resolutions")
        .insert(row)
        .select(QA_RESOLUTION_SELECT)
        .single();
      if (error) {
        return json({ error: error.message }, 400);
      }
      return json({ ok: true, qa_resolution: data }, 201);
    }

    if (action === "duplicate_resolution") {
      const row = {
        candidate_id: asString(payload.candidate_id),
        keeper_event_id: asString(payload.keeper_event_id),
        merged_event_ids: asStringArray(payload.merged_event_ids),
        event_ids: asStringArray(payload.event_ids),
        reason_code: asString(payload.reason_code),
        manual: asBoolean(payload.manual),
        keeper_patch: asNullableJsonObject(payload.keeper_patch),
        editor_user_id: userId,
        editor_name: editorName,
        editor_role: editorRole,
        resolved_at: nowIso,
        status: asString(payload.status) || "merged",
        comment: asString(payload.comment),
      };
      if (!row.candidate_id) {
        return json({ error: "missing_candidate_id" }, 400);
      }
      const { data, error } = await supabase
        .from("duplicate_resolutions")
        .insert(row)
        .select(DUPLICATE_RESOLUTION_SELECT)
        .single();
      if (error) {
        return json({ error: error.message }, 400);
      }
      return json({ ok: true, duplicate_resolution: data }, 201);
    }

    if (action === "registry_edit") {
      const row = {
        action: asString(payload.action) || "registry_edit",
        payload,
        editor_user_id: userId,
        editor_name: editorName,
        editor_role: editorRole,
      };
      const { data, error } = await supabase
        .from("registry_edits")
        .insert(row)
        .select(REGISTRY_EDIT_SELECT)
        .single();
      if (error) {
        return json({ error: error.message }, 400);
      }
      return json({ ok: true, registry_edit: data }, 201);
    }

    if (action === "manual_event") {
      const row = {
        headline: asString(payload.headline),
        country: asString(payload.country),
        event_date: asString(payload.event_date),
        event_type: asString(payload.event_type),
        summary: asString(payload.summary),
        source_primary: asString(payload.source_primary),
        confidence: asString(payload.confidence) || "medium",
        salience: asString(payload.salience) || "medium",
        review_priority: asString(payload.review_priority) || "medium",
        location: asString(payload.location),
        status: "manual_submitted",
        note: asString(payload.note),
        editor_user_id: userId,
        editor_name: editorName,
        editor_role: editorRole,
      };
      if (!row.headline) {
        return json({ error: "missing_manual_event_headline" }, 400);
      }
      const { data, error } = await supabase
        .from("manual_event_submissions")
        .insert(row)
        .select(MANUAL_EVENT_SELECT)
        .single();
      if (error) {
        return json({ error: error.message }, 400);
      }
      return json({ ok: true, manual_event: data }, 201);
    }

    if (action === "send_notification") {
      const recipientRole = asString(payload.recipient_role);
      const subject = asString(payload.subject);
      const message = asString(payload.message);

      if (!recipientRole || !NOTIFICATION_RECIPIENT_ROLES.has(recipientRole)) {
        return json({ error: "invalid_recipient_role" }, 400);
      }

      if (!subject || !message) {
        return json({ error: "missing_notification_fields" }, 400);
      }

      const row = {
        event_id: asString(payload.event_id),
        recipient_role: recipientRole,
        subject,
        message,
        metadata: asNullableJsonObject(payload.metadata),
        sender_user_id: userId,
        sender_name: editorName,
        sender_role: editorRole,
      };

      const { data, error } = await supabase
        .from("console_notifications")
        .insert(row)
        .select(NOTIFICATION_SELECT)
        .single();
      if (error) {
        return json({ error: error.message }, 400);
      }
      return json({ ok: true, notification: data }, 201);
    }

    if (action === "invite_console_user") {
      if (!canAdministerAccessRole(editorRole)) {
        return json({ error: "admin_required" }, 403);
      }

      const invitedEmail = asEmail(payload.email);
      const invitedRole = asString(payload.role) || "ra";
      const invitedDisplayName = asString(payload.display_name);
      const redirectTo = asString(payload.redirect_to);

      if (!invitedEmail) {
        return json({ error: "missing_invited_email" }, 400);
      }

      if (!INVITE_ROLES.has(invitedRole)) {
        return json({ error: "invalid_invited_role" }, 400);
      }

      let adminSupabase;
      try {
        adminSupabase = createAdminSupabaseClient();
      } catch (error: unknown) {
        return json(
          {
            error:
              error instanceof Error
                ? error.message
                : "missing_service_role_config",
          },
          500,
        );
      }

      const inviteOptions: {
        data?: Record<string, unknown>;
        redirectTo?: string;
      } = {};

      if (invitedDisplayName) {
        inviteOptions.data = { display_name: invitedDisplayName };
      }

      if (redirectTo) {
        inviteOptions.redirectTo = redirectTo;
      }

      const { data: inviteData, error: inviteError } =
        await adminSupabase.auth.admin.inviteUserByEmail(
          invitedEmail,
          inviteOptions,
        );

      if (inviteError) {
        return json({ error: inviteError.message }, 400);
      }

      const invitedUserId = inviteData.user?.id ?? null;

      if (invitedUserId) {
        const { error: profileUpsertError } = await adminSupabase
          .from("profiles")
          .upsert(
            {
              id: invitedUserId,
              email: invitedEmail,
              display_name:
                invitedDisplayName || inviteData.user?.email?.split("@")[0] || "Analyst",
              role: invitedRole,
              active: true,
            },
            { onConflict: "id" },
          );

        if (profileUpsertError) {
          return json({ error: profileUpsertError.message }, 400);
        }
      }

      const inviteRecord = {
        invited_user_id: invitedUserId,
        invited_email: invitedEmail,
        invited_display_name: invitedDisplayName,
        invited_role: invitedRole,
        inviter_user_id: userId,
        inviter_name: editorName,
        inviter_role: editorRole,
        status: "invited",
        redirect_to: redirectTo,
        invited_at: nowIso,
        last_sent_at: nowIso,
        accepted_at: null,
        metadata: {
          source: "analyst-console",
          ...(asNullableJsonObject(payload.metadata) ?? {}),
        },
      };

      const { data, error } = await adminSupabase
        .from("console_user_invites")
        .upsert(inviteRecord, { onConflict: "invited_email" })
        .select(INVITE_SELECT)
        .single();

      if (error) {
        return json({ error: error.message }, 400);
      }

      return json({ ok: true, invite: data }, 201);
    }

    if (action === "notification_read") {
      const notificationId = asString(payload.notification_id);
      if (!notificationId) {
        return json({ error: "missing_notification_id" }, 400);
      }

      const { data, error } = await supabase
        .from("console_notifications")
        .update({ read_at: nowIso })
        .eq("notification_id", notificationId)
        .select(NOTIFICATION_SELECT)
        .single();
      if (error) {
        return json({ error: error.message }, 400);
      }
      return json({ ok: true, notification: data }, 200);
    }

    return json({ error: "unsupported_action" }, 404);
  }),
);
