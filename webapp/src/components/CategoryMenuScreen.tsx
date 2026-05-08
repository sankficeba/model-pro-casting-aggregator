import { useState } from "react";
import { CheckCircle2, AlertCircle, ShieldCheck, Plus, Ban, Megaphone, Bell, BellOff } from "lucide-react";
import { api } from "../api";
import type { CategoryCode, Subscription } from "../types";
import { CATEGORY_LABELS } from "../types";

interface Props {
  subscriptions: Subscription[];
  onOpenForm: (c: CategoryCode) => void;
  onAddCategory: () => void;
  onBlacklist: () => void;
  onSuggestChannel: () => void;
  onDelivery: () => void;
  onAdmin?: () => void;
  isAdmin?: boolean;
  onChange?: () => Promise<void> | void;
}

export function CategoryMenuScreen({
  subscriptions,
  onOpenForm,
  onAddCategory,
  onBlacklist,
  onSuggestChannel,
  onDelivery,
  onAdmin,
  isAdmin,
  onChange,
}: Props) {
  const [pending, setPending] = useState<CategoryCode | null>(null);
  const canAdd = subscriptions.length < 4;

  const toggle = async (sub: Subscription, e: React.MouseEvent) => {
    e.stopPropagation();
    setPending(sub.category);
    try {
      await api.patchSubscription(sub.category, !sub.enabled);
      if (onChange) await onChange();
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="min-h-screen p-5 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Мои направления</h1>
        {isAdmin && (
          <button
            onClick={onAdmin}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-card text-xs text-accent hover:bg-accent/10 transition"
            title="Админка"
          >
            <ShieldCheck className="w-4 h-4" />
            Админка
          </button>
        )}
      </div>
      <div className="space-y-3">
        {subscriptions.map((s) => {
          const pct = Math.max(0, Math.min(100, s.completion_pct ?? (s.profile_completed ? 100 : 0)));
          const isComplete = s.profile_completed;
          const isPending = pending === s.category;
          return (
            <button
              key={s.category}
              onClick={() => onOpenForm(s.category)}
              className={`w-full p-4 rounded-card border transition text-left ${
                s.enabled
                  ? "border-bg-card hover:border-accent"
                  : "border-bg-card/40 opacity-60 hover:opacity-80"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <button
                  onClick={(e) => toggle(s, e)}
                  disabled={isPending}
                  className={`shrink-0 p-2 rounded-card transition ${
                    s.enabled
                      ? "text-accent hover:bg-accent/10"
                      : "text-slate-500 hover:text-slate-300 hover:bg-bg-card"
                  } ${isPending ? "opacity-50" : ""}`}
                  aria-label={s.enabled ? "Выключить уведомления" : "Включить уведомления"}
                  title={s.enabled ? "Уведомления включены" : "Уведомления выключены"}
                >
                  {s.enabled ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
                </button>
                <span className="font-medium flex-1 min-w-0">{CATEGORY_LABELS[s.category]}</span>
                <span className="flex items-center gap-1.5 text-sm text-slate-400">
                  {isComplete ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      <span>Заполнена</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-4 h-4 text-amber-400" />
                      <span className="tabular-nums">{pct}%</span>
                    </>
                  )}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-bg-card overflow-hidden">
                <div
                  className={`h-full transition-all ${isComplete ? "bg-emerald-500" : "bg-accent"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>
      {canAdd && (
        <button
          onClick={onAddCategory}
          className="w-full py-3 rounded-card border-2 border-dashed border-bg-card text-slate-400 hover:border-accent hover:text-accent transition flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Добавить категорию
        </button>
      )}

      <div className="mt-4 grid grid-cols-1 gap-2">
        <button
          onClick={onDelivery}
          className="w-full py-3 rounded-card border border-bg-card text-slate-300 hover:border-accent hover:text-accent transition flex items-center justify-center gap-2"
        >
          <Bell className="w-4 h-4" />
          Доставка уведомлений
        </button>
        <button
          onClick={onBlacklist}
          className="w-full py-3 rounded-card border border-bg-card text-slate-300 hover:border-accent hover:text-accent transition flex items-center justify-center gap-2"
        >
          <Ban className="w-4 h-4" />
          Чёрный список слов
        </button>
        <button
          onClick={onSuggestChannel}
          className="w-full py-3 rounded-card border border-bg-card text-slate-300 hover:border-accent hover:text-accent transition flex items-center justify-center gap-2"
        >
          <Megaphone className="w-4 h-4" />
          Предложить канал
        </button>
      </div>
    </div>
  );
}
