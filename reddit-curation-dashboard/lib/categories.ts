import type { CategoryKey } from "./types";

// Debe coincidir con CATEGORIES en reddit-curation-ingestor/fetch_reddit.py.
export const CATEGORIES: Record<
  CategoryKey,
  { label: string; hint: string }
> = {
  tecnologia: { label: "Tecnología", hint: "Noticias y lanzamientos" },
  mercado_laboral: { label: "Mercado laboral", hint: "Carreras, sueldos y contratación" },
  reclutamiento: { label: "Reclutamiento", hint: "Lo que discuten reclutadores y candidatos" },
  tendencias: { label: "Tendencias", hint: "IA, startups y trabajo remoto" },
};

export const CATEGORY_KEYS = Object.keys(CATEGORIES) as CategoryKey[];
