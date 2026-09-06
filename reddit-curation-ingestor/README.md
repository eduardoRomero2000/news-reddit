# reddit-curation-ingestor

Script que jala los top posts de Reddit por categoría y hace *upsert*
en la tabla `reddit_posts` de Supabase. Correrlo varias veces no duplica:
actualiza score, comentarios y `fetched_at`. Nunca toca `used` / `used_at`.

## Setup

```bash
cd reddit-curation-ingestor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Pega en `.env` la **service_role** de `supabase status` dentro de
`reddit-curation-supabase`. Esa key no va en el dashboard ni en git.

## Uso

```bash
# Arranca primero la base local:
#   cd ../reddit-curation-supabase && supabase start

python3 fetch_reddit.py
```

Parámetros en `.env`: `TIME_FILTER` (`day` / `week` / `month`) y `LIMIT_PER_SUB`.
Si una categoría trae poco volumen (terror en un solo día), sube a `week`.

## Cómo habla con Reddit (tres caminos)

| Camino | Cuándo se usa | Qué trae | Límite |
|---|---|---|---|
| **OAuth oficial** (`oauth.reddit.com`) | Si `.env` tiene `REDDIT_CLIENT_ID` y `REDDIT_CLIENT_SECRET` | Todo: score, comentarios, texto | ~100 req/min con token |
| **JSON público** (`/top.json`) | Sin credenciales | Todo | Reddit lo bloquea por IP con 403 ("blocked by network security") en muchas redes, incluida esta |
| **RSS** (`/top.rss`) | Fallback automático si el JSON da 403 (`ALLOW_RSS_FALLBACK=true`) | id, título, link, fecha y texto. **Sin score ni comentarios** | ~1 req/min anónimo; el script lee `x-ratelimit-*` y espera lo que Reddit pide, así que una corrida completa (12 subs) tarda ~12 min |

En modo RSS las filas nuevas quedan con `score`/`comments` en 0 y el dashboard
las muestra como "sin métricas aún". El upsert **no** manda esas columnas, así
que si más tarde entra OAuth, los valores reales se llenan sin pisar nada.

### Activar OAuth (recomendado, 5 minutos)

1. Entra a <https://www.reddit.com/prefs/apps> con tu cuenta y crea una app
   tipo **script** (redirect uri: `http://localhost:8080`, no se usa).
2. Copia el `client_id` (debajo del nombre de la app) y el `secret` a `.env`.
3. Vuelve a correr `python3 fetch_reddit.py`. Debe loguear
   `Usando la API oficial de Reddit (OAuth)`.

Referencia del flujo *application-only* (client_credentials):
<https://github.com/reddit-archive/reddit/wiki/OAuth2>. La documentación en
<https://developers.reddit.com/docs> es de la **Developer Platform (Devvit)**,
apps que corren *dentro* de Reddit; no aplica a este script, que usa la Data API.

## Cron local (cada 6 horas)

```cron
0 */6 * * * cd /ruta/a/reddit-curation-ingestor && .venv/bin/python fetch_reddit.py >> fetch.log 2>&1
```
