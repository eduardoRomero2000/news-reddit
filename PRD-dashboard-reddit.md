# PRD — Panel de curación de contenido (Reddit)

## 1. Resumen

Herramienta que jala automáticamente los posts con más engagement de Reddit en 4 categorías (noticias, terror, experiencias, chismes), los organiza en un panel visual, y permite identificar rápidamente qué historias tienen potencial para convertirse en guiones de video monetizables.

**Problema que resuelve:** buscar manualmente en Reddit historias con potencial viral toma tiempo y es inconsistente. No hay forma fácil de comparar engagement entre subreddits ni de llevar registro de qué ya se usó.

**Fuera de alcance (por ahora):** X y Facebook quedan fuera — X requiere API de pago ($100+ USD/mes) y Facebook no permite este tipo de extracción vía sus términos de servicio. Se revisita en v2 si el proyecto lo justifica.

---

## 2. Objetivos y métricas de éxito

| Objetivo | Métrica |
|---|---|
| Reducir tiempo de curación diaria | De ~30-45 min manuales a <5 min revisando el panel |
| Aumentar volumen de contenido producido | De X videos/semana a Y videos/semana (definir línea base) |
| Evitar repetir historias ya usadas | 0% de historias repetidas entre videos publicados |
| Detectar historias de alto potencial | Panel muestra score/comentarios como proxy de "qué tan viral" es la historia en su origen |

---

## 3. Usuario / caso de uso

- **Usuario único (por ahora):** tú, como creador de contenido, buscando insumos para grabar video corto/largo.
- **Flujo de uso esperado:**
  1. Corre el script de extracción (manual o programado).
  2. Abre el panel, revisa por categoría.
  3. Marca las historias elegidas como "usadas".
  4. Copia el link/snippet como referencia para escribir el guion (reescrito, no copiado literal).

---

## 4. Alcance funcional

### v1 (lo que ya existe — punto de partida)
- Script en Python que jala top posts (`/top.json`) de subreddits configurables por categoría.
- **Supabase (Postgres) como base de datos**: el script hace *upsert* de cada post (tabla `reddit_posts`), usando el id de Reddit como llave única — correr el script varias veces no duplica nada, solo actualiza score/comentarios.
- Dashboard HTML que se conecta directo a Supabase (vía `supabase-js` + anon key) y muestra tarjetas por categoría, ordenadas por score.
- Botón "marcar como usado" en cada tarjeta, que ya persiste en la base (columna `used`/`used_at`) — resuelto desde v1, no hace falta esperar a v1.1.

### v1.1 — próximas features a construir
1. **Filtro por umbral de engagement**
   - Slider o input para "score mínimo" / "comentarios mínimos", para descartar ruido de baja tracción.

2. **Refresco automático programado**
   - Cron local (ya incluido como comentario en el script) para correr cada N horas.
   - La deduplicación ya la resuelve el upsert por id — no hace falta lógica extra.

3. **Búsqueda / filtro de texto**
   - Campo para buscar palabra clave dentro de títulos ya jalados (útil cuando el panel crece).

4. **Exportar historia elegida**
   - Botón "copiar como brief" que arma un bloque de texto (título + link + snippet + categoría) listo para pegar en tu editor de guiones.

5. **Historial / analítica simple**
   - Con los datos ya en Postgres, es fácil agregar una vista de "cuántas historias usadas por semana" o "categoría con más volumen" — consulta SQL directa, sin necesitar features nuevas en el script.

### Explícitamente fuera de alcance en v1.x
- Integración con X/Facebook.
- Generación automática de guion o voz (eso sería una fase posterior, v2).
- Multi-usuario / cuentas / login.
- Publicación automática a redes (sigue siendo manual).

---

## 5. Fuentes de datos y configuración

**Fuente:** endpoint público `https://www.reddit.com/r/{subreddit}/top.json`, sin autenticación (respetando rate limits razonables, ~1 request/1.5s).

**Categorías y subreddits iniciales (editables en el script):**

| Categoría | Subreddits sugeridos |
|---|---|
| Noticias | news, worldnews, mexico |
| Terror | nosleep, LetsNotMeet, creepypasta |
| Experiencias | tifu, confession, AmItheAsshole |
| Chismes | Fauxmoi, popculturechat, entertainment |

**Parámetros configurables:** `TIME_FILTER` (day/week/month), `LIMIT_PER_SUB`, lista de subreddits por categoría.

## 5bis. Base de datos (Supabase)

**Tabla única `reddit_posts`:**

| Columna | Tipo | Notas |
|---|---|---|
| id | text (PK) | id del post en Reddit — evita duplicados vía upsert |
| category | text | noticias / terror / experiencias / chismes |
| subreddit | text | |
| title | text | |
| score | integer | |
| comments | integer | |
| url | text | |
| selftext | text | primeros 400 caracteres |
| created_utc | double precision | fecha original del post |
| fetched_at | timestamptz | cuándo se jaló |
| used | boolean | marcado desde el dashboard |
| used_at | timestamptz | |

**Llaves y permisos:**
- El **script** (`fetch_reddit.py`) usa la `service_role key` — corre en tu máquina/servidor, nunca en el navegador, y tiene permiso total (bypassa RLS) para insertar/actualizar.
- El **dashboard** (navegador) usa la `anon key`, protegida por Row Level Security: solo puede leer todo y actualizar (para el botón "marcar como usado"). No puede insertar ni borrar.
- El SQL de setup (tabla + políticas de RLS) vive en `supabase_schema.sql`, se corre una sola vez en el SQL Editor de Supabase.

---

## 6. Requisitos no funcionales

- **Red:** el script debe correr en una máquina/servidor con salida a internet sin restricciones a `reddit.com` (no corre dentro del entorno de Claude por política de red de la cuenta).
- **Costo:** $0 — Reddit vía endpoint público, y Supabase free tier (500MB de DB) sobra por mucho margen para este volumen de posts.
- **Mantenimiento:** si Reddit empieza a bloquear el User-Agent o exige autenticación, habría que migrar a la API oficial (OAuth con PRAW), que sigue siendo gratuita para uso de bajo volumen.
- **Portabilidad:** el dashboard es un solo archivo HTML sin build ni backend propio — se abre directo en el navegador y habla directo con Supabase.
- **Seguridad:** la `service_role key` de Supabase nunca debe subirse a un repo público ni exponerse en el HTML — vive solo en el `.env` local del script.

---

## 7. Riesgos y consideraciones

| Riesgo | Mitigación |
|---|---|
| Reddit cambia/bloquea el endpoint público | Migrar a API oficial con OAuth (requiere registrar una app, sigue gratis) |
| Reutilizar contenido de forma muy literal → riesgo de copyright / contenido "reciclado" en la plataforma de video | Reescribir siempre con palabras propias, no copiar texto ni imágenes del post original |
| Historias identificables (nombres, detalles muy específicos) | Difuminar detalles identificables antes de narrar, especialmente en confesiones/experiencias |
| Baja calidad de datos en categorías con poco volumen (ej. terror en un solo día) | Ajustar `TIME_FILTER` a "week" cuando el volumen diario sea bajo |

---

## 8. Roadmap propuesto

1. **Ahora:** validar que v1 (script + dashboard) sirve en el flujo real de curación diaria/semanal.
2. **Siguiente:** agregar "marcar como usado" + deduplicación entre corridas (la feature con más impacto en ahorro de tiempo).
3. **Después:** filtro de umbral + búsqueda de texto.
4. **Evaluar más adelante:** si el volumen de video lo justifica, migrar a API oficial de Reddit (OAuth) para más estabilidad, y reconsiderar X/Facebook si aparece una vía dentro de sus términos de servicio.

---

## 9. Preguntas abiertas

- ¿El dashboard se queda como archivo local que abres en tu compu, o prefieres hostearlo (Vercel/Netlify gratis) para verlo desde el celular? Como ya habla con Supabase, hostearlo es trivial.
- ¿Cadencia real de grabación (diaria/semanal) para calibrar `TIME_FILTER` y cuántos subreddits por categoría son suficientes?
- ¿Vale la pena una vista simple de analítica (posts usados por semana, categoría más productiva) ahora que los datos viven en Postgres, o se deja para más adelante?
