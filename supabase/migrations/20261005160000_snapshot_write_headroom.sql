-- Console snapshots are large JSON documents (the council snapshot is about 10 MB).
-- Writing one through the REST API ran into the statement timeout on 2026-10-05.
--
-- 1. Give the service role, which only the sync scripts use, two minutes per statement.
-- 2. Store snapshot payloads uncompressed: compressing a multi-megabyte value on every
--    write is most of the write's cost, and the space saved does not matter here.

alter role service_role set statement_timeout = '120s';
alter table public.console_snapshots alter column payload set storage external;
notify pgrst, 'reload config';
