import { useEffect, useState, useCallback } from "react";
import { ChevronLeft, Bookmark, Trash2, MessageSquare, Loader2 } from "lucide-react";
import { api } from "../api";
import type { FavoriteItem } from "../types";

interface Props {
  onBack: () => void;
}

const fmtDate = (iso: string): string => {
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const RETENTION_OPTIONS = [1, 3, 5, 7, 14, 30, 0];

export function FavoritesScreen({ onBack }: Props) {
  const [items, setItems] = useState<FavoriteItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [retention, setRetention] = useState<number>(5);

  const refresh = useCallback(async () => {
    const t_mount = performance.now();
    try {
      const t_fetch_start = performance.now();
      const [data, settings] = await Promise.all([
        api.listFavorites(),
        api.getFavoritesSettings().catch(() => ({ retention_days: 5 })),
      ]);
      const t_fetch_end = performance.now();
      setItems(data.items);
      setRetention(settings.retention_days ?? 5);
      // Замер render: ждём кадр после setState.
      requestAnimationFrame(() => {
        const t_render = performance.now();
        api.reportPerf("favorites_open", t_render - t_mount, {
          fetch: t_fetch_end - t_fetch_start,
          render: t_render - t_fetch_end,
        });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onRetentionChange = async (days: number) => {
    setRetention(days);
    try {
      await api.putFavoritesSettings({ retention_days: days });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleRemove = async (id: number) => {
    if (pendingId !== null) return;
    setPendingId(id);
    try {
      await api.removeFavorite(id);
      setItems((prev) => prev?.filter((x) => x.message_id !== id) ?? prev);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPendingId(null);
    }
  };

  const handleShow = async (id: number) => {
    if (pendingId !== null) return;
    setPendingId(id);
    try {
      const res = await api.showFavoriteInChat(id);
      if (!res.sent) {
        setError(res.error || "Не удалось отправить.");
        return;
      }
      // Закрываем Mini App, чтобы юзер увидел сообщение в чате бота.
      const tg = (window as unknown as { Telegram?: { WebApp?: { close?: () => void } } }).Telegram;
      tg?.WebApp?.close?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPendingId(null);
    }
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
        <h1 className="text-2xl font-semibold inline-flex items-center gap-2">
          <Bookmark className="w-6 h-6 text-accent" />
          Избранные вакансии
        </h1>

        <div className="rounded-card border border-bg-card bg-bg-card/30 px-3 py-2.5 text-xs text-slate-300 space-y-1.5">
          <label className="flex items-center justify-between gap-2">
            <span>Автоудалять через:</span>
            <select
              value={retention}
              onChange={(e) => onRetentionChange(parseInt(e.target.value, 10))}
              className="bg-bg-card rounded-card px-2 py-1 outline-none focus:ring-1 ring-accent text-xs"
            >
              {RETENTION_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {d === 0 ? "не удалять" : `${d} ${d === 1 ? "день" : d < 5 ? "дня" : "дней"}`}
                </option>
              ))}
            </select>
          </label>
          {retention > 0 && (
            <div className="text-[11px] text-slate-500">
              Старее этого срока — удаляются автоматически при открытии экрана.
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-card bg-red-950/40 border border-red-900 px-3 py-2 text-sm text-red-300">
            {error}
          </div>
        )}

        {items === null && (
          <div className="text-slate-400 text-sm flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Загрузка…
          </div>
        )}

        {items !== null && items.length === 0 && (
          <div className="rounded-card border border-bg-card p-6 text-center text-slate-400">
            Пока пусто. Кнопка <b>«Добавить в избранное»</b> появится под кастинг-уведомлениями
            в чате бота.
          </div>
        )}

        {items !== null && items.length > 0 && (
          <div className="space-y-3">
            {items.map((it) => {
              const busy = pendingId === it.message_id;
              return (
                <div
                  key={it.message_id}
                  className="rounded-card border border-bg-card bg-bg-card/30 p-4 space-y-3"
                >
                  <div className="space-y-1">
                    <div className="font-medium text-sm">{it.title}</div>
                    <div className="text-xs text-slate-400 whitespace-pre-line">
                      {it.preview}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-slate-500 pt-1">
                      <span>📥 {fmtDate(it.saved_at)}</span>
                      <span>·</span>
                      <span>{it.source_label}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleShow(it.message_id)}
                      disabled={busy}
                      className="flex-1 rounded-card bg-accent text-bg font-medium py-2 text-sm transition disabled:opacity-50 hover:opacity-90 inline-flex items-center justify-center gap-1.5"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Показать в чате
                    </button>
                    <button
                      onClick={() => handleRemove(it.message_id)}
                      disabled={busy}
                      className="px-3 rounded-card border border-bg-card text-slate-300 hover:text-red-300 hover:border-red-700 transition disabled:opacity-50 inline-flex items-center justify-center"
                      aria-label="Удалить из избранного"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
