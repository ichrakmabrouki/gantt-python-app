-- enable_rls.sql
-- Defense en profondeur : active Row Level Security sur toutes les tables.
-- A executer dans Supabase : Dashboard > SQL Editor > New query > Run.
--
-- POURQUOI CA NE CASSE PAS L'APPLICATION :
-- l'app se connecte avec une cle "secret" (sb_secret_... = role service_role),
-- et ce role CONTOURNE RLS par conception. L'app continue donc de tout lire et
-- ecrire normalement.
--
-- CE QUE CA PROTEGE :
-- la cle "publishable" (sb_publishable_... = role anon) est publique par nature.
-- Sans RLS, quiconque la recupere peut lire et modifier toutes les tables.
-- Avec RLS active et aucune policy, le role anon n'a acces a RIEN.
-- C'est gratuit, invisible pour l'app, et ca supprime toute une classe de fuites.

alter table public.users           enable row level security;
alter table public.operations      enable row level security;
alter table public.jobs            enable row level security;
alter table public.kpis            enable row level security;
alter table public.prix            enable row level security;
alter table public.planning_jours  enable row level security;
alter table public.app_access_logs enable row level security;

-- Verification : les 7 tables doivent afficher rowsecurity = true
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
order by tablename;

-- Verification : aucune policy ne doit exister (0 ligne attendue).
-- Si une policy "allow all" trainait, le role anon retrouverait l'acces.
select schemaname, tablename, policyname
from pg_policies
where schemaname = 'public';
