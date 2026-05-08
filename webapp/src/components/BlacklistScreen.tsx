import { useEffect, useState } from "react";
import { ChevronLeft, X, Plus } from "lucide-react";
import { api } from "../api";

interface Props {
  onBack: () => void;
}

export function BlacklistScreen({ onBack }: Props) {
  const [words, setWords] = useState<string[]>([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getBlacklist()
      .then((r) => setWords(r.words))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const persist = async (next: string[]) => {
    setSaving(true);
    setError(null);
    try {
      const r = await api.putBlacklist(next);
      setWords(r.words);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const addWord = async () => {
    const w = draft.trim();
    if (!w) return;
    if (words.some((x) => x.toLowerCase() === w.toLowerCase())) {
      setDraft("");
      return;
    }
    setDraft("");
    await persist([...words, w]);
  };

  const removeWord = async (w: string) => {
    await persist(words.filter((x) => x !== w));
  };

  return (
    <div className="min-h-screen pb-5">
      <div className="sticky top-0 z-20 bg-bg/90 backdrop-blur border-b border-bg-card">
        <button
          onClick={onBack}
          className="flex items-center gap-1 px-4 py-3 text-slate-400 hover:text-white transition"
        >
          <ChevronLeft className="w-5 h-5" />
          Назад
        </button>
      </div>

      <div className="p-5 space-y-4">
        <h1 className="text-2xl font-semibold">Чёрный список слов</h1>
        <p className="text-sm text-slate-400">
          Если в тексте кастинга встречается любое из этих слов или фраз —
          уведомление тебе не придёт. Сравнение без учёта регистра.
        </p>

        <div className="flex gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") addWord();
            }}
            placeholder="например, «18+» или «без оплаты»"
            className="flex-1 bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
          />
          <button
            onClick={addWord}
            disabled={!draft.trim() || saving}
            className="px-4 py-2 rounded-card bg-accent text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            Добавить
          </button>
        </div>

        {loading ? (
          <div className="text-slate-400 text-sm">Загрузка…</div>
        ) : words.length === 0 ? (
          <div className="text-slate-500 text-sm py-8 text-center">
            Список пуст. Все подходящие кастинги будут приходить.
          </div>
        ) : (
          <div className="space-y-2">
            {words.map((w) => (
              <div
                key={w}
                className="flex items-center justify-between p-3 rounded-card bg-bg-card border border-bg-card"
              >
                <span className="text-sm text-slate-200 break-words">{w}</span>
                <button
                  onClick={() => removeWord(w)}
                  className="shrink-0 ml-3 p-1.5 rounded-card text-slate-400 hover:text-red-400 hover:bg-red-950/30 transition"
                  aria-label={`Удалить «${w}»`}
                  title="Удалить"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
