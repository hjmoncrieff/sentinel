create table if not exists public.console_user_invites (
  invite_id uuid primary key default gen_random_uuid(),
  invited_user_id uuid references auth.users (id) on delete set null,
  invited_email text not null unique,
  invited_display_name text,
  invited_role public.app_role not null,
  inviter_user_id uuid not null references auth.users (id) on delete cascade,
  inviter_name text not null,
  inviter_role text not null,
  status text not null default 'invited',
  redirect_to text,
  invited_at timestamptz not null default timezone('utc', now()),
  last_sent_at timestamptz not null default timezone('utc', now()),
  accepted_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_console_user_invites_last_sent_at
  on public.console_user_invites (last_sent_at desc);

create index if not exists idx_console_user_invites_invited_role
  on public.console_user_invites (invited_role);

drop trigger if exists touch_console_user_invites_updated_at on public.console_user_invites;
create trigger touch_console_user_invites_updated_at
before update on public.console_user_invites
for each row execute procedure public.touch_updated_at();

alter table public.console_user_invites enable row level security;

drop policy if exists console_user_invites_select_admin on public.console_user_invites;
create policy console_user_invites_select_admin
on public.console_user_invites
for select
to authenticated
using (public.has_app_role(array['admin']));

drop policy if exists console_user_invites_insert_admin on public.console_user_invites;
create policy console_user_invites_insert_admin
on public.console_user_invites
for insert
to authenticated
with check (
  auth.uid() = inviter_user_id
  and public.has_app_role(array['admin'])
  and inviter_role = public.current_app_role()
);

drop policy if exists console_user_invites_update_admin on public.console_user_invites;
create policy console_user_invites_update_admin
on public.console_user_invites
for update
to authenticated
using (public.has_app_role(array['admin']))
with check (public.has_app_role(array['admin']));
