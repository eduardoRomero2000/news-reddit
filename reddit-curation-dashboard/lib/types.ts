export type CategoryKey = "noticias" | "terror" | "experiencias" | "chismes";

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
  used: boolean;
  used_at: string | null;
};
