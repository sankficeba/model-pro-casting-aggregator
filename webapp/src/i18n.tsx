// Лёгкий i18n без библиотек: язык — ru/en, строки задаются инлайн через
// t(ru, en) в месте использования (без реестра ключей). Автоопределение
// по Telegram language_code, с ручным переключением, которое запоминается
// в localStorage.
import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { isInTelegram, tg } from "./telegram";
import { api, setApiLang } from "./api";

export type Lang = "ru" | "en";

const STORAGE_KEY = "mpa_lang";

function detectLang(): Lang {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "ru" || stored === "en") return stored;
  const code = tg?.initDataUnsafe?.user?.language_code ?? navigator.language;
  return (code ?? "").toLowerCase().startsWith("en") ? "en" : "ru";
}

// Считаем язык и синхронизируем api.ts синхронно при загрузке модуля —
// раньше, чем сработает useEffect любого потомка (например, getRefs()
// внутри useCategoryFormState на mount).
const initialLang = detectLang();
setApiLang(initialLang);

interface LangContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  /** Синхронизация с users.language из /api/me (общий язык с ботом). */
  syncWithServer: (serverLang: Lang | null | undefined) => void;
  t: (ru: string, en: string) => string;
}

const LangContext = createContext<LangContextValue | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  const applyLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* storage недоступен — язык всё равно применится на сессию */
    }
    setApiLang(l);
  };

  // Ручное переключение: в Mini App сохраняем выбор и на сервере, чтобы бот
  // говорил на том же языке. На лендинге initData нет — только localStorage.
  const setLang = (l: Lang) => {
    applyLang(l);
    if (isInTelegram()) api.setLanguage(l).catch(() => {});
  };

  // Серверный выбор (в т.ч. сделанный через /language в боте) приоритетнее
  // локального. Если на сервере пусто, а локально юзер уже переключал язык
  // раньше (до появления синхронизации) — отправляем его на сервер.
  const syncWithServer = (serverLang: Lang | null | undefined) => {
    if (serverLang === "ru" || serverLang === "en") {
      applyLang(serverLang);
      return;
    }
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch {
      /* noop */
    }
    if ((stored === "ru" || stored === "en") && isInTelegram()) {
      api.setLanguage(stored).catch(() => {});
    }
  };

  const value = useMemo<LangContextValue>(
    () => ({
      lang,
      setLang,
      syncWithServer,
      t: (ru: string, en: string) => (lang === "en" ? en : ru),
    }),
    [lang],
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang() must be used within LangProvider");
  return ctx;
}
