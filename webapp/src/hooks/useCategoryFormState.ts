import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { CategoryCode, Refs } from "../types";
import { useSuggestionsRefresh } from "../contexts/SuggestionsContext";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Data = Record<string, any>;

interface Options {
  category: CategoryCode;
  validate: (data: Data) => string[];
  onDone: () => void;
  initial?: Data;
}

interface State {
  data: Data;
  refs: Refs | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  update: (patch: Data) => void;
  finish: () => Promise<void>;
}

/** Общий стейт для per-category форм: загрузка, дебаунс-автосейв,
 * валидация перед complete, обработка ошибок. */
export function useCategoryFormState({
  category,
  validate,
  onDone,
  initial = {},
}: Options): State {
  const [data, setData] = useState<Data>(initial);
  const [refs, setRefs] = useState<Refs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshSuggestions = useSuggestionsRefresh();

  useEffect(() => {
    refreshSuggestions();
  }, [refreshSuggestions]);

  useEffect(() => {
    Promise.all([api.getCategoryProfile(category), api.getRefs()])
      .then(([p, r]) => {
        setData((prev) => ({ ...prev, ...(p as Data) }));
        setRefs(r);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [category]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const update = (patch: Data) => {
    setData((prev) => {
      const next = { ...prev, ...patch };
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        api.putCategoryProfile(category, next).catch(() => {});
      }, 400);
      return next;
    });
  };

  const finish = async () => {
    const missing = validate(data);
    if (missing.length > 0) {
      setError("Заполни обязательные поля: " + missing.join(", "));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      await api.putCategoryProfile(category, data);
      await api.completeCategoryProfile(category);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return { data, refs, loading, saving, error, update, finish };
}
