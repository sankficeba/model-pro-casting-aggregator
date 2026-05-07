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
        <div className="flex gap-3">
          {isAdmin && (
            <button
              onClick={onAdmin}
              className="text-xs text-accent hover:underline"
              title="Админка"
            >
              ⚙ Админка
            </button>
          )}
          <button
            onClick={onSettings}
            className="text-2xl"
            aria-label="Настройки"
          >
            ⚙️
          </button>
        </div>
      </div>
      <div className="space-y-3">
        {visibleEnabled.map((s) => (
          <button
            key={s.category}
            onClick={() => onOpenForm(s.category)}
            className="w-full p-4 rounded-card border border-bg-card flex justify-between items-center hover:border-accent transition"
          >
            <span className="font-medium">{CATEGORY_LABELS[s.category]}</span>
            <span className="text-sm text-slate-400">
              {s.profile_completed ? "✅ Заполнена" : "⚠️ Не заполнена"}
            </span>
          </button>
        ))}
      </div>
      {canAdd && (
        <button
          onClick={onAddCategory}
          className="w-full py-3 rounded-card border-2 border-dashed border-bg-card text-slate-400 hover:border-accent hover:text-accent transition"
        >
          + Добавить категорию
        </button>
      )}
    </div>
  );
}
