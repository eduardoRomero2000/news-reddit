# news-reddit

Agregador personal de noticias y panel privado para seguir debates de
tendencia, noticias de la industria e hilos relevantes en subreddits públicos.
Me ayuda a mantenerme al día en temas de mi trabajo en reclutamiento
tecnológico: tendencias del mercado laboral, actualizaciones de tecnología y
debates de la comunidad, en un solo panel y **sin publicar ni interactuar con
ningún contenido de Reddit**.

Detalle funcional en [PRD-dashboard-reddit.md](PRD-dashboard-reddit.md).

## Estructura

| Carpeta | Qué es |
|---|---|
| [`reddit-curation-ingestor/`](reddit-curation-ingestor/) | Script Python que consulta Reddit (solo lectura) y hace *upsert* en Supabase. Corre en mi máquina, a mano o por cron cada 6 horas. |
| [`reddit-curation-supabase/`](reddit-curation-supabase/) | Proyecto Supabase local: migración de la tabla `reddit_posts` y políticas RLS. |
| [`reddit-curation-dashboard/`](reddit-curation-dashboard/) | Panel en Next.js, un solo usuario. Lee la tabla y marca hilos como leídos. Modo oscuro por defecto. |

## Cómo habla con Reddit

Sigue la [Data API](https://www.reddit.com/dev/api) con OAuth2
*application-only* (`client_credentials`) contra `oauth.reddit.com`:

- Endpoint: `GET /r/{subreddit}/top` con `t=day` y `limit=8`. Scope `read`.
- Subreddits: technology, programming, technews, cscareerquestions,
  ExperiencedDevs, jobs, recruiting, humanresources, recruitinghell,
  artificial, startups, remotework.
- Volumen: 12 peticiones por corrida, 4 corridas al día (~50 peticiones/día).
- Respeta `X-Ratelimit-Remaining` / `X-Ratelimit-Reset` y `Retry-After`.
- User-Agent descriptivo e identificable, configurado en `.env`.
- Datos guardados por hilo: id, subreddit, título, permalink, score, número de
  comentarios, primeros 400 caracteres del texto y fecha. No se guardan datos
  de usuarios ni comentarios. Nada se republica ni se redistribuye.

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
nunca llega al navegador; el panel usa la `anon` key limitada por RLS a leer
y a actualizar `used` / `used_at`.
