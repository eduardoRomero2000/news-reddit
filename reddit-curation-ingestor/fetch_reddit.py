#!/usr/bin/env python3
"""Agregador personal de noticias: extrae los hilos destacados de subreddits
públicos sobre tecnología, mercado laboral y reclutamiento, y los guarda en
Supabase para leerlos en un panel privado. Solo lectura: nunca publica, vota
ni interactúa con contenido de Reddit.

Tres caminos para hablar con Reddit, en este orden:

1. **OAuth oficial** (si hay REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET):
   token de app (client_credentials) contra oauth.reddit.com. Trae score y
   comentarios y no sufre el bloqueo por IP del endpoint público.
2. **JSON público** (/r/{sub}/top.json): sin credenciales. Reddit lo bloquea
   ("blocked by network security") en muchas redes.
3. **RSS** (/r/{sub}/top.rss): casi nunca bloqueado. Trae id, título, link,
   fecha y texto, pero NO score ni comentarios. Esas columnas se omiten del
   payload para no pisar métricas reales con ceros; en filas nuevas quedan 0.
"""

from __future__ import annotations

import html
import json
import logging
import os
import random
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import requests


REDDIT_JSON_URL = "https://www.reddit.com/r/{subreddit}/top.json"
REDDIT_RSS_URL = "https://www.reddit.com/r/{subreddit}/top.rss"
REDDIT_OAUTH_URL = "https://oauth.reddit.com/r/{subreddit}/top"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
REQUEST_INTERVAL_SECONDS = 1.5
MAX_RETRIES = 3
VALID_TIME_FILTERS = {"hour", "day", "week", "month", "year", "all"}
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}

# Categorías del panel y subreddits públicos que alimentan cada una.
# Editable; las llaves se guardan en la columna `category` y las conoce el dashboard.
CATEGORIES = {
    "tecnologia": ("technology", "programming", "technews"),
    "mercado_laboral": ("cscareerquestions", "ExperiencedDevs", "jobs"),
    "reclutamiento": ("recruiting", "humanresources", "recruitinghell"),
    "tendencias": ("artificial", "startups", "remotework"),
}

LOGGER = logging.getLogger("reddit-curation-ingestor")


class BlockedError(Exception):
    """Reddit rechazó la petición anónima (403); conviene cambiar de camino."""


@dataclass(frozen=True)
class Config:
    time_filter: str
    limit_per_sub: int
    reddit_user_agent: str
    supabase_url: str
    supabase_service_role_key: str
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    allow_rss_fallback: bool = True

    @property
    def has_oauth(self) -> bool:
        return bool(self.reddit_client_id and self.reddit_client_secret)


def load_dotenv(path: Path | str = ".env", *, override: bool = False) -> None:
    """Carga un archivo KEY=VALUE sencillo sin ejecutar su contenido."""
    env_path = Path(path)
    if not env_path.is_file():
        return

    for line_number, raw_line in enumerate(
        env_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(
                f"Línea inválida en {env_path}:{line_number}; se esperaba KEY=VALUE"
            )
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"Variable vacía en {env_path}:{line_number}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value


def load_config(environ: Mapping[str, str] | None = None) -> Config:
    """Construye y valida la configuración desde variables de entorno."""
    env = os.environ if environ is None else environ
    time_filter = env.get("TIME_FILTER", "day").strip().lower()
    if time_filter not in VALID_TIME_FILTERS:
        allowed = ", ".join(sorted(VALID_TIME_FILTERS))
        raise ValueError(f"TIME_FILTER inválido; valores permitidos: {allowed}")

    raw_limit = env.get("LIMIT_PER_SUB", "8").strip()
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise ValueError("LIMIT_PER_SUB debe ser un entero") from exc
    if not 1 <= limit <= 100:
        raise ValueError("LIMIT_PER_SUB debe estar entre 1 y 100")

    user_agent = env.get("REDDIT_USER_AGENT", "").strip()
    if not user_agent:
        raise ValueError("Falta REDDIT_USER_AGENT")

    service_key = env.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not service_key:
        raise ValueError("Falta SUPABASE_SERVICE_ROLE_KEY")

    supabase_url = env.get("SUPABASE_URL", "http://127.0.0.1:55321").strip()
    if not supabase_url.startswith(("http://", "https://")):
        raise ValueError("SUPABASE_URL debe comenzar con http:// o https://")

    rss_fallback = env.get("ALLOW_RSS_FALLBACK", "true").strip().lower()
    if rss_fallback not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError("ALLOW_RSS_FALLBACK debe ser true o false")

    return Config(
        time_filter=time_filter,
        limit_per_sub=limit,
        reddit_user_agent=user_agent,
        supabase_url=supabase_url.rstrip("/"),
        supabase_service_role_key=service_key,
        reddit_client_id=env.get("REDDIT_CLIENT_ID", "").strip(),
        reddit_client_secret=env.get("REDDIT_CLIENT_SECRET", "").strip(),
        allow_rss_fallback=rss_fallback in {"true", "1", "yes"},
    )


# --------------------------------------------------------------------------- #
# Parseo de respuestas
# --------------------------------------------------------------------------- #


def parse_listing(
    payload: Any, category: str, subreddit: str, fetched_at: str
) -> list[dict[str, Any]]:
    """Valida una respuesta Listing de Reddit (JSON/OAuth) y normaliza sus posts."""
    if not isinstance(payload, dict):
        raise ValueError("La respuesta JSON no es un objeto")
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("children"), list):
        raise ValueError("La respuesta no contiene data.children")

    posts: list[dict[str, Any]] = []
    for index, child in enumerate(data["children"]):
        post = child.get("data") if isinstance(child, dict) else None
        if not isinstance(post, dict):
            LOGGER.warning("Post inválido omitido en r/%s (índice %d)", subreddit, index)
            continue

        post_id = post.get("id")
        title = post.get("title")
        if not isinstance(post_id, str) or not post_id:
            LOGGER.warning("Post sin id omitido en r/%s (índice %d)", subreddit, index)
            continue
        if not isinstance(title, str):
            LOGGER.warning("Post sin título omitido en r/%s (id %s)", subreddit, post_id)
            continue

        selftext = post.get("selftext")
        if not isinstance(selftext, str):
            selftext = ""
        permalink = post.get("permalink")
        if isinstance(permalink, str) and permalink:
            url = "https://reddit.com" + permalink
        else:
            url = str(post.get("url") or "")
        posts.append(
            {
                "id": post_id,
                "category": category,
                "subreddit": str(post.get("subreddit") or subreddit),
                "title": title,
                "score": _as_int(post.get("score")),
                "comments": _as_int(post.get("num_comments")),
                "url": url,
                "selftext": selftext[:400],
                "created_utc": _as_float(post.get("created_utc")),
                "fetched_at": fetched_at,
            }
        )
    return posts


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _html_to_text(fragment: str) -> str:
    """Convierte el HTML del feed en texto plano compacto."""
    text = re.sub(r"<!--.*?-->", " ", fragment, flags=re.S)
    text = re.sub(r"</(p|div|br|li|h\d)>", "\n", text, flags=re.I)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _rss_selftext(content_html: str) -> str:
    """El feed envuelve el texto del post en <div class="md">…</div>."""
    match = re.search(
        r'<div class="md">(.*?)</div>\s*<!-- SC_ON -->', content_html, flags=re.S
    )
    if not match:
        match = re.search(r'<div class="md">(.*?)</div>', content_html, flags=re.S)
    return _html_to_text(match.group(1)) if match else ""


def parse_rss(
    body: bytes, category: str, subreddit: str, fetched_at: str
) -> list[dict[str, Any]]:
    """Normaliza un feed Atom de Reddit. Sin score/comments (el feed no los trae)."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise ValueError(f"RSS inválido recibido de r/{subreddit}") from exc

    posts: list[dict[str, Any]] = []
    for index, entry in enumerate(root.findall("a:entry", ATOM_NS)):
        raw_id = (entry.findtext("a:id", default="", namespaces=ATOM_NS) or "").strip()
        title = entry.findtext("a:title", default=None, namespaces=ATOM_NS)
        if not raw_id:
            LOGGER.warning("Entrada sin id omitida en r/%s (índice %d)", subreddit, index)
            continue
        if title is None:
            LOGGER.warning("Entrada sin título omitida en r/%s (id %s)", subreddit, raw_id)
            continue
        post_id = raw_id[3:] if raw_id.startswith("t3_") else raw_id

        link = entry.find("a:link", ATOM_NS)
        url = link.get("href", "") if link is not None else ""
        published = entry.findtext("a:published", default="", namespaces=ATOM_NS) or ""
        created_utc = _iso_to_epoch(published)
        content = entry.findtext("a:content", default="", namespaces=ATOM_NS) or ""

        posts.append(
            {
                "id": post_id,
                "category": category,
                "subreddit": subreddit,
                "title": html.unescape(title),
                "url": url,
                "selftext": _rss_selftext(content)[:400],
                "created_utc": created_utc,
                "fetched_at": fetched_at,
            }
        )
    return posts


def _iso_to_epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------------------------------- #
# HTTP con reintentos
# --------------------------------------------------------------------------- #


def _header_seconds(response: requests.Response, name: str) -> float | None:
    raw = response.headers.get(name)
    if not raw:
        return None
    try:
        return min(max(float(raw), 0.0), 120.0)
    except ValueError:
        return None


def _backoff_seconds(response: requests.Response, attempt: int) -> float:
    """Prefiere lo que Reddit pide (Retry-After / x-ratelimit-reset); si no, exponencial."""
    for header in ("Retry-After", "x-ratelimit-reset"):
        seconds = _header_seconds(response, header)
        if seconds is not None:
            return seconds + 1.0
    return min(2**attempt + random.uniform(0.0, 0.5), 30.0)


def _respect_rate_limit(response: requests.Response, label: str) -> None:
    """Si Reddit dice que ya no queda cuota en esta ventana, espera a que se reinicie.

    El RSS anónimo da ~1 petición por ventana de 60s, así que sin esto la
    siguiente llamada casi siempre sería un 429.
    """
    remaining = _header_seconds(response, "x-ratelimit-remaining")
    reset = _header_seconds(response, "x-ratelimit-reset")
    if remaining is not None and remaining < 1.0 and reset:
        LOGGER.info("Cuota de Reddit agotada tras %s; esperando %.0fs", label, reset + 1.0)
        time.sleep(reset + 1.0)


def _get_with_retries(
    session: requests.Session, url: str, *, params: dict[str, Any], label: str
) -> requests.Response:
    """GET con reintentos para errores de red, 429 y 5xx. 403 → BlockedError."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=(5, 30))
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                raise
            delay = min(2**attempt + random.uniform(0.0, 0.5), 30.0)
            LOGGER.warning("Error de red en %s; reintento en %.1fs", label, delay)
            time.sleep(delay)
            continue

        if response.status_code == 403:
            raise BlockedError(f"Reddit bloqueó la petición anónima a {label} (403)")

        if response.status_code == 429 or 500 <= response.status_code < 600:
            if attempt == MAX_RETRIES:
                response.raise_for_status()
            delay = _backoff_seconds(response, attempt)
            LOGGER.warning(
                "Reddit respondió %d para %s; reintento en %.1fs",
                response.status_code,
                label,
                delay,
            )
            time.sleep(delay)
            continue

        response.raise_for_status()
        _respect_rate_limit(response, label)
        return response

    raise RuntimeError(f"No se pudo consultar {label}")


def _decode_json(response: requests.Response, subreddit: str) -> Any:
    try:
        return response.json()
    except (requests.exceptions.JSONDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON inválido recibido de r/{subreddit}") from exc


def get_oauth_token(session: requests.Session, config: Config) -> str:
    """Token de aplicación (client_credentials). Dura ~1h; sobra para una corrida."""
    response = session.post(
        REDDIT_TOKEN_URL,
        auth=(config.reddit_client_id, config.reddit_client_secret),
        data={"grant_type": "client_credentials"},
        timeout=(5, 30),
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not isinstance(token, str) or not token:
        raise ValueError("Reddit no devolvió access_token; revisa client id/secret")
    return token


# --------------------------------------------------------------------------- #
# Orquestación
# --------------------------------------------------------------------------- #


def fetch_subreddit(
    session: requests.Session,
    config: Config,
    category: str,
    subreddit: str,
    mode: str,
) -> list[dict[str, Any]]:
    """Consulta un subreddit por el camino indicado: oauth | json | rss."""
    params = {"t": config.time_filter, "limit": config.limit_per_sub}
    label = f"r/{subreddit}"
    if mode == "oauth":
        response = _get_with_retries(
            session,
            REDDIT_OAUTH_URL.format(subreddit=subreddit),
            params={**params, "raw_json": 1},
            label=label,
        )
        fetched_at = datetime.now(timezone.utc).isoformat()
        return parse_listing(_decode_json(response, subreddit), category, subreddit, fetched_at)
    if mode == "json":
        response = _get_with_retries(
            session, REDDIT_JSON_URL.format(subreddit=subreddit), params=params, label=label
        )
        fetched_at = datetime.now(timezone.utc).isoformat()
        return parse_listing(_decode_json(response, subreddit), category, subreddit, fetched_at)
    if mode == "rss":
        response = _get_with_retries(
            session, REDDIT_RSS_URL.format(subreddit=subreddit), params=params, label=label
        )
        fetched_at = datetime.now(timezone.utc).isoformat()
        return parse_rss(response.content, category, subreddit, fetched_at)
    raise ValueError(f"Modo desconocido: {mode}")


def fetch_all(
    config: Config, on_category: Callable[[str, list[dict[str, Any]]], None] | None = None
) -> tuple[list[dict[str, Any]], str]:
    """Recorre todos los subreddits respetando el intervalo. Devuelve (posts, modo).

    Si se pasa `on_category`, se invoca al terminar cada categoría con sus posts:
    así una corrida larga (modo RSS ~1 req/min) va guardando progreso y un corte
    a la mitad no pierde lo ya descargado.
    """
    posts: list[dict[str, Any]] = []
    session = requests.Session()
    session.headers.update(
        {"User-Agent": config.reddit_user_agent, "Accept": "application/json, application/atom+xml;q=0.9, */*;q=0.8"}
    )

    mode = "json"
    if config.has_oauth:
        try:
            token = get_oauth_token(session, config)
            session.headers["Authorization"] = f"Bearer {token}"
            mode = "oauth"
            LOGGER.info("Usando la API oficial de Reddit (OAuth)")
        except (requests.RequestException, ValueError) as exc:
            LOGGER.error("OAuth falló (%s); se intenta el JSON público", exc)

    last_request_started: float | None = None

    def paced_fetch(category: str, subreddit: str, current_mode: str) -> list[dict[str, Any]]:
        nonlocal last_request_started
        if last_request_started is not None:
            elapsed = time.monotonic() - last_request_started
            time.sleep(max(0.0, REQUEST_INTERVAL_SECONDS - elapsed))
        last_request_started = time.monotonic()
        return fetch_subreddit(session, config, category, subreddit, current_mode)

    for category, subreddits in CATEGORIES.items():
        category_posts: list[dict[str, Any]] = []
        for subreddit in subreddits:
            try:
                try:
                    subreddit_posts = paced_fetch(category, subreddit, mode)
                except BlockedError as exc:
                    if mode != "json" or not config.allow_rss_fallback:
                        raise
                    LOGGER.warning(
                        "%s. Cambiando a RSS para el resto de la corrida: "
                        "sin score ni comentarios. Para métricas completas registra "
                        "una app en https://www.reddit.com/prefs/apps y llena "
                        "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET en .env",
                        exc,
                    )
                    mode = "rss"
                    subreddit_posts = paced_fetch(category, subreddit, mode)
            except (requests.RequestException, ValueError, BlockedError) as exc:
                LOGGER.error("No se pudo procesar r/%s: %s", subreddit, exc)
                continue
            category_posts.extend(subreddit_posts)
            LOGGER.info("r/%s: %d posts (%s)", subreddit, len(subreddit_posts), mode)
        posts.extend(category_posts)
        if on_category is not None and category_posts:
            on_category(category, category_posts)
    return posts, mode


def upsert_posts(
    session: requests.Session, config: Config, posts: list[dict[str, Any]]
) -> None:
    """Hace upsert por id; el payload nunca contiene used ni used_at.

    PostgREST exige que todas las filas de un mismo POST tengan las mismas
    llaves, así que se agrupan por conjunto de columnas (JSON vs RSS).
    """
    if not posts:
        LOGGER.warning("No hay posts para guardar")
        return

    groups: dict[frozenset[str], list[dict[str, Any]]] = {}
    for post in posts:
        groups.setdefault(frozenset(post), []).append(post)

    for batch in groups.values():
        response = session.post(
            f"{config.supabase_url}/rest/v1/reddit_posts",
            params={"on_conflict": "id"},
            headers={
                "apikey": config.supabase_service_role_key,
                "Authorization": f"Bearer {config.supabase_service_role_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=batch,
            timeout=(5, 60),
        )
        if response.status_code >= 400:
            raise requests.HTTPError(
                f"Supabase respondió {response.status_code}: {response.text[:300]}",
                response=response,
            )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        load_dotenv(Path(__file__).with_name(".env"))
        config = load_config()
        with requests.Session() as session:

            def save(category: str, rows: list[dict[str, Any]]) -> None:
                upsert_posts(session, config, rows)
                LOGGER.info("%s: %d posts guardados en Supabase", category, len(rows))

            posts, mode = fetch_all(config, on_category=save)
        LOGGER.info("%d posts procesados correctamente (modo %s)", len(posts), mode)
        if mode == "rss":
            LOGGER.warning(
                "Corrida en modo RSS: las filas nuevas no tienen score/comentarios. "
                "Configura OAuth en .env para métricas reales."
            )
        return 0
    except (ValueError, OSError, requests.RequestException, BlockedError) as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
