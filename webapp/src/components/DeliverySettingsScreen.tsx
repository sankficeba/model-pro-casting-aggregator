import { useEffect, useState } from "react";
import { ChevronLeft, Zap, Inbox, Moon, Sun, PlayCircle, Trash2 } from "lucide-react";
import { api } from "../api";
import { tg } from "../telegram";
import { useLang } from "../i18n";
import type { DeliverySettings } from "../types";

interface Props {
  onBack: () => void;
}

const DEFAULT: DeliverySettings = {
  delivery_mode: "instant",
  night_mode_enabled: false,
  night_start_hour: 23,
  night_end_hour: 9,
  digest_daily_enabled: false,
  digest_daily_hour: 20,
  pending_count: 0,
};

export function DeliverySettingsScreen({ onBack }: Props) {
  const { t } = useLang();
  const [settings, setSettings] = useState<DeliverySettings>(DEFAULT);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedToast, setSavedToast] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [emptyQueue, setEmptyQueue] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [confirmingClear, setConfirmingClear] = useState(false);

  useEffect(() => {
    if (!emptyQueue) return;
    const handle = setTimeout(() => setEmptyQueue(false), 3000);
    return () => clearTimeout(handle);
  }, [emptyQueue]);

  const startReview = async () => {
    setReviewing(true);
    setError(null);
    setEmptyQueue(false);
    try {
      const res = await api.startDigestReview();
      if (!res.sent) {
        setEmptyQueue(true);
        setSettings((s) => ({ ...s, pending_count: 0 }));
        setReviewing(false);
        return;
      }
      tg?.close();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setReviewing(false);
    }
  };

  const clearQueue = async () => {
    if (!confirmingClear) {
      setConfirmingClear(true);
      return;
    }
    setClearing(true);
    setError(null);
    setConfirmingClear(false);
    try {
      await api.clearDigestQueue();
      setSettings((s) => ({ ...s, pending_count: 0 }));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    if (!confirmingClear) return;
    const handle = setTimeout(() => setConfirmingClear(false), 4000);
    return () => clearTimeout(handle);
  }, [confirmingClear]);

  useEffect(() => {
    api
      .getDeliverySettings()
      .then((s) => setSettings(s))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const persist = async (next: DeliverySettings) => {
    setSettings(next);
    setSaving(true);
    setError(null);
    try {
      const saved = await api.putDeliverySettings(next);
      setSettings(saved);
      setSavedToast(true);
      setTimeout(() => setSavedToast(false), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-slate-400">{t("Загрузка…", "Loading…")}</div>;
  }

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

      <div className="p-5 space-y-5">
        <h1 className="text-2xl font-semibold">{t("Доставка уведомлений", "Notification delivery")}</h1>

        {/* Mode picker */}
        <div className="space-y-3">
          <h2 className="text-sm uppercase tracking-wider text-slate-500">{t("Режим", "Mode")}</h2>
          <button
            onClick={() => persist({ ...settings, delivery_mode: "instant" })}
            className={`w-full p-4 rounded-card border text-left flex items-start gap-3 transition ${
              settings.delivery_mode === "instant"
                ? "border-accent bg-accent/10"
                : "border-bg-card"
            }`}
          >
            <Zap className="w-5 h-5 mt-0.5 text-accent shrink-0" />
            <div className="flex-1">
              <div className="font-medium">{t("Сразу", "Instant")}</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {t(
                  "Уведомления приходят сразу, как только появляется подходящий кастинг.",
                  "Notifications arrive as soon as a matching casting appears.",
                )}
              </div>
            </div>
          </button>
          <button
            onClick={() =>
              persist({
                ...settings,
                delivery_mode: "digest",
                // При первом переключении на digest сразу включаем
                // ежедневное напоминание; повторные клики не трогают.
                digest_daily_enabled:
                  settings.delivery_mode === "instant"
                    ? true
                    : settings.digest_daily_enabled,
              })
            }
            className={`w-full p-4 rounded-card border text-left flex items-start gap-3 transition ${
              settings.delivery_mode === "digest"
                ? "border-accent bg-accent/10"
                : "border-bg-card"
            }`}
          >
            <Inbox className="w-5 h-5 mt-0.5 text-accent shrink-0" />
            <div className="flex-1">
              <div className="font-medium">{t("Накопить и просмотреть", "Collect and review")}</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {t(
                  "Объявления копятся, ты листаешь их по одному в чате с ботом кнопкой «Далее».",
                  "Postings pile up, and you flip through them one by one in the bot chat with a \"Next\" button.",
                )}
              </div>
            </div>
          </button>
          {settings.delivery_mode === "digest" && (
            <>
              <button
                onClick={startReview}
                disabled={reviewing}
                className="w-full p-4 rounded-card border border-accent/40 text-left flex items-center gap-3 transition hover:border-accent disabled:opacity-50"
              >
                <PlayCircle className="w-5 h-5 text-accent shrink-0" />
                <div className="flex-1">
                  <div className="font-medium">
                    {reviewing
                      ? t("Открываем…", "Opening…")
                      : t(
                          `Пролистать накопленные объявления${
                            settings.pending_count > 0 ? ` (${settings.pending_count})` : ""
                          }`,
                          `Browse collected postings${
                            settings.pending_count > 0 ? ` (${settings.pending_count})` : ""
                          }`,
                        )}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {t(
                      "Mini App закроется, и в чате с ботом начнут приходить накопленные кастинги.",
                      "The Mini App will close, and collected castings will start arriving in the bot chat.",
                    )}
                  </div>
                </div>
              </button>
              {emptyQueue && (
                <div
                  role="status"
                  className="rounded-card border border-red-500/60 bg-red-950/30 text-red-200 text-sm px-3 py-2 animate-fade-in-out"
                >
                  {t("Пока что новых объявлений нет.", "There are no new postings yet.")}
                </div>
              )}
              <button
                onClick={clearQueue}
                disabled={clearing || settings.pending_count === 0}
                className={`w-full p-4 rounded-card border text-left flex items-center gap-3 transition disabled:opacity-40 ${
                  confirmingClear
                    ? "border-red-500 bg-red-950/30"
                    : "border-bg-card hover:border-red-500/40"
                }`}
              >
                <Trash2 className="w-5 h-5 text-red-400 shrink-0" />
                <div className="flex-1">
                  <div className="font-medium">
                    {clearing
                      ? t("Очищаем…", "Clearing…")
                      : confirmingClear
                        ? t("Точно очистить? Нажмите ещё раз", "Sure? Tap again to confirm")
                        : t("Очистить накопленные сообщения", "Clear accumulated messages")}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {t(
                      "Все накопленные объявления будут удалены без отправки.",
                      "All collected postings will be deleted without sending.",
                    )}
                  </div>
                </div>
              </button>
            </>
          )}
        </div>

        {/* Daily digest scheduled push */}
        {settings.delivery_mode === "digest" && (
          <div className="space-y-3">
            <h2 className="text-sm uppercase tracking-wider text-slate-500">
              <span className="inline-flex items-center gap-1.5">
                <Sun className="w-4 h-4" />
                {t("Ежедневное напоминание", "Daily reminder")}
              </span>
            </h2>
            <label className="flex items-center justify-between p-4 rounded-card border border-bg-card cursor-pointer">
              <div className="flex-1">
                <div className="font-medium">{t("Присылать сводку в указанное время", "Send a digest at a set time")}</div>
                <div className="text-xs text-slate-400 mt-0.5">
                  {t(
                    "Каждый день в выбранный час придёт «За сегодня — N кастингов, посмотреть?».",
                    'Every day at the chosen hour you\'ll get "Today — N castings, want to see them?".',
                  )}
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.digest_daily_enabled}
                onChange={(e) =>
                  persist({ ...settings, digest_daily_enabled: e.target.checked })
                }
                className="w-6 h-6 accent-accent ml-3"
              />
            </label>
            {settings.digest_daily_enabled && (
              <div className="px-1">
                <label className="block space-y-1">
                  <span className="text-xs text-slate-400">{t("Время (МСК)", "Time (MSK)")}</span>
                  <select
                    value={settings.digest_daily_hour}
                    onChange={(e) =>
                      persist({
                        ...settings,
                        digest_daily_hour: Number(e.target.value),
                      })
                    }
                    className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
                  >
                    {Array.from({ length: 24 }, (_, h) => (
                      <option key={h} value={h}>{`${h.toString().padStart(2, "0")}:00`}</option>
                    ))}
                  </select>
                </label>
              </div>
            )}
          </div>
        )}

        {/* Night mode */}
        <div className="space-y-3">
          <h2 className="text-sm uppercase tracking-wider text-slate-500">
            <span className="inline-flex items-center gap-1.5">
              <Moon className="w-4 h-4" />
              {t("Ночной режим", "Night mode")}
            </span>
          </h2>
          <label className="flex items-center justify-between p-4 rounded-card border border-bg-card cursor-pointer">
            <div className="flex-1">
              <div className="font-medium">{t("Не присылать уведомления ночью", "Don't send notifications at night")}</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {t(
                  "В указанное время объявления копятся. Утром придёт одно сообщение «За ночь — N кастингов» с кнопкой «Далее».",
                  'Postings pile up during the set hours. In the morning you\'ll get one message "Overnight — N castings" with a "Next" button.',
                )}
              </div>
            </div>
            <input
              type="checkbox"
              checked={settings.night_mode_enabled}
              onChange={(e) =>
                persist({ ...settings, night_mode_enabled: e.target.checked })
              }
              className="w-6 h-6 accent-accent ml-3"
            />
          </label>
          {settings.night_mode_enabled && (
            <div className="grid grid-cols-2 gap-3 px-1">
              <label className="block space-y-1">
                <span className="text-xs text-slate-400">{t("С (МСК)", "From (MSK)")}</span>
                <select
                  value={settings.night_start_hour}
                  onChange={(e) =>
                    persist({ ...settings, night_start_hour: Number(e.target.value) })
                  }
                  className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
                >
                  {Array.from({ length: 24 }, (_, h) => (
                    <option key={h} value={h}>{`${h.toString().padStart(2, "0")}:00`}</option>
                  ))}
                </select>
              </label>
              <label className="block space-y-1">
                <span className="text-xs text-slate-400">{t("До (МСК)", "To (MSK)")}</span>
                <select
                  value={settings.night_end_hour}
                  onChange={(e) =>
                    persist({ ...settings, night_end_hour: Number(e.target.value) })
                  }
                  className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
                >
                  {Array.from({ length: 24 }, (_, h) => (
                    <option key={h} value={h}>{`${h.toString().padStart(2, "0")}:00`}</option>
                  ))}
                </select>
              </label>
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}
        {savedToast && !error && (
          <div className="text-xs text-emerald-400">{t("Сохранено", "Saved")}</div>
        )}
        {saving && !savedToast && (
          <div className="text-xs text-slate-500">{t("Сохраняем…", "Saving…")}</div>
        )}
      </div>
    </div>
  );
}
