-- Tabla de enlaces acortados
create table if not exists links (
    id uuid primary key default gen_random_uuid(),
    original_url text not null,
    short_code text unique not null,
    created_at timestamp with time zone default now()
);

-- Tabla de visitas
create table if not exists visits (
    id uuid primary key default gen_random_uuid(),
    link_id uuid references links(id) on delete cascade,
    ip text,
    user_agent text,
    location jsonb,
    visited_at timestamp with time zone default now()
);

-->     Mwsndjkn2""adsad"   <--heroku ------> beteaokbetta@gmail.com <-------

