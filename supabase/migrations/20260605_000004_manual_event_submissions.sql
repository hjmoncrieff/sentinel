create table if not exists public.manual_event_submissions (
  submission_id uuid primary key default gen_random_uuid(),
  headline text not null,
  country text,
  event_date text,
  event_type text,
  summary text,
  source_primary text,
  confidence text not null default 'medium',
  salience text not null default 'medium',
  review_priority text not null default 'medium',
  location text,
  note text,
  status text not null default 'manual_submitted',
  editor_user_id uuid not null references auth.users (id) on delete cascade,
  editor_name text not null,
  editor_role text not null,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_manual_event_submissions_created_at
  on public.manual_event_submissions (created_at desc);

create index if not exists idx_manual_event_submissions_event_date
  on public.manual_event_submissions (event_date desc);

alter table public.manual_event_submissions enable row level security;

drop policy if exists manual_event_submissions_select_analysts on public.manual_event_submissions;
create policy manual_event_submissions_select_analysts
on public.manual_event_submissions
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));

drop policy if exists manual_event_submissions_insert_analysts on public.manual_event_submissions;
create policy manual_event_submissions_insert_analysts
on public.manual_event_submissions
for insert
to authenticated
with check (
  auth.uid() = editor_user_id
  and public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin'])
  and editor_role = public.current_app_role()
);
