-- supabase_schema.sql
-- Schema complet de l'application Gantt.
-- A executer dans Supabase : Dashboard > SQL Editor > New query > Run.
-- A n'utiliser QUE si tu dois recreer le projet Supabase de zero.
-- Si ton projet existe deja et qu'il est simplement en pause, clique sur
-- "Restore" : les tables et les donnees sont intactes, ce script est inutile.

-- ── Comptes utilisateurs ─────────────────────────────────────────────────────
create table if not exists public.users (
    id         uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    username   text not null unique,
    password   text not null,          -- hash pbkdf2_sha256, jamais en clair
    role       text not null default 'user'
);

-- ── Donnees de travail (isolees par session_id = username) ───────────────────
create table if not exists public.operations (
    id         bigserial primary key,
    created_at timestamptz not null default now(),
    session_id text not null,
    data       jsonb not null
);
create index if not exists operations_session_idx on public.operations (session_id);

create table if not exists public.jobs (
    id         bigserial primary key,
    created_at timestamptz not null default now(),
    session_id text not null,
    data       jsonb not null
);
create index if not exists jobs_session_idx on public.jobs (session_id);

create table if not exists public.kpis (
    id         bigserial primary key,
    created_at timestamptz not null default now(),
    session_id text not null,
    data       jsonb not null
);
create index if not exists kpis_session_idx on public.kpis (session_id);

-- Sert a la fois pour les prix unitaires et pour les maps OF / piece
-- (le code utilise le session_id "<user>_maps" pour ces dernieres).
create table if not exists public.prix (
    id         bigserial primary key,
    created_at timestamptz not null default now(),
    session_id text not null,
    data       jsonb not null
);
create index if not exists prix_session_idx on public.prix (session_id);

-- ── Plannings sauvegardes par jour ───────────────────────────────────────────
create table if not exists public.planning_jours (
    id         bigserial primary key,
    created_at timestamptz not null default now(),
    session_id text not null,
    jour       text not null,
    label      text,
    operations jsonb not null default '[]'::jsonb,
    jobs       jsonb not null default '[]'::jsonb,
    of_map     jsonb not null default '{}'::jsonb,
    piece_map  jsonb not null default '{}'::jsonb,
    makespan   integer,
    unique (session_id, jour)
);
create index if not exists planning_jours_session_idx on public.planning_jours (session_id);

-- ── Journal d'acces ──────────────────────────────────────────────────────────
create table if not exists public.app_access_logs (
    id         uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    username   text not null,
    event      text not null default 'visit',
    page       text,
    source     text,
    app_url    text,
    user_agent text
);
create index if not exists app_access_logs_created_at_idx on public.app_access_logs (created_at desc);
create index if not exists app_access_logs_username_idx  on public.app_access_logs (username);
create index if not exists app_access_logs_source_idx    on public.app_access_logs (source);

-- ── Securite ─────────────────────────────────────────────────────────────────
-- L'application est en Streamlit : tout le code tourne cote serveur, la cle
-- n'est jamais envoyee au navigateur. Avec une cle "secret" (sb_secret_...),
-- RLS est de toute facon contourne : la seule protection reelle est de NE
-- JAMAIS commiter .streamlit/secrets.toml (il est deja dans .gitignore).
--
-- Si tu passes un jour a une cle "publishable" (sb_publishable_...), il faudra
-- activer RLS et ecrire des politiques, sinon l'application ne pourra plus
-- rien lire ni ecrire :
--
--   alter table public.users          enable row level security;
--   alter table public.operations     enable row level security;
--   alter table public.jobs           enable row level security;
--   alter table public.kpis           enable row level security;
--   alter table public.prix           enable row level security;
--   alter table public.planning_jours enable row level security;
--   alter table public.app_access_logs enable row level security;
