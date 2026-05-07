import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "../api";

type Suggestions = Record<string, unknown[]>;

const SuggestionsContext = createContext<Suggestions>({});

export function SuggestionsProvider({ children }: { children: ReactNode }) {
  const [suggestions, setSuggestions] = useState<Suggestions>({});

  useEffect(() => {
    api
      .getSuggestions()
      .then((r) => setSuggestions(r.suggestions))
      .catch(() => setSuggestions({}));
  }, []);

  return (
    <SuggestionsContext.Provider value={suggestions}>
      {children}
    </SuggestionsContext.Provider>
  );
}

export function useFieldSuggestions(field: string): unknown[] {
  const all = useContext(SuggestionsContext);
  return all[field] ?? [];
}
