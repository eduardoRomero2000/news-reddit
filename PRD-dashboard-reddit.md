# PRD — Radar: agregador personal de noticias de tecnología y reclutamiento

## 1. Resumen

Panel privado, de un solo usuario, que reúne los hilos más relevantes de
subreddits públicos sobre tecnología, mercado laboral y reclutamiento. Sirve
para mantenerme al día en lo que importa para mi trabajo en reclutamiento
tecnológico: tendencias del mercado laboral, actualizaciones de tecnología y
debates de la comunidad, todo en un solo lugar y sin tener que recorrer
subreddit por subreddit.

**Solo lectura.** La herramienta no publica, no vota, no comenta, no manda
mensajes ni interactúa de ninguna forma con contenido o usuarios de Reddit.
Tampoco redistribuye el contenido: el panel es local y personal.

**Problema que resuelve:** revisar a mano una docena de subreddits cada día
toma tiempo y es inconsistente. No hay una vista única que permita comparar
qué se está discutiendo, ni llevar registro de qué ya leí.

## 2. Objetivos

| Objetivo | Métrica |
|---|---|
| Reducir el tiempo de lectura diaria | De ~30 min recorriendo subreddits a <5 min en el panel |
| No perder hilos relevantes | Los hilos top del día de cada subreddit configurado aparecen en el panel |
| No releer lo mismo | Marcar como leído y ocultarlo |

## 3. Usuario y flujo

- **Usuario único:** yo, como reclutador tech.
- **Flujo:**
  1. El ingestor corre (a mano o por cron cada 6 horas) y actualiza la base.
  2. Abro el panel y reviso por categoría.
  3. Marco como leídos los hilos que ya vi; si algo me sirve para un post
     interno o una conversación con un candidato, copio el resumen (título,
     link, snippet) como referencia. El link siempre lleva al hilo original en
     Reddit.

## 4. Alcance funcional

### Implementado
- **Ingestor** en Python que consulta el listado *top* de cada subreddit y hace
  *upsert* en Postgres por id de post: correrlo varias veces no duplica, solo
  actualiza score y comentarios.
- **Supabase (Postgres)** como base local, tabla única `reddit_posts`.
- **Panel** en Next.js: tarjetas por categoría ordenadas por score, filtros por
  score y comentarios mínimos, búsqueda por palabra en el título, "ocultar
  leídos", "copiar resumen", modo oscuro por defecto.
- **Analítica simple:** hilos guardados, leídos esta semana, categoría con más
  volumen.

### Siguientes
- Búsqueda por tema con `GET /search` (`q`, `restrict_sr`) para seguir
  palabras clave (por ejemplo "layoffs", "salary", "remote").
- Vista semanal: qué temas se repitieron más.

### Fuera de alcance
- Publicar, votar, comentar o mensajear en Reddit.
- Multi-usuario, cuentas, login.
- Cualquier redistribución del contenido o entrenamiento de modelos.
- Otras redes (X, Facebook, LinkedIn).

## 5. Fuente de datos

**Reddit Data API** (https://www.reddit.com/dev/api), OAuth2 *application-only*
(`client_credentials`) contra `oauth.reddit.com`:

- `GET /r/{subreddit}/top` con `t=day`, `limit=8`. Scope `read`.
- 12 peticiones por corrida, 4 corridas al día: unas 50 peticiones diarias,
  muy por debajo del límite de 100 por minuto.
- Se respetan `X-Ratelimit-Remaining`, `X-Ratelimit-Reset` y `Retry-After`.
- User-Agent descriptivo e identificable.

Mientras no hay credenciales OAuth aprobadas, el ingestor usa el feed RSS
público (`/r/{subreddit}/top.rss`), que no expone score ni comentarios.

**Categorías y subreddits iniciales** (editables en el ingestor):

| Categoría | Subreddits |
|---|---|
| Tecnología | technology, programming, technews |
| Mercado laboral | cscareerquestions, ExperiencedDevs, jobs |
| Reclutamiento | recruiting, humanresources, recruitinghell |
| Tendencias | artificial, startups, remotework |

## 6. Datos almacenados

Tabla `reddit_posts`, un renglón por post:

| Columna | Notas |
|---|---|
| id | id del post en Reddit (llave del upsert) |
| category, subreddit | |
| title, url | el url es el permalink al hilo en Reddit |
| score, comments | métricas públicas del hilo |
| selftext | primeros 400 caracteres del texto, como vista previa |
| created_utc, fetched_at | |
| used, used_at | "leído" desde el panel |

No se guardan datos de usuarios (autor, votos individuales) ni comentarios.
Los registros se pueden borrar en cualquier momento; no se conservan más allá
del uso personal del panel.

## 7. Seguridad y permisos

- El ingestor usa la `service_role` de Supabase y corre solo en mi máquina.
- El panel usa la `anon` key, limitada por Row Level Security a leer y a
  actualizar `used` / `used_at`.
- Ninguna llave (Supabase ni Reddit) se sube al repositorio: viven en `.env*`
  ignorados por git.

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Cambios en la Data API o en sus términos | Un solo módulo habla con Reddit; se ajusta ahí |
| Subreddits con poco volumen diario | Subir `TIME_FILTER` a `week` |
| Uso más allá de lo personal | Fuera de alcance; el panel no tiene login ni se hostea públicamente |
