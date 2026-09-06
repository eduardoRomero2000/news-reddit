-- Corre esto en el SQL Editor de tu proyecto de Supabase.

create table if not exists reddit_posts (
  id            text primary key,        -- id del post en reddit (unico, sirve para evitar duplicados)
  category      text not null,           -- noticias | terror | experiencias | chismes
  subreddit     text not null,
  title         text not null,
  score         integer not null default 0,
  comments      integer not null default 0,
  url           text not null,
  selftext      text,
  created_utc   double precision,        -- fecha de creacion del post en reddit
  fetched_at    timestamptz not null default now(),
  used          boolean not null default false,
  used_at       timestamptz
);

create index if not exists idx_reddit_posts_category on reddit_posts(category);
create index if not exists idx_reddit_posts_score on reddit_posts(score desc);
create index if not exists idx_reddit_posts_used on reddit_posts(used);

-- Row Level Security: el dashboard usa la anon key desde el navegador,
-- asi que solo le damos permiso de LEER y de marcar "used".
-- Insertar/actualizar el resto de columnas queda reservado al script
-- (que corre con la service_role key, la cual ignora RLS).

alter table reddit_posts enable row level security;

create policy "anon puede leer"
  on reddit_posts for select
  using (true);

create policy "anon puede marcar como usado"
  on reddit_posts for update
  using (true)
  with check (true);
-- Nota: esta policy permite actualizar cualquier columna desde el cliente.
-- Para un uso personal esta bien; si mas adelante hay mas gente con acceso
-- al dashboard, conviene restringirla a nivel de columna con una funcion.
