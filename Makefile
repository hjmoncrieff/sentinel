.PHONY: serve push-snapshots pull-registry export-published supabase-cycle

serve:
	python3 -m http.server 8000

push-snapshots:
	python3 scripts/sync/push_console_snapshots_to_supabase.py

pull-registry:
	python3 scripts/sync/pull_registry_edits_from_supabase.py

export-published:
	python3 scripts/sync/export_published_from_supabase.py

supabase-cycle:
	python3 scripts/sync/run_supabase_cycle.py
