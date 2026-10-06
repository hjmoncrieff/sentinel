-- Analyst decisions on machine-proposed public content.
--
-- kind 'reference_proposal': a researched change to a country's officeholders, elections
-- or notes (apps/public-site/reference/countries.json). The proposals themselves reach
-- the console as the 'content_review_items' console snapshot; this table holds only the
-- decisions. The sync cycle applies undecided rows to the repository and stamps applied_at.
-- kind 'scenario' is reserved for AI-written scenarios, which need approval before they
-- are published.

create table if not exists public.content_reviews (
  content_review_id uuid primary key default gen_random_uuid(),
  kind text not null check (kind in ('reference_proposal', 'scenario')),
  subject text not null,
  item_key text not null,
  decision text not null check (decision in ('approve', 'dismiss')),
  comment text,
  reviewer_user_id uuid not null references auth.users (id) on delete cascade,
  reviewer_name text not null,
  reviewer_role text not null,
  created_at timestamptz not null default timezone('utc', now()),
  applied_at timestamptz,
  applied_note text
);

create index if not exists idx_content_reviews_pending
  on public.content_reviews (created_at)
  where applied_at is null;

create index if not exists idx_content_reviews_item_key
  on public.content_reviews (item_key);

alter table public.content_reviews enable row level security;

drop policy if exists content_reviews_select_team on public.content_reviews;
create policy content_reviews_select_team
on public.content_reviews
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));

drop policy if exists content_reviews_insert_analysts on public.content_reviews;
create policy content_reviews_insert_analysts
on public.content_reviews
for insert
to authenticated
with check (
  auth.uid() = reviewer_user_id
  and public.has_app_role(array['analyst', 'coordinator', 'admin'])
  and reviewer_role = public.current_app_role()
);
