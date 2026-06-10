import type {
  ConsoleNotificationRecord,
  NotificationRecipientRole,
} from "@/lib/domain/types";
import { supabase } from "@/lib/supabase/client";

const NOTIFICATION_SELECT =
  "notification_id,event_id,recipient_role,subject,message,sender_name,sender_role,created_at,read_at,metadata";

export type SendNotificationPayload = {
  event_id?: string;
  recipient_role: NotificationRecipientRole;
  subject: string;
  message: string;
  metadata?: Record<string, unknown>;
};

export async function loadConsoleNotifications(): Promise<
  ConsoleNotificationRecord[]
> {
  const { data, error } = await supabase
    .from("console_notifications")
    .select(NOTIFICATION_SELECT)
    .order("created_at", { ascending: false })
    .limit(20);

  if (error) {
    throw error;
  }

  return (data ?? []) as ConsoleNotificationRecord[];
}

export async function sendConsoleNotification(
  payload: SendNotificationPayload,
): Promise<{ ok?: boolean; notification?: ConsoleNotificationRecord }> {
  const { data, error } = await supabase.functions.invoke("review-action", {
    body: {
      action: "send_notification",
      payload,
    },
  });

  if (error) {
    throw error;
  }

  if (data?.error) {
    throw new Error(data.error);
  }

  return data as { ok?: boolean; notification?: ConsoleNotificationRecord };
}

export async function markConsoleNotificationRead(
  notification_id: string,
): Promise<{ ok?: boolean; notification?: ConsoleNotificationRecord }> {
  const { data, error } = await supabase.functions.invoke("review-action", {
    body: {
      action: "notification_read",
      payload: { notification_id },
    },
  });

  if (error) {
    throw error;
  }

  if (data?.error) {
    throw new Error(data.error);
  }

  return data as { ok?: boolean; notification?: ConsoleNotificationRecord };
}
