import type {
  ContentReviewDecision,
  ContentReviewItem,
  SessionProfile,
} from "@/lib/domain/types";
import { supabase } from "@/lib/supabase/client";

type ContentReviewEnvelope = {
  generated_at?: string;
  items?: ContentReviewItem[];
};

export type ContentReviewQueue = {
  generatedAt: string | null;
  items: ContentReviewItem[];
  decisions: ContentReviewDecision[];
};

/** Items awaiting review come from a console snapshot; decisions from their own table. */
export async function loadContentReviewQueue(): Promise<ContentReviewQueue> {
  const [snapshot, decisions] = await Promise.all([
    supabase
      .from("console_snapshots")
      .select("payload")
      .eq("snapshot_key", "content_review_items")
      .maybeSingle(),
    supabase
      .from("content_reviews")
      .select(
        "content_review_id,kind,subject,item_key,decision,comment,reviewer_name,reviewer_role,created_at,applied_at,applied_note",
      )
      .order("created_at", { ascending: false })
      .limit(100),
  ]);

  if (snapshot.error) {
    throw snapshot.error;
  }
  if (decisions.error) {
    throw decisions.error;
  }

  const envelope = (snapshot.data?.payload ?? {}) as ContentReviewEnvelope;

  return {
    generatedAt: envelope.generated_at ?? null,
    items: Array.isArray(envelope.items) ? envelope.items : [],
    decisions: (decisions.data ?? []) as ContentReviewDecision[],
  };
}

export async function submitContentReview(
  profile: SessionProfile,
  item: ContentReviewItem,
  decision: ContentReviewDecision["decision"],
  comment: string,
): Promise<void> {
  const { error } = await supabase.from("content_reviews").insert({
    kind: item.kind,
    subject: item.subject,
    item_key: item.item_key,
    decision,
    comment: comment.trim() || null,
    reviewer_user_id: profile.id,
    reviewer_name: profile.display_name || profile.email || "Analyst",
    reviewer_role: profile.role,
  });

  if (error) {
    throw error;
  }
}

/** The newest decision recorded for an item, if any. */
export function latestDecision(
  item: ContentReviewItem,
  decisions: ContentReviewDecision[],
): ContentReviewDecision | null {
  return decisions.find((row) => row.item_key === item.item_key) ?? null;
}
