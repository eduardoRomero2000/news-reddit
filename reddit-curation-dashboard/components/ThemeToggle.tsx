"use client";

import { useSyncExternalStore } from "react";
import {
  applyTheme,
  readServerTheme,
  readTheme,
  subscribeTheme,
  type Theme,
} from "@/lib/theme";

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, readTheme, readServerTheme);

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    applyTheme(next);
  }

  const goingTo = theme === "dark" ? "Modo papel" : "Modo oscuro";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Cambiar a ${goingTo.toLowerCase()}`}
      title={goingTo}
      className="inline-flex items-center gap-2 rounded-full bg-sheet px-3 py-1.5 text-[14px] text-muted ring-1 ring-line transition-colors hover:bg-sheet-hover hover:text-ink"
    >
      <span aria-hidden="true" className="text-[15px] leading-none">
        {theme === "dark" ? "☾" : "☀"}
      </span>
      {goingTo}
    </button>
  );
}
