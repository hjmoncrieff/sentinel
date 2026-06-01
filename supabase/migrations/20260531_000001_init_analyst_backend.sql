create extension if not exists pgcrypto;

do $$
begin
  if not exists (
    select 1
    from pg_type
    where typname = 'app_role'
  ) then
    create type public.app_role as enum ('ra', 'analyst', 'coordinator', 'admin');
  end if;
end
$$;

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text unique,
  display_name text,
  role public.app_role not null default 'analyst',
  active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create or replace function public.current_app_role()
returns text
language sql
stable
as $$
  select role::text
  from public.profiles
  where id = auth.uid()
    and active = true
  limit 1;
$$;

create or replace function public.has_app_role(allowed_roles text[])
returns boolean
language sql
stable
as $$
  select coalesce(public.current_app_role() = any(allowed_roles), false);
$$;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (
    id,
    email,
    display_name,
    role
  )
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data ->> 'display_name', split_part(coalesce(new.email, 'analyst'), '@', 1)),
    'analyst'
  )
  on conflict (id) do update
  set
    email = excluded.email,
    display_name = coalesce(excluded.display_name, public.profiles.display_name),
    updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

create table if not exists public.console_snapshots (
  snapshot_key text primary key,
  payload jsonb not null default '{}'::jsonb,
  source_path text,
  content_hash text,
  rows_count integer,
  generated_at timestamptz,
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.event_edits (
  edit_id uuid primary key default gen_random_uuid(),
  event_id text not null,
  editor_user_id uuid not null references auth.users (id) on delete cascade,
  editor_name text not null,
  editor_role text not null,
  edited_at timestamptz not null default timezone('utc', now()),
  status text not null default 'saved',
  comment text,
  patch jsonb not null default '{}'::jsonb,
  actor_patches jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_event_edits_event_id on public.event_edits (event_id);
create index if not exists idx_event_edits_editor_user_id on public.event_edits (editor_user_id);
create index if not exists idx_event_edits_edited_at on public.event_edits (edited_at desc);

create table if not exists public.qa_resolutions (
  resolution_id uuid primary key default gen_random_uuid(),
  flag_id text not null,
  event_id text not null,
  editor_user_id uuid not null references auth.users (id) on delete cascade,
  editor_name text not null,
  editor_role text not null,
  resolved_at timestamptz not null default timezone('utc', now()),
  status text not null default 'resolved',
  comment text,
  resolution_type text not null default 'manual_fix',
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_qa_resolutions_flag_id on public.qa_resolutions (flag_id);
create index if not exists idx_qa_resolutions_event_id on public.qa_resolutions (event_id);

create table if not exists public.duplicate_resolutions (
  resolution_id uuid primary key default gen_random_uuid(),
  candidate_id text not null,
  keeper_event_id text,
  merged_event_ids jsonb not null default '[]'::jsonb,
  event_ids jsonb not null default '[]'::jsonb,
  reason_code text,
  manual boolean not null default false,
  keeper_patch jsonb not null default '{}'::jsonb,
  editor_user_id uuid not null references auth.users (id) on delete cascade,
  editor_name text not null,
  editor_role text not null,
  resolved_at timestamptz not null default timezone('utc', now()),
  status text not null default 'merged',
  comment text,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_duplicate_resolutions_candidate_id on public.duplicate_resolutions (candidate_id);
create index if not exists idx_duplicate_resolutions_keeper_event_id on public.duplicate_resolutions (keeper_event_id);

create table if not exists public.registry_edits (
  registry_edit_id uuid primary key default gen_random_uuid(),
  action text not null,
  payload jsonb not null default '{}'::jsonb,
  editor_user_id uuid not null references auth.users (id) on delete cascade,
  editor_name text not null,
  editor_role text not null,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.sync_runs (
  sync_run_id uuid primary key default gen_random_uuid(),
  sync_type text not null,
  status text not null default 'started',
  started_at timestamptz not null default timezone('utc', now()),
  finished_at timestamptz,
  rows_processed integer,
  error_message text,
  metadata jsonb not null default '{}'::jsonb
);

drop trigger if exists touch_profiles_updated_at on public.profiles;
create trigger touch_profiles_updated_at
before update on public.profiles
for each row execute procedure public.touch_updated_at();

drop trigger if exists touch_console_snapshots_updated_at on public.console_snapshots;
create trigger touch_console_snapshots_updated_at
before update on public.console_snapshots
for each row execute procedure public.touch_updated_at();

alter table public.profiles enable row level security;
alter table public.console_snapshots enable row level security;
alter table public.event_edits enable row level security;
alter table public.qa_resolutions enable row level security;
alter table public.duplicate_resolutions enable row level security;
alter table public.registry_edits enable row level security;
alter table public.sync_runs enable row level security;

drop policy if exists profiles_select_self on public.profiles;
create policy profiles_select_self
on public.profiles
for select
to authenticated
using (auth.uid() = id);

drop policy if exists profiles_update_self on public.profiles;
create policy profiles_update_self
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id and role = current_app_role()::public.app_role);

drop policy if exists profiles_admin_all on public.profiles;
create policy profiles_admin_all
on public.profiles
for all
to authenticated
using (public.has_app_role(array['admin']))
with check (public.has_app_role(array['admin']));

drop policy if exists console_snapshots_select_analysts on public.console_snapshots;
create policy console_snapshots_select_analysts
on public.console_snapshots
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));

drop policy if exists event_edits_select_analysts on public.event_edits;
create policy event_edits_select_analysts
on public.event_edits
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));

drop policy if exists event_edits_insert_analysts on public.event_edits;
create policy event_edits_insert_analysts
on public.event_edits
for insert
to authenticated
with check (
  auth.uid() = editor_user_id
  and public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin'])
  and editor_role = public.current_app_role()
);

drop policy if exists qa_resolutions_select_analysts on public.qa_resolutions;
create policy qa_resolutions_select_analysts
on public.qa_resolutions
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));

drop policy if exists qa_resolutions_insert_analysts on public.qa_resolutions;
create policy qa_resolutions_insert_analysts
on public.qa_resolutions
for insert
to authenticated
with check (
  auth.uid() = editor_user_id
  and public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin'])
  and editor_role = public.current_app_role()
);

drop policy if exists duplicate_resolutions_select_analysts on public.duplicate_resolutions;
create policy duplicate_resolutions_select_analysts
on public.duplicate_resolutions
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));

drop policy if exists duplicate_resolutions_insert_analysts on public.duplicate_resolutions;
create policy duplicate_resolutions_insert_analysts
on public.duplicate_resolutions
for insert
to authenticated
with check (
  auth.uid() = editor_user_id
  and public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin'])
  and editor_role = public.current_app_role()
);

drop policy if exists registry_edits_select_analysts on public.registry_edits;
create policy registry_edits_select_analysts
on public.registry_edits
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));

drop policy if exists registry_edits_insert_coordinators on public.registry_edits;
create policy registry_edits_insert_coordinators
on public.registry_edits
for insert
to authenticated
with check (
  auth.uid() = editor_user_id
  and public.has_app_role(array['analyst', 'coordinator', 'admin'])
  and editor_role = public.current_app_role()
);

drop policy if exists sync_runs_select_analysts on public.sync_runs;
create policy sync_runs_select_analysts
on public.sync_runs
for select
to authenticated
using (public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin']));
