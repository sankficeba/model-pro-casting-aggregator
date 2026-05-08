import type { ReactNode } from "react";

interface Props {
  title: string;
  error: string | null;
  saving: boolean;
  onSubmit: () => void;
  /** 0-100 — процент заполнения required-полей. Рендерится в sticky-футере. */
  progressPct: number;
  children: ReactNode;
}

/** Общая обёртка per-category формы: заголовок + поля сверху, sticky-футер
 * снизу с прогрессом, ошибкой и кнопкой «Сохранить». */
export function CategoryFormShell({
  title,
  error,
  saving,
  onSubmit,
  progressPct,
  children,
}: Props) {
  const pct = Math.max(0, Math.min(100, progressPct));
  const isComplete = pct >= 100;
  return (
    <div className="min-h-screen flex flex-col">
      {/* pb-40 даёт зазор чтобы последние поля (email, vk и т.п.) могли
       * проскроллиться выше sticky-футера и не были им перекрыты. */}
      <div className="flex-1 p-5 pb-40 space-y-6">
        <h2 className="text-xl font-semibold">{title}</h2>
        {children}
      </div>

      <div className="sticky bottom-0 left-0 right-0 z-10 px-5 py-3 bg-bg/95 backdrop-blur border-t border-bg-card space-y-2">
        {error && (
          <div className="rounded-card bg-red-950/40 border border-red-900 px-3 py-2 text-xs text-red-300">
            {error}
          </div>
        )}
        <div className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-slate-400">Заполнено</span>
              <span className="text-xs text-slate-300 tabular-nums">{pct}%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-bg-card overflow-hidden">
              <div
                className={`h-full transition-all ${isComplete ? "bg-emerald-500" : "bg-accent"}`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
          <button
            onClick={onSubmit}
            disabled={saving}
            className="shrink-0 px-5 py-3 rounded-card bg-accent text-white font-medium disabled:opacity-50 whitespace-nowrap"
          >
            {saving ? "Сохраняем…" : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}
