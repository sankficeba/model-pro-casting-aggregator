import { useState } from "react";
import { api } from "../api";
import type { CategoryCode } from "../types";
import { CATEGORY_DESCRIPTIONS, CATEGORY_LABELS } from "../types";

const ALL_CATEGORIES: CategoryCode[] = ["creative", "event", "general", "admin"];

interface Props {
  onDone: () => void;
  excludeCategories?: CategoryCode[];
  title?: string;
}

export function CategorySurveyScreen({
  onDone,
  excludeCategories = [],
  title = "Какие направления интересуют?",
}: Props) {
  const [selected, setSelected] = useState<Set<CategoryCode>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const visible = ALL_CATEGORIES.filter((c) => !excludeCategories.includes(c));

  const toggle = (c: CategoryCode) => {
    const next = new Set(selected);
    if (next.has(c)) next.delete(c);
    else next.add(c);
    setSelected(next);
  };

  const submit = async () => {
    if (selected.size === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.createSubscriptions(Array.from(selected));
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen p-5 space-y-4">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-sm text-slate-400">
        Выбери одно или несколько — для каждого заполнишь свою анкету.
      </p>
      <div className="space-y-3">
        {visible.map((c) => (
          <label
            key={c}
            className={`flex items-start gap-3 p-4 rounded-card border cursor-pointer transition ${
              selected.has(c)
                ? "border-accent bg-accent/10"
                : "border-bg-card"
            }`}
          >
            <input
              type="checkbox"
              checked={selected.has(c)}
              onChange={() => toggle(c)}
              className="mt-1 w-5 h-5 accent-accent"
            />
            <div className="flex-1">
              <div className="font-medium">{CATEGORY_LABELS[c]}</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {CATEGORY_DESCRIPTIONS[c]}
              </div>
            </div>
          </label>
        ))}
      </div>
      {error && (
        <div className="rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}
      <button
        onClick={submit}
        disabled={selected.size === 0 || submitting}
        className="w-full py-3 rounded-card bg-accent text-white font-medium disabled:opacity-50"
      >
        {submitting ? "Сохраняем…" : "Продолжить"}
      </button>
    </div>
  );
}
