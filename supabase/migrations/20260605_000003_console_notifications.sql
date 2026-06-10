create table if not exists public.console_notifications (
  notification_id uuid primary key default gen_random_uuid(),
  event_id text,
  recipient_role text not null,
  subject text not null,
  message text not null,
  metadata jsonb not null default '{}'::jsonb,
  sender_user_id uuid not null references auth.users (id) on delete cascade,
  sender_name text not null,
  sender_role text not null,
  created_at timestamptz not null default timezone('utc', now()),
  read_at timestamptz
);

create index if not exists idx_console_notifications_created_at
  on public.console_notifications (created_at desc);

create index if not exists idx_console_notifications_recipient_role
  on public.console_notifications (recipient_role);

create index if not exists idx_console_notifications_event_id
  on public.console_notifications (event_id);

alter table public.console_notifications enable row level security;

drop policy if exists console_notifications_select_visible on public.console_notifications;
create policy console_notifications_select_visible
on public.console_notifications
for select
to authenticated
using (
  auth.uid() = sender_user_id
  or recipient_role = public.current_app_role()
  or (recipient_role = 'analyst' and public.current_app_role() = 'coordinator')
  or public.has_app_role(array['admin'])
);

drop policy if exists console_notifications_insert_team on public.console_notifications;
create policy console_notifications_insert_team
on public.console_notifications
for insert
to authenticated
with check (
  auth.uid() = sender_user_id
  and public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin'])
  and sender_role = public.current_app_role()
  and recipient_role = any(array['ra', 'analyst', 'admin', 'coordinator'])
);

drop policy if exists console_notifications_update_visible on public.console_notifications;
create policy console_notifications_update_visible
on public.console_notifications
for update
to authenticated
using (
  auth.uid() = sender_user_id
  or recipient_role = public.current_app_role()
  or (recipient_role = 'analyst' and public.current_app_role() = 'coordinator')
  or public.has_app_role(array['admin'])
)
with check (
  auth.uid() = sender_user_id
  or recipient_role = public.current_app_role()
  or (recipient_role = 'analyst' and public.current_app_role() = 'coordinator')
  or public.has_app_role(array['admin'])
);
