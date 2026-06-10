import { supabase } from "@/lib/supabase/client";
import type { ConsoleUserInviteRecord, InviteRole } from "@/lib/domain/types";

const INVITE_SELECT =
  "invite_id,invited_user_id,invited_email,invited_display_name,invited_role,inviter_name,inviter_role,status,redirect_to,invited_at,last_sent_at,accepted_at,metadata";

export async function loadConsoleInvites(): Promise<ConsoleUserInviteRecord[]> {
  const { data, error } = await supabase
    .from("console_user_invites")
    .select(INVITE_SELECT)
    .order("last_sent_at", { ascending: false });

  if (error) {
    throw error;
  }

  return (data as ConsoleUserInviteRecord[] | null) ?? [];
}

export async function inviteConsoleUser(payload: {
  email: string;
  display_name?: string;
  role: InviteRole;
  redirect_to?: string;
}): Promise<{ ok?: boolean; error?: string; invite?: ConsoleUserInviteRecord }> {
  const { data, error } = await supabase.functions.invoke("review-action", {
    body: {
      action: "invite_console_user",
      payload,
    },
  });

  if (error) {
    throw error;
  }

  if (data?.error) {
    throw new Error(data.error);
  }

  return data as { ok?: boolean; error?: string; invite?: ConsoleUserInviteRecord };
}
