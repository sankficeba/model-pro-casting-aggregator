import { useState } from "react";
import { api } from "../api";
import { useLang } from "../i18n";
import type { CategoryCode } from "../types";
import {
  CATEGORY_DESCRIPTIONS,
  CATEGORY_DESCRIPTIONS_EN,
  CATEGORY_LABELS,
  CATEGORY_LABELS_EN,
} from "../types";

const ALL_CATEGORIES: CategoryCode[] = ["creative", "event", "general", "admin"];

interface Props {
  onDone: () => void;
  excludeCategories?: CategoryCode[];
  title?: string;
}

export function CategorySurveyScreen({
  onDone,
  excludeCategories = [],
  title,
}: Props) {
  const { t } = useLang();
  const displayTitle = title ?? t("Какие направления интересуют?", "Which categories interest you?");
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
      <h1 className="text-2xl font-semibold">{displayTitle}</h1>
      <p className="text-sm text-slate-400">
        {t(
          "Выбери одно или несколько — для каждого заполнишь свою анкету.",
          "Pick one or more — you'll fill out a separate form for each.",
        )}
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
              <div className="font-medium">{t(CATEGORY_LABELS[c], CATEGORY_LABELS_EN[c])}</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {t(CATEGORY_DESCRIPTIONS[c], CATEGORY_DESCRIPTIONS_EN[c])}
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
        {submitting ? t("Сохраняем…", "Saving…") : t("Продолжить", "Continue")}
      </button>
    </div>
  );
}
