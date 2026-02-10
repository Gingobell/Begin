"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import React from "react";
import { enUS } from "./en-US";
import { zhCN } from "./zh-CN";

export type Locale = "en-US" | "zh-CN";

const translations: Record<Locale, Record<string, any>> = {
  "en-US": enUS,
  "zh-CN": zhCN,
};

function getNestedValue(obj: any, path: string): any {
  const keys = path.split(".");
  let current = obj;
  for (const key of keys) {
    if (current == null || typeof current !== "object") return path;
    current = current[key];
  }
  return current != null ? current : path;
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => any;
}

const I18nContext = createContext<I18nContextValue | null>(null);

const STORAGE_KEY = "begin-locale";

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en-US");

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as Locale | null;
      if (stored && translations[stored]) {
        setLocaleState(stored);
      }
    } catch {
      // ignore
    }
  }, []);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    try {
      localStorage.setItem(STORAGE_KEY, newLocale);
    } catch {
      // ignore
    }
    document.documentElement.lang = newLocale;
  }, []);

  const t = useCallback(
    (key: string): string => getNestedValue(translations[locale], key),
    [locale],
  );

  return React.createElement(
    I18nContext.Provider,
    { value: { locale, setLocale, t } },
    children,
  );
}

export function useTranslation() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useTranslation must be used within LanguageProvider");
  return ctx;
}
