import { useSyncExternalStore } from "react";
import {
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  type Settings,
} from "@/lib/settings";

const listeners = new Set<() => void>();
let cache: { raw: string | null; value: Settings } = {
  raw: null,
  value: DEFAULT_SETTINGS,
};

function rawValue(): string | null {
  try {
    return window.localStorage.getItem("nexusrag.provider");
  } catch {
    return null;
  }
}

function getSnapshot(): Settings {
  const raw = rawValue();
  if (raw !== cache.raw) cache = { raw, value: loadSettings() };
  return cache.value;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

export function updateSettings(settings: Settings): void {
  saveSettings(settings);
  listeners.forEach((l) => l());
}

export function useSettings(): Settings {
  return useSyncExternalStore(subscribe, getSnapshot, () => DEFAULT_SETTINGS);
}
