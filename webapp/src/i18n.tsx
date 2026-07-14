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
import { tg } from "./telegram";
import { setApiLang } from "./api";

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
  t: (ru: string, en: string) => string;
}

const LangContext = createContext<LangContextValue | null>(null);

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  const setLang = (l: Lang) => {
    setLangState(l);
    localStorage.setItem(STORAGE_KEY, l);
    setApiLang(l);
  };

  const value = useMemo<LangContextValue>(
    () => ({
      lang,
      setLang,
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
