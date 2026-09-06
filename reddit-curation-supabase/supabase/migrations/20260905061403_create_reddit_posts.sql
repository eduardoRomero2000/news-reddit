-- Tabla única del panel de curación. El id de Reddit es la llave de upsert.
create table if not exists public.reddit_posts (
  id            text primary key,
  category      text not null,
  subreddit     text not null,
  title         text not null,
  score         integer not null default 0,
  comments      integer not null default 0,
  url           text not null,
  selftext      text,
  created_utc   double precision,
  fetched_at    timestamptz not null default now(),
  used          boolean not null default false,
  used_at       timestamptz
);

create index if not exists idx_reddit_posts_category on public.reddit_posts (category);
create index if not exists idx_reddit_posts_score on public.reddit_posts (score desc);
create index if not exists idx_reddit_posts_used on public.reddit_posts (used);
create index if not exists idx_reddit_posts_title_search
  on public.reddit_posts using gin (to_tsvector('simple', coalesce(title, '')));

alter table public.reddit_posts enable row level security;

create policy "anon puede leer"
  on public.reddit_posts
  for select
  to anon, authenticated
  using (true);

-- UPDATE necesita también SELECT (ya cubierto arriba).
-- Uso personal: el dashboard solo marca used/used_at.
create policy "anon puede marcar como usado"
  on public.reddit_posts
  for update
  to anon, authenticated
  using (true)
  with check (true);

grant select, update on table public.reddit_posts to anon, authenticated;
grant all on table public.reddit_posts to service_role;
