import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { api } from "../api";

type Suggestions = Record<string, unknown[]>;

interface ContextValue {
  suggestions: Suggestions;
  refresh: () => Promise<void>;
}

const SuggestionsContext = createContext<ContextValue>({
  suggestions: {},
  refresh: async () => {},
});

export function SuggestionsProvider({ children }: { children: ReactNode }) {
  const [suggestions, setSuggestions] = useState<Suggestions>({});

  const refresh = useCallback(async () => {
    try {
      const r = await api.getSuggestions();
      setSuggestions(r.suggestions);
    } catch {
      /* keep existing suggestions on error */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <SuggestionsContext.Provider value={{ suggestions, refresh }}>
      {children}
    </SuggestionsContext.Provider>
  );
}

export function useFieldSuggestions(field: string): unknown[] {
  return useContext(SuggestionsContext).suggestions[field] ?? [];
}

export function useSuggestionsRefresh(): () => Promise<void> {
  return useContext(SuggestionsContext).refresh;
}
