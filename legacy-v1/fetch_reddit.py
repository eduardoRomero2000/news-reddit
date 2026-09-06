"""
Jala los posts con mas engagement de Reddit, organizados en 4 categorias,
y los sube (upsert) a una tabla de Supabase. Los posts que ya existen
(mismo id) se actualizan en vez de duplicarse.

SETUP:
    pip install requests

    Crea un archivo .env junto a este script (no lo subas a git) con:
        SUPABASE_URL=https://TUPROYECTO.supabase.co
        SUPABASE_SERVICE_ROLE_KEY=eyJ......

    La service_role key la encuentras en Supabase > Project Settings > API.
    IMPORTANTE: esta key nunca debe usarse en el dashboard (navegador),
    solo aqui, en un script que corre en tu maquina/servidor.

USO:
    python3 fetch_reddit.py

Automatizar con cron, por ejemplo cada 6 horas:
    0 */6 * * * cd /ruta/a/la/carpeta && python3 fetch_reddit.py >> fetch.log 2>&1
"""
import os
import time
import requests

HEADERS_REDDIT = {"User-Agent": "content-dashboard-script/1.0 (personal use)"}

CATEGORIES = {
    "noticias": ["news", "worldnews", "mexico"],
    "terror": ["nosleep", "LetsNotMeet", "creepypasta"],
    "experiencias": ["tifu", "confession", "AmItheAsshole"],
    "chismes": ["Fauxmoi", "popculturechat", "entertainment"],
}

TIME_FILTER = "day"   # day / week / month
LIMIT_PER_SUB = 8


def load_env(path=".env"):
    """Carga variables de un .env simple sin depender de python-dotenv."""
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


def fetch_subreddit(sub, time_filter=TIME_FILTER, limit=LIMIT_PER_SUB):
    url = f"https://www.reddit.com/r/{sub}/top.json"
    params = {"limit": limit, "t": time_filter}
    resp = requests.get(url, headers=HEADERS_REDDIT, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    posts = []
    for child in data["data"]["children"]:
        d = child["data"]
        posts.append({
            "id": d.get("id"),
            "subreddit": d.get("subreddit"),
            "title": d.get("title"),
            "score": d.get("score", 0),
            "comments": d.get("num_comments", 0),
            "url": "https://reddit.com" + d.get("permalink", ""),
            "selftext": (d.get("selftext") or "")[:400],
            "created_utc": d.get("created_utc"),
        })
    return posts


def upsert_to_supabase(rows, supabase_url, service_key):
    if not rows:
        return
    endpoint = f"{supabase_url}/rest/v1/reddit_posts"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    resp = requests.post(endpoint, headers=headers, json=rows, timeout=20)
    if resp.status_code >= 300:
        print(f"  ! error subiendo a Supabase: {resp.status_code} {resp.text[:300]}")
    else:
        print(f"  -> {len(rows)} posts subidos/actualizados")


def main():
    load_env()
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_key:
        raise SystemExit(
            "Faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY. "
            "Crea un archivo .env (ver instrucciones al inicio del script)."
        )

    for category, subs in CATEGORIES.items():
        print(f"\n{category}:")
        rows = []
        for sub in subs:
            try:
                posts = fetch_subreddit(sub)
                for p in posts:
                    p["category"] = category
                rows.extend(posts)
                time.sleep(1.5)  # se amable con la API publica de reddit
            except Exception as e:
                print(f"  ! error jalando r/{sub}: {e}")
        upsert_to_supabase(rows, supabase_url, service_key)

    print("\nListo.")


if __name__ == "__main__":
    main()
