import { useEffect, useState } from "react";
import { ChevronLeft, X, Plus } from "lucide-react";
import { api } from "../api";
import { useLang } from "../i18n";

interface Props {
  onBack: () => void;
}

export function BlacklistScreen({ onBack }: Props) {
  const { t } = useLang();
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
          {t("Назад", "Back")}
        </button>
      </div>

      <div className="p-5 space-y-4">
        <h1 className="text-2xl font-semibold">{t("Чёрный список слов", "Word blacklist")}</h1>
        <p className="text-sm text-slate-400">
          {t(
            "Если в тексте кастинга встречается любое из этих слов или фраз — уведомление тебе не придёт. Сравнение без учёта регистра.",
            "If a casting's text contains any of these words or phrases, you won't get notified about it. Matching is case-insensitive.",
          )}
        </p>

        <div className="flex gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") addWord();
            }}
            placeholder={t("например, «18+» или «без оплаты»", 'e.g. "18+" or "unpaid"')}
            className="flex-1 bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
          />
          <button
            onClick={addWord}
            disabled={!draft.trim() || saving}
            className="px-4 py-2 rounded-card bg-accent text-white font-medium disabled:opacity-50 flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            {t("Добавить", "Add")}
          </button>
        </div>

        {loading ? (
          <div className="text-slate-400 text-sm">{t("Загрузка…", "Loading…")}</div>
        ) : words.length === 0 ? (
          <div className="text-slate-500 text-sm py-8 text-center">
            {t(
              "Список пуст. Все подходящие кастинги будут приходить.",
              "The list is empty. You'll get notified about all matching castings.",
            )}
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
                  aria-label={t(`Удалить «${w}»`, `Remove "${w}"`)}
                  title={t("Удалить", "Remove")}
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
