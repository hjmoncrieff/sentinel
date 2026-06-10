drop policy if exists registry_edits_insert_coordinators on public.registry_edits;

create policy registry_edits_insert_reviewers
on public.registry_edits
for insert
to authenticated
with check (
  auth.uid() = editor_user_id
  and public.has_app_role(array['ra', 'analyst', 'coordinator', 'admin'])
  and editor_role = public.current_app_role()
);
