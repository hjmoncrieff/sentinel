.PHONY: serve js-install python-install lint-python format-python typecheck-python smoke-dashboard supabase-start supabase-stop supabase-status supabase-status-env supabase-db-reset supabase-db-push-local push-snapshots pull-registry export-published supabase-cycle

serve:
	python3 -m http.server 8000

js-install:
	pnpm install

python-install:
	uv pip install -r requirements-ci.txt

lint-python:
	ruff check scripts

format-python:
	ruff format scripts

typecheck-python:
	basedpyright scripts

smoke-dashboard:
	node scripts/dev/playwright_smoke_dashboard.mjs

supabase-start:
	supabase start

supabase-stop:
	supabase stop

supabase-status:
	supabase status

supabase-status-env:
	supabase status -o env

supabase-db-reset:
	supabase db reset --local

supabase-db-push-local:
	supabase db push --local

push-snapshots:
	python3 scripts/sync/push_console_snapshots_to_supabase.py

pull-registry:
	python3 scripts/sync/pull_registry_edits_from_supabase.py

export-published:
	python3 scripts/sync/export_published_from_supabase.py

supabase-cycle:
	python3 scripts/sync/run_supabase_cycle.py
