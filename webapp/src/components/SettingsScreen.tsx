import { useState } from "react";
import { api } from "../api";
import type { CategoryCode, Subscription } from "../types";
import { CATEGORY_LABELS, CATEGORY_DESCRIPTIONS } from "../types";

const ALL: CategoryCode[] = ["creative", "event", "general", "admin"];

interface Props {
  subscriptions: Subscription[];
  onChange: () => Promise<void> | void;
  onEditForm: (c: CategoryCode) => void;
  onAddCategory: () => void;
  onBack: () => void;
}

export function SettingsScreen({ subscriptions, onChange, onEditForm, onAddCategory, onBack }: Props) {
  const subMap = new Map(subscriptions.map((s) => [s.category, s]));
  const [pending, setPending] = useState<CategoryCode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const canAdd = subscriptions.length < 4;

  const toggle = async (c: CategoryCode, enabled: boolean) => {
    setPending(c);
    setError(null);
    try {
      await api.patchSubscription(c, enabled);
      await onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="min-h-screen pb-5">
      <div className="sticky top-0 z-20 bg-bg/90 backdrop-blur border-b border-bg-card">
        <button onClick={onBack} className="px-4 py-3 text-slate-400 hover:text-white transition">← Назад</button>
      </div>
      <div className="p-5 space-y-4">
      <h1 className="text-2xl font-semibold">Настройки</h1>
      <div className="space-y-3">
        {ALL.map((c) => {
          const sub = subMap.get(c);
          const subscribed = sub !== undefined;
          return (
            <div
              key={c}
              className={`p-4 rounded-card border ${
                subscribed ? "border-bg-card" : "border-bg-card/40 opacity-60"
              }`}
            >
              <div className="flex justify-between items-start gap-3">
                <div className="flex-1">
                  <div className="font-medium">{CATEGORY_LABELS[c]}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{CATEGORY_DESCRIPTIONS[c]}</div>
                </div>
                {subscribed && (
                  <input
                    type="checkbox"
                    checked={sub!.enabled}
                    disabled={pending === c}
                    onChange={(e) => toggle(c, e.target.checked)}
                    className="w-6 h-6 accent-accent"
                    aria-label={`Включить ${CATEGORY_LABELS[c]}`}
                  />
                )}
              </div>
              {subscribed && (
                <button
                  onClick={() => onEditForm(c)}
                  className="mt-3 text-sm text-accent hover:underline"
                >
                  Изменить анкету
                </button>
              )}
              {!subscribed && (
                <p className="text-xs text-slate-500 mt-2">Не подписан. Нажми «+ Добавить категорию» ниже, чтобы пройти.</p>
              )}
            </div>
          );
        })}
      </div>
      {canAdd && (
        <button
          onClick={onAddCategory}
          className="w-full py-3 rounded-card border-2 border-dashed border-bg-card text-slate-400 hover:border-accent hover:text-accent transition"
        >
          + Добавить категорию
        </button>
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
