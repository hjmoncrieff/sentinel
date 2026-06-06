import { supabase } from "@/lib/supabase/client";

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
