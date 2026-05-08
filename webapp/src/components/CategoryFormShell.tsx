import type { ReactNode } from "react";

interface Props {
  title: string;
  error: string | null;
  saving: boolean;
  onSubmit: () => void;
  children: ReactNode;
}

/** Общая обёртка per-category формы: заголовок, секции, ошибка, кнопка
 * «Сохранить». Содержимое (секции с полями) приходит через children. */
export function CategoryFormShell({ title, error, saving, onSubmit, children }: Props) {
  return (
    <div className="min-h-screen p-5 pb-32 space-y-6">
      <h2 className="text-xl font-semibold">{title}</h2>

      {children}

      {error && (
        <div className="rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <button
        onClick={onSubmit}
        disabled={saving}
        className="w-full py-3 rounded-card bg-accent text-white font-medium disabled:opacity-50"
      >
        {saving ? "Сохраняем…" : "Сохранить анкету"}
      </button>
    </div>
  );
}
