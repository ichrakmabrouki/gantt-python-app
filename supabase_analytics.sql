create table if not exists public.app_access_logs (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    username text not null,
    event text not null default 'visit',
    page text,
    source text,
    app_url text,
    user_agent text
);

create index if not exists app_access_logs_created_at_idx
    on public.app_access_logs (created_at desc);

create index if not exists app_access_logs_username_idx
    on public.app_access_logs (username);

create index if not exists app_access_logs_source_idx
    on public.app_access_logs (source);
