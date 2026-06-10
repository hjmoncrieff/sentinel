import type { EventEditRecord, RegistryEditRecord } from "@/lib/domain/types";
import { supabase } from "@/lib/supabase/client";

export async function loadEventEdits(eventId: string): Promise<EventEditRecord[]> {
  const { data, error } = await supabase
    .from("event_edits")
    .select(
      "edit_id,event_id,editor_name,editor_role,edited_at,status,comment,patch,actor_patches",
    )
    .eq("event_id", eventId)
    .order("edited_at", { ascending: false })
    .limit(20);

  if (error) {
    throw error;
  }

  return (data ?? []) as EventEditRecord[];
}

export async function loadRecentRegistryEdits(): Promise<RegistryEditRecord[]> {
  const { data, error } = await supabase
    .from("registry_edits")
    .select("registry_edit_id,action,payload,editor_name,editor_role,created_at")
    .order("created_at", { ascending: false })
    .limit(20);

  if (error) {
    throw error;
  }

  return (data ?? []) as RegistryEditRecord[];
}
