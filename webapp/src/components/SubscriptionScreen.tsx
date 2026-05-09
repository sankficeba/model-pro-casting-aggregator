import { useEffect, useState } from "react";
import { ChevronLeft, Crown, CheckCircle2, Clock, Sparkles } from "lucide-react";
import { api } from "../api";
import type { SubscriptionPlan, SubscriptionStatus } from "../types";

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

// Стили рамки/акцента под бейдж конкретного тарифа.
const BADGE_STYLES: Record<string, { ring: string; chip: string; chipText: string }> = {
  Популярный: {
    ring: "border-amber-400/70 ring-1 ring-amber-400/40",
    chip: "bg-amber-400/20 border-amber-400/60",
    chipText: "text-amber-200",
  },
  Выгодный: {
    ring: "border-emerald-400/70 ring-1 ring-emerald-400/40",
    chip: "bg-emerald-400/15 border-emerald-400/60",
    chipText: "text-emerald-200",
  },
  Максимум: {
    ring: "border-fuchsia-400/70 ring-1 ring-fuchsia-400/40",
    chip: "bg-fuchsia-400/15 border-fuchsia-400/60",
    chipText: "text-fuchsia-200",
  },
};

function planMonthlyHint(plan: SubscriptionPlan): string | null {
  if (plan.days < 60) return null;
  const months = Math.round(plan.days / 30);
  const perMonth = Math.round(plan.price_rub / months);
  return `≈ ${perMonth} ₽/мес`;
}

export function SubscriptionScreen({ onBack }: Props) {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutPending, setCheckoutPending] = useState(false);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSubscriptionStatus()
      .then((s) => {
        setStatus(s);
        // Стартовый выбор: «Популярный» если есть, иначе самый длинный.
        const popular = s.plans.find((p) => p.badge === "Популярный");
        const fallback = s.plans[s.plans.length - 1] ?? s.plans[0];
        setSelectedCode((popular ?? fallback)?.code ?? null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const selectedPlan: SubscriptionPlan | null = status
    ? status.plans.find((p) => p.code === selectedCode) ?? status.plans[0] ?? null
    : null;

  const handlePay = async () => {
    if (checkoutPending || !selectedPlan) return;
    setCheckoutPending(true);
    setError(null);
    try {
      const checkout = await api.createSubscriptionCheckout(selectedPlan.code);
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
                  Осталось {status.days_left} {pluralizeDays(status.days_left)}
                </div>
                {status.trial_started_at && (
                  <div className="text-xs text-slate-500 mt-2">
                    Пробный период активирован {formatDate(status.trial_started_at)}.
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
          <>
            <div className="text-xs uppercase tracking-wider text-slate-500 px-1">
              Выберите тариф
            </div>
            <div className="space-y-3">
              {status.plans.map((plan) => {
                const isSelected = selectedPlan?.code === plan.code;
                const styles = plan.badge ? BADGE_STYLES[plan.badge] : null;
                const monthly = planMonthlyHint(plan);
                return (
                  <button
                    key={plan.code}
                    onClick={() => setSelectedCode(plan.code)}
                    className={`w-full text-left rounded-card border p-4 transition relative
                      ${
                        isSelected
                          ? styles
                            ? `${styles.ring} bg-bg-card/40`
                            : "border-accent ring-1 ring-accent/40 bg-accent/5"
                          : styles
                            ? `${styles.ring} bg-bg-card/20 opacity-90`
                            : "border-bg-card hover:border-accent/60 bg-bg-card/20"
                      }`}
                  >
                    {plan.badge && styles && (
                      <span
                        className={`absolute -top-2 left-3 px-2 py-0.5 rounded-full border text-[11px] font-medium uppercase tracking-wide ${styles.chip} ${styles.chipText}`}
                      >
                        {plan.badge === "Популярный" && (
                          <Sparkles className="inline w-3 h-3 mr-1 -mt-0.5" />
                        )}
                        {plan.badge}
                      </span>
                    )}
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-medium">{plan.label}</div>
                        {plan.discount_pct > 0 && (
                          <div className="text-xs text-emerald-300 mt-0.5">
                            Скидка {plan.discount_pct}%
                          </div>
                        )}
                        {monthly && (
                          <div className="text-xs text-slate-400 mt-1">{monthly}</div>
                        )}
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-2xl font-semibold tabular-nums">
                          {plan.price_rub} ₽
                        </div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          за {plan.days} {pluralizeDays(plan.days)}
                        </div>
                      </div>
                    </div>
                    <div
                      className={`mt-3 flex items-center gap-2 text-xs ${
                        isSelected ? "text-accent" : "text-slate-500"
                      }`}
                    >
                      <span
                        className={`inline-block w-3 h-3 rounded-full border ${
                          isSelected
                            ? "border-accent bg-accent"
                            : "border-slate-500"
                        }`}
                      />
                      {isSelected ? "Выбрано" : "Выбрать"}
                    </div>
                  </button>
                );
              })}
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
              disabled={
                !status.payments_configured || checkoutPending || !selectedPlan
              }
              className="w-full rounded-card bg-accent text-bg font-medium py-3 transition disabled:opacity-50 hover:opacity-90"
            >
              {checkoutPending
                ? "Открываем оплату…"
                : selectedPlan
                  ? `${status.is_active ? "Продлить" : "Оплатить"} за ${selectedPlan.price_rub} ₽`
                  : "Выберите тариф"}
            </button>
            <div className="text-[11px] text-slate-500 text-center">
              Оплата через ЮKassa. После успешного платежа подписка продлевается
              автоматически.
            </div>
          </>
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
