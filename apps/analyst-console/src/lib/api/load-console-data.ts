import type { QueueItem } from "@/lib/domain/types";

type ReviewQueueEnvelope = {
  items?: QueueItem[];
};

function isQueueEnvelope(value: unknown): value is ReviewQueueEnvelope {
  return typeof value === "object" && value !== null && "items" in value;
}

export async function loadConsoleData(): Promise<QueueItem[]> {
  const response = await fetch("/data/review/review_queue.json");

  if (!response.ok) {
    throw new Error(`Failed to load review queue: ${response.status}`);
  }

  const payload = (await response.json()) as QueueItem[] | ReviewQueueEnvelope;

  if (Array.isArray(payload)) {
    return payload;
  }

  if (isQueueEnvelope(payload) && Array.isArray(payload.items)) {
    return payload.items;
  }

  return [];
}
