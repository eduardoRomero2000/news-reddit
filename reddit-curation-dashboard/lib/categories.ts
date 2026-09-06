import type { CategoryKey } from "./types";

export const CATEGORIES: Record<
  CategoryKey,
  { label: string; hint: string }
> = {
  noticias: { label: "Noticias", hint: "Lo que está pasando" },
  terror: { label: "Terror", hint: "Historias que incomodan" },
  experiencias: { label: "Experiencias", hint: "Relatos en primera persona" },
  chismes: { label: "Chismes", hint: "Cultura y farándula" },
};

export const CATEGORY_KEYS = Object.keys(CATEGORIES) as CategoryKey[];
