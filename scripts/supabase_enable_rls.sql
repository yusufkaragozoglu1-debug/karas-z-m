-- Kararsizim: enable Row Level Security on every table in the public schema.
--
-- Why: Django's tables live in Supabase's `public` schema, which the Data API
-- (PostgREST) exposes to the `anon` / `authenticated` roles. With RLS enabled and
-- NO policies, those roles can read/write nothing. Django is unaffected because it
-- connects as the `postgres` role, which bypasses RLS.
--
-- Run in: Supabase Dashboard -> SQL Editor. Safe to run repeatedly; run it again
-- after every migration that creates new tables.

DO $$
DECLARE
  t record;
BEGIN
  FOR t IN
    SELECT tablename FROM pg_tables WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.tablename);
  END LOOP;
END
$$;

-- Verify: every row should show rowsecurity = true.
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
