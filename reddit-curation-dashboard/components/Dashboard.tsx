"use client";

import { useEffect, useMemo, useState } from "react";
import ThemeToggle from "@/components/ThemeToggle";
import { CATEGORIES, CATEGORY_KEYS } from "@/lib/categories";
import {
  analytics,
  briefText,
  countVisible,
  filterPosts,
  lastFetchedLabel,
} from "@/lib/posts";
import { getSupabase, hasSupabaseConfig } from "@/lib/supabase";
import type { CategoryKey, RedditPost } from "@/lib/types";

export default function Dashboard() {
  const [posts, setPosts] = useState<RedditPost[]>([]);
  const [category, setCategory] = useState<CategoryKey>("tecnologia");
  const [hideRead, setHideRead] = useState(true);
  const [minScore, setMinScore] = useState(0);
  const [minComments, setMinComments] = useState(0);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("Cargando…");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [reloadKey, setReloadKey] = useState(0);

  // Patrón "fetch en el efecto": todos los setState ocurren después del
  // await (asíncronos), que es lo que permite react-hooks/set-state-in-effect.
  // `cancelled` evita pisar estado si el componente se desmonta a media carga.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await fetchPosts();
      if (cancelled) return;
      setLoading(false);
      if (result.kind === "unconfigured") {
        setError("Faltan variables NEXT_PUBLIC_SUPABASE_* en .env.local");
        setStatus("Sin configurar");
        return;
      }
      if (result.kind === "error") {
        setError(
          "No se pudo leer Supabase. ¿Está corriendo reddit-curation-supabase en :55321?",
        );
        setStatus("Error de conexión");
        return;
      }
      setError(null);
      setPosts(result.posts);
      setStatus(`${result.posts.length} hilos`);
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  function refresh() {
    setLoading(true);
    setStatus("Cargando…");
    setReloadKey((key) => key + 1);
  }

  const filters = useMemo(
    () => ({ category, hideUsed: hideRead, minScore, minComments, query }),
    [category, hideRead, minScore, minComments, query],
  );
  const visible = useMemo(() => filterPosts(posts, filters), [posts, filters]);
  const stats = useMemo(() => analytics(posts), [posts]);
  const lastFetched = useMemo(() => lastFetchedLabel(posts), [posts]);

  async function markRead(id: string, used: boolean) {
    const supabase = getSupabase();
    const usedAt = used ? new Date().toISOString() : null;
    const { error: updateError } = await supabase
      .from("reddit_posts")
      .update({ used, used_at: usedAt })
      .eq("id", id);
    if (updateError) {
      showToast("No se pudo guardar el cambio");
      return;
    }
    setPosts((current) =>
      current.map((post) =>
        post.id === id ? { ...post, used, used_at: usedAt } : post,
      ),
    );
  }

  async function copyBrief(post: RedditPost) {
    await navigator.clipboard.writeText(briefText(post));
    showToast("Resumen copiado");
  }

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(null), 1600);
  }

  return (
    <div className="mx-auto max-w-3xl px-5 py-10 sm:px-8 sm:py-14">
      <header className="mb-8">
        <div className="flex items-start justify-between gap-4">
          <p className="mb-2 text-sm tracking-wide text-muted">
            Agregador personal · solo lectura
          </p>
          <ThemeToggle />
        </div>
        <h1 className="font-serif text-[2.1rem] font-semibold leading-tight tracking-tight text-ink">
          Radar
        </h1>
        <p className="mt-3 max-w-prose text-[17px] leading-7 text-muted">
          Hilos destacados de subreddits públicos sobre tecnología, mercado
          laboral y reclutamiento, en un solo panel privado. Nada se publica ni
          se responde desde aquí.
        </p>
        <p className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted">
          <span>{status}</span>
          {lastFetched ? <span>· última actualización {lastFetched}</span> : null}
          <button
            type="button"
            onClick={refresh}
            disabled={loading}
            className="underline decoration-line underline-offset-4 hover:text-ink disabled:opacity-50"
          >
            Actualizar
          </button>
        </p>
      </header>

      <section className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Hilos guardados" value={String(stats.total)} />
        <Stat label="Leídos esta semana" value={String(stats.usedThisWeek)} />
        <Stat label="Leídos en total" value={String(stats.usedTotal)} />
        <Stat label="Más volumen" value={stats.topCategory} />
      </section>

      {error ? (
        <p className="mb-6 rounded-lg border border-line bg-sheet px-4 py-3 text-[15px] text-ink">
          {error}
        </p>
      ) : null}

      <nav className="mb-5 flex flex-wrap gap-2" aria-label="Categorías">
        {CATEGORY_KEYS.map((key) => {
          const active = key === category;
          const count = countVisible(posts, key, {
            hideUsed: hideRead,
            minScore,
            minComments,
            query,
          });
          return (
            <button
              key={key}
              type="button"
              onClick={() => setCategory(key)}
              className={`rounded-full px-3.5 py-1.5 text-[15px] transition-colors ${
                active
                  ? "bg-accent text-paper"
                  : "bg-sheet text-ink ring-1 ring-line hover:bg-sheet-hover"
              }`}
            >
              {CATEGORIES[key].label}
              <span className={active ? "ml-1.5 opacity-80" : "ml-1.5 text-muted"}>
                {count}
              </span>
            </button>
          );
        })}
      </nav>

      <div className="mb-8 flex flex-wrap items-end gap-4 border-b border-line pb-5">
        <label className="flex items-center gap-2 text-[15px] text-ink">
          <input
            type="checkbox"
            checked={hideRead}
            onChange={(e) => setHideRead(e.target.checked)}
            className="size-4 accent-accent"
          />
          Ocultar leídos
        </label>
        <Field label="Score mín." value={minScore} onChange={setMinScore} />
        <Field
          label="Comentarios mín."
          value={minComments}
          onChange={setMinComments}
        />
        <label className="min-w-[220px] flex-1 text-[13px] text-muted">
          Buscar
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Palabra en el título"
            className="mt-1 w-full rounded-md border border-line bg-sheet px-3 py-2 text-[16px] text-ink outline-none placeholder:text-muted focus:border-accent"
          />
        </label>
      </div>

      <p className="mb-4 text-sm text-muted">
        {CATEGORIES[category].hint} · {visible.length} visibles
      </p>

      {visible.length === 0 ? (
        <p className="max-w-prose text-muted">
          Nada aquí todavía. Corre el ingestor, baja el umbral o desmarca
          “ocultar leídos”.
        </p>
      ) : (
        <ol className="space-y-5">
          {visible.map((post) => (
            <li
              key={post.id}
              className={`rounded-xl border border-line bg-sheet px-5 py-5 ${
                post.used ? "opacity-60" : ""
              }`}
            >
              <p className="text-[13px] tracking-wide text-accent">
                r/{post.subreddit}
              </p>
              <h2 className="mt-1.5 font-serif text-[1.35rem] font-semibold leading-snug text-ink">
                {post.title}
              </h2>
              {post.selftext ? (
                <p className="mt-3 max-w-prose text-[16.5px] leading-7 text-body">
                  {post.selftext}
                  {post.selftext.length >= 400 ? "…" : ""}
                </p>
              ) : null}
              <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[14px] text-muted">
                <Metrics post={post} />
                <a
                  href={post.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline decoration-line underline-offset-4 hover:text-ink"
                >
                  Ver original
                </a>
                <button
                  type="button"
                  onClick={() => void copyBrief(post)}
                  className="underline decoration-line underline-offset-4 hover:text-ink"
                >
                  Copiar resumen
                </button>
                <button
                  type="button"
                  onClick={() => void markRead(post.id, !post.used)}
                  className="ml-auto rounded-full bg-accent-soft px-3 py-1 text-accent transition-colors hover:bg-accent-soft-hover"
                >
                  {post.used ? "Marcar no leído" : "Marcar leído"}
                </button>
              </div>
            </li>
          ))}
        </ol>
      )}

      {toast ? (
        <div className="fixed bottom-5 right-5 rounded-full bg-ink px-4 py-2 text-sm text-paper">
          {toast}
        </div>
      ) : null}
    </div>
  );
}

function Metrics({ post }: { post: RedditPost }) {
  const score = post.score || 0;
  const comments = post.comments || 0;
  // Las filas que entraron por RSS no traen métricas: mejor decirlo que
  // mostrar "0 pts" como si fuera un dato real.
  if (score === 0 && comments === 0) {
    return (
      <span title="Ingresada vía RSS; Reddit no expone score ahí. Configura OAuth en el ingestor para ver métricas.">
        sin métricas aún
      </span>
    );
  }
  return (
    <>
      <span>{score.toLocaleString()} pts</span>
      <span>{comments.toLocaleString()} comentarios</span>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-sheet px-3.5 py-3">
      <p className="text-[12px] uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 font-serif text-xl text-ink">{value}</p>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="text-[13px] text-muted">
      {label}
      <input
        type="number"
        min={0}
        value={value}
        onChange={(e) => onChange(Number(e.target.value) || 0)}
        className="mt-1 block w-24 rounded-md border border-line bg-sheet px-3 py-2 text-[16px] text-ink outline-none focus:border-accent"
      />
    </label>
  );
}

type FetchResult =
  | { kind: "ok"; posts: RedditPost[] }
  | { kind: "error" }
  | { kind: "unconfigured" };

async function fetchPosts(): Promise<FetchResult> {
  if (!hasSupabaseConfig()) return { kind: "unconfigured" };
  // Score desc como proxy de relevancia; las filas sin métricas (RSS)
  // empatan en 0 y se desempatan por fecha del post más reciente.
  const { data, error } = await getSupabase()
    .from("reddit_posts")
    .select("*")
    .order("score", { ascending: false })
    .order("created_utc", { ascending: false, nullsFirst: false });
  if (error) return { kind: "error" };
  return { kind: "ok", posts: (data ?? []) as RedditPost[] };
}
