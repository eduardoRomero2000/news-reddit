# reddit-news-dashboard

Herramienta personal de curación de contenido: lee el listado *top* de 12
subreddits públicos, guarda los posts en una base Postgres local (Supabase) y
los muestra en un panel de un solo usuario para elegir historias que después
se investigan y se reescriben con palabras propias como guion de video.

Nada se republica ni se redistribuye. Solo lectura, sin votar, sin publicar,
sin mensajes, sin entrenamiento de modelos. El detalle funcional está en
[PRD-dashboard-reddit.md](PRD-dashboard-reddit.md).

## Estructura

| Carpeta | Qué es |
|---|---|
| [`reddit-curation-ingestor/`](reddit-curation-ingestor/) | Script Python que consulta Reddit y hace *upsert* en Supabase. Corre en la máquina del autor, a mano o por cron cada 6 horas. |
| [`reddit-curation-supabase/`](reddit-curation-supabase/) | Proyecto Supabase local (migración de la tabla `reddit_posts` y sus políticas RLS). |
| [`reddit-curation-dashboard/`](reddit-curation-dashboard/) | Panel en Next.js. Solo lee la tabla y marca posts como "usados". Modo oscuro por defecto. |
| [`legacy-v1/`](legacy-v1/) | Primera versión (un HTML y un script planos). Se conserva como referencia; ya no se usa. |

## Cómo habla con Reddit

El ingestor sigue la [Data API](https://www.reddit.com/dev/api) con OAuth2
*application-only* (`client_credentials`) contra `oauth.reddit.com`:

- Endpoint: `GET /r/{subreddit}/top` con `t=day` y `limit=8`. Scope `read`.
- Volumen: 12 peticiones por corrida, 4 corridas al día (~50 peticiones/día).
- Respeta `X-Ratelimit-Remaining` / `X-Ratelimit-Reset` y `Retry-After`.
- User-Agent descriptivo e identificable, configurado en `.env`.
- Datos guardados por post: id, subreddit, título, permalink, score, número
  de comentarios, primeros 400 caracteres del texto y fecha. Nunca datos de
  usuarios ni contenido de comentarios.

Mientras no hay credenciales OAuth aprobadas, el script cae al feed RSS
público (`/r/{subreddit}/top.rss`), que no expone score ni comentarios.

## Correr en local

```bash
# 1. Base de datos
cd reddit-curation-supabase && supabase start

# 2. Ingestor
cd ../reddit-curation-ingestor
cp .env.example .env         # pegar service_role de `supabase status` y, si hay, credenciales OAuth
pip install -r requirements.txt
python3 fetch_reddit.py

# 3. Panel
cd ../reddit-curation-dashboard
cp .env.example .env.local   # pegar anon key de `supabase status`
npm install && npm run dev   # http://localhost:3000
```

Las llaves viven solo en archivos `.env*` ignorados por git. La `service_role`
nunca llega al navegador; el panel usa la `anon` key limitada por RLS a
leer y a actualizar `used` / `used_at`.
