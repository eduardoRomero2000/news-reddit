export type Theme = "dark" | "light";

export const THEME_STORAGE_KEY = "radar:theme";
export const DEFAULT_THEME: Theme = "dark";

/*
  Corre como <script> inline en el <head>, antes de que React hidrate,
  para que la primera pintura ya tenga el tema correcto y no parpadee.
  Si no hay preferencia guardada, usa el default (oscuro).
*/
export const themeInitScript = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  THEME_STORAGE_KEY,
)});if(t!=="light"&&t!=="dark"){t=${JSON.stringify(
  DEFAULT_THEME,
)}}document.documentElement.setAttribute("data-theme",t)}catch(e){document.documentElement.setAttribute("data-theme",${JSON.stringify(
  DEFAULT_THEME,
)})}})();`;

/*
  Mini "store" externo: la fuente de verdad es el atributo data-theme del
  <html>, que ya fijó el script inline. useSyncExternalStore lo lee sin
  setState dentro de un efecto y sin desajuste servidor/cliente.
*/
const listeners = new Set<() => void>();

export function subscribeTheme(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function readTheme(): Theme {
  if (typeof document === "undefined") return DEFAULT_THEME;
  const current = document.documentElement.getAttribute("data-theme");
  return current === "light" ? "light" : "dark";
}

export function readServerTheme(): Theme {
  return DEFAULT_THEME;
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute("data-theme", theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    /* modo privado o storage bloqueado: el tema vive solo en esta pestaña */
  }
  listeners.forEach((listener) => listener());
}
