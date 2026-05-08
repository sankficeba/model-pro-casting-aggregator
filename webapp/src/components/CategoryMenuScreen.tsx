import { CheckCircle2, AlertCircle, Settings, ShieldCheck, Plus } from "lucide-react";
import type { CategoryCode, Subscription } from "../types";
import { CATEGORY_LABELS } from "../types";

interface Props {
  subscriptions: Subscription[];
  onOpenForm: (c: CategoryCode) => void;
  onAddCategory: () => void;
  onSettings: () => void;
  onAdmin?: () => void;
  isAdmin?: boolean;
}

export function CategoryMenuScreen({
  subscriptions,
  onOpenForm,
  onAddCategory,
  onSettings,
  onAdmin,
  isAdmin,
}: Props) {
  const visibleEnabled = subscriptions.filter((s) => s.enabled);
  const canAdd = subscriptions.length < 4;

  return (
    <div className="min-h-screen p-5 space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Мои направления</h1>
        <div className="flex items-center gap-2">
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
          <button
            onClick={onSettings}
            className="p-2 rounded-card text-slate-300 hover:text-white hover:bg-bg-card transition"
            aria-label="Настройки"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>
      <div className="space-y-3">
        {visibleEnabled.map((s) => {
          const pct = Math.max(0, Math.min(100, s.completion_pct ?? (s.profile_completed ? 100 : 0)));
          const isComplete = s.profile_completed;
          return (
            <button
              key={s.category}
              onClick={() => onOpenForm(s.category)}
              className="w-full p-4 rounded-card border border-bg-card hover:border-accent transition text-left"
            >
              <div className="flex justify-between items-center mb-2">
                <span className="font-medium">{CATEGORY_LABELS[s.category]}</span>
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
    </div>
  );
}
