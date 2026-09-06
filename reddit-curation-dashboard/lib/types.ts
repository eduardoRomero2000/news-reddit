export type CategoryKey =
  | "tecnologia"
  | "mercado_laboral"
  | "reclutamiento"
  | "tendencias";

export type RedditPost = {
  id: string;
  category: CategoryKey;
  subreddit: string;
  title: string;
  score: number;
  comments: number;
  url: string;
  selftext: string | null;
  created_utc: number | null;
  fetched_at: string;
  /** Marcado desde el panel como "ya leído". Columna `used` en la tabla. */
  used: boolean;
  used_at: string | null;
};
