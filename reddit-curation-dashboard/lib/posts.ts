import type { CategoryKey, RedditPost } from "./types";
import { CATEGORIES, CATEGORY_KEYS } from "./categories";

export type Filters = {
  category: CategoryKey;
  hideUsed: boolean;
  minScore: number;
  minComments: number;
  query: string;
};

export function filterPosts(posts: RedditPost[], filters: Filters): RedditPost[] {
  const q = filters.query.trim().toLowerCase();
  return posts.filter((post) => {
    if (post.category !== filters.category) return false;
    if (filters.hideUsed && post.used) return false;
    if ((post.score || 0) < filters.minScore) return false;
    if ((post.comments || 0) < filters.minComments) return false;
    if (q && !post.title.toLowerCase().includes(q)) return false;
    return true;
  });
}

export function countVisible(
  posts: RedditPost[],
  category: CategoryKey,
  filters: Omit<Filters, "category">,
): number {
  return filterPosts(posts, { ...filters, category }).length;
}

function startOfWeek(date: Date): Date {
  const d = new Date(date);
  const diff = (d.getDay() + 6) % 7;
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - diff);
  return d;
}

export function analytics(posts: RedditPost[]) {
  const weekStart = startOfWeek(new Date());
  const usedThisWeek = posts.filter(
    (p) => p.used && p.used_at && new Date(p.used_at) >= weekStart,
  ).length;
  const top = CATEGORY_KEYS.map((key) => ({
    key,
    count: posts.filter((p) => p.category === key).length,
  })).sort((a, b) => b.count - a.count)[0];

  return {
    total: posts.length,
    usedThisWeek,
    usedTotal: posts.filter((p) => p.used).length,
    topCategory: top && top.count ? CATEGORIES[top.key].label : "—",
  };
}

export function briefText(post: RedditPost): string {
  return [
    `Categoría: ${post.category}`,
    `Subreddit: r/${post.subreddit}`,
    `Título: ${post.title}`,
    `Link: ${post.url}`,
    `Score: ${post.score || 0} · Comentarios: ${post.comments || 0}`,
    "",
    post.selftext || "(sin texto)",
  ].join("\n");
}

export function lastFetchedLabel(posts: RedditPost[]): string | null {
  let latest = 0;
  for (const post of posts) {
    const t = new Date(post.fetched_at).getTime();
    if (t > latest) latest = t;
  }
  if (!latest) return null;
  const minutes = Math.round((Date.now() - latest) / 60000);
  if (minutes < 1) return "hace un momento";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `hace ${hours} h`;
  return new Date(latest).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  });
}
