import { supabase } from "@/lib/supabase/client";

export type ReviewActionResponse = {
  ok?: boolean;
  error?: string;
  [key: string]: unknown;
};

export type EventEditPayload = {
  event_id: string;
  status?: string;
  comment?: string;
  patch?: Record<string, unknown>;
  actor_patches?: unknown[];
};

async function invokeReviewAction<TResponse>(
  action: string,
  payload: Record<string, unknown>,
): Promise<TResponse> {
  const { data, error } = await supabase.functions.invoke("review-action", {
    body: {
      action,
      payload,
    },
  });

  if (error) {
    throw error;
  }

  if (data?.error) {
    throw new Error(data.error);
  }

  return data as TResponse;
}

export function saveEventEdit<TResponse = unknown>(
  payload: Record<string, unknown>,
): Promise<TResponse> {
  return invokeReviewAction<TResponse>("event_edit", payload);
}

export function markEventReadyForRelease(
  payload: EventEditPayload,
): Promise<ReviewActionResponse> {
  return saveEventEdit<ReviewActionResponse>({
    ...payload,
    status: payload.status ?? "ready_for_release",
  });
}

export function withholdEventFromRelease(
  payload: EventEditPayload,
): Promise<ReviewActionResponse> {
  return saveEventEdit<ReviewActionResponse>({
    ...payload,
    status: payload.status ?? "withheld",
  });
}
