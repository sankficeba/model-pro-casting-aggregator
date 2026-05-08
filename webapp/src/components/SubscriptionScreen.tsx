import { useEffect, useState } from "react";
import { ChevronLeft, Crown, CheckCircle2, Clock } from "lucide-react";
import { api } from "../api";
import type { SubscriptionStatus } from "../types";

interface Props {
  onBack: () => void;
}

const formatDate = (iso: string | null): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};

export function SubscriptionScreen({ onBack }: Props) {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutPending, setCheckoutPending] = useState(false);

  useEffect(() => {
    api
      .getSubscriptionStatus()
      .then(setStatus)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const handlePay = async () => {
    if (checkoutPending) return;
    setCheckoutPending(true);
    setError(null);
    try {
      const checkout = await api.createSubscriptionCheckout();
      window.location.href = checkout.confirmation_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setCheckoutPending(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-slate-400">Загрузка…</div>;
  }

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

      <div className="p-5 space-y-5">
        <h1 className="text-2xl font-semibold inline-flex items-center gap-2">
          <Crown className="w-6 h-6 text-accent" />
          Подписка
        </h1>

        {status && (
          <div
            className={`rounded-card border p-4 ${
              status.is_active
                ? "border-accent/40 bg-accent/5"
                : "border-red-500/40 bg-red-950/20"
            }`}
          >
            {status.is_active ? (
              <>
                <div className="inline-flex items-center gap-1.5 text-sm text-accent">
                  <CheckCircle2 className="w-4 h-4" />
                  Активна
                </div>
                <div className="mt-2 text-2xl font-semibold">
                  до {formatDate(status.active_until)}
                </div>
                <div className="text-sm text-slate-400 mt-0.5">
                  Осталось {status.days_left}{" "}
                  {pluralizeDays(status.days_left)}
                </div>
                {status.trial_started_at && (
                  <div className="text-xs text-slate-500 mt-2">
                    Пробный период активирован{" "}
                    {formatDate(status.trial_started_at)}.
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="inline-flex items-center gap-1.5 text-sm text-red-300">
                  <Clock className="w-4 h-4" />
                  Не активна
                </div>
                <div className="mt-2 text-base text-slate-200">
                  Уведомления приходят в режиме «1 в день», пока подписка
                  не продлена.
                </div>
              </>
            )}
          </div>
        )}

        {status && (
          <div className="rounded-card border border-bg-card p-4 space-y-3">
            <div>
              <div className="text-xs uppercase tracking-wider text-slate-500">
                Тариф
              </div>
              <div className="mt-1 flex items-baseline justify-between gap-3">
                <div>
                  <div className="font-medium">
                    Подписка на {status.plan_period_days}{" "}
                    {pluralizeDays(status.plan_period_days)}
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    Все категории, без ограничений
                  </div>
                </div>
                <div className="text-2xl font-semibold tabular-nums">
                  {status.plan_price_rub} ₽
                </div>
              </div>
            </div>

            {!status.payments_configured && (
              <div className="rounded-card bg-amber-950/40 border border-amber-900 px-3 py-2 text-xs text-amber-200">
                Платёжная система ещё не настроена администратором.
              </div>
            )}

            {error && (
              <div className="rounded-card bg-red-950/40 border border-red-900 px-3 py-2 text-sm text-red-300">
                {error}
              </div>
            )}

            <button
              onClick={handlePay}
              disabled={!status.payments_configured || checkoutPending}
              className="w-full rounded-card bg-accent text-bg font-medium py-3 transition disabled:opacity-50 hover:opacity-90"
            >
              {checkoutPending
                ? "Открываем оплату…"
                : status.is_active
                  ? `Продлить за ${status.plan_price_rub} ₽`
                  : `Оплатить ${status.plan_price_rub} ₽`}
            </button>
            <div className="text-[11px] text-slate-500 text-center">
              Оплата через ЮKassa. После успешного платежа подписка продлевается
              автоматически.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function pluralizeDays(n: number): string {
  const lastTwo = n % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return "дней";
  const last = n % 10;
  if (last === 1) return "день";
  if (last >= 2 && last <= 4) return "дня";
  return "дней";
}
