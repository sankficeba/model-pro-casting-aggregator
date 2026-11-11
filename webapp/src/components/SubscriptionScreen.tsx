import { useEffect, useState } from "react";
import { ChevronLeft, Crown, CheckCircle2, Clock, Sparkles } from "lucide-react";
import { api } from "../api";
import { useLang } from "../i18n";
import { openExternalLink } from "../telegram";
import type { SubscriptionPlan, SubscriptionStatus } from "../types";

interface Props {
  onBack: () => void;
}

const formatDate = (iso: string | null, lang: "ru" | "en"): string => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString(lang === "en" ? "en-US" : "ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};

// Цвет бейджа тарифа (чип рядом с названием, без наезда на рамку).
const BADGE_STYLES: Record<string, { chip: string; en: string }> = {
  Популярный: { chip: "bg-amber-400/15 text-amber-300", en: "Popular" },
  Выгодный: { chip: "bg-emerald-400/15 text-emerald-300", en: "Best value" },
  Максимум: { chip: "bg-fuchsia-400/15 text-fuchsia-300", en: "Maximum" },
};

const monthsOf = (plan: SubscriptionPlan) => Math.max(1, Math.round(plan.days / 30));

function planTitle(plan: SubscriptionPlan, lang: "ru" | "en"): string {
  if (lang !== "en") return plan.label;
  const m = monthsOf(plan);
  return `${m} month${m === 1 ? "" : "s"}`;
}

function planMonthlyHint(plan: SubscriptionPlan, lang: "ru" | "en"): string {
  const perMonth = Math.round(plan.price_rub / monthsOf(plan));
  return lang === "en" ? `${perMonth} ₽/mo` : `${perMonth} ₽/мес`;
}

// Полная цена без скидки — от цены месячного тарифа.
function fullPrice(plan: SubscriptionPlan, plans: SubscriptionPlan[]): number | null {
  const monthly = plans.find((p) => monthsOf(p) === 1);
  if (!monthly || monthsOf(plan) === 1) return null;
  const full = monthly.price_rub * monthsOf(plan);
  return full > plan.price_rub ? full : null;
}

function pluralizeDaysRu(n: number): string {
  const lastTwo = n % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return "дней";
  const last = n % 10;
  if (last === 1) return "день";
  if (last >= 2 && last <= 4) return "дня";
  return "дней";
}

function dayLabel(n: number, lang: "ru" | "en"): string {
  return lang === "en" ? `day${n === 1 ? "" : "s"}` : pluralizeDaysRu(n);
}

export function SubscriptionScreen({ onBack }: Props) {
  const { t, lang } = useLang();
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutPending, setCheckoutPending] = useState(false);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [awaitingPayment, setAwaitingPayment] = useState(false);

  // Пока оплата открыта в браузере, при возврате в Mini App перечитываем
  // статус: webhook ЮKassa к этому моменту обычно уже продлил подписку.
  useEffect(() => {
    if (!awaitingPayment) return;
    const refresh = () => {
      if (document.visibilityState !== "visible") return;
      api
        .getSubscriptionStatus()
        .then((s) => {
          setStatus(s);
          if (s.is_active) setAwaitingPayment(false);
        })
        .catch(() => {});
    };
    document.addEventListener("visibilitychange", refresh);
    window.addEventListener("focus", refresh);
    return () => {
      document.removeEventListener("visibilitychange", refresh);
      window.removeEventListener("focus", refresh);
    };
  }, [awaitingPayment]);

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
      if (openExternalLink(checkout.confirmation_url)) {
        // Оплата открылась в браузере, Mini App остаётся открытым —
        // статус подтянем, когда юзер вернётся (см. useEffect ниже).
        setCheckoutPending(false);
        setAwaitingPayment(true);
      } else {
        window.location.href = checkout.confirmation_url;
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setCheckoutPending(false);
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
        <h1 className="text-2xl font-semibold inline-flex items-center gap-2">
          <Crown className="w-6 h-6 text-accent" />
          {t("Подписка", "Subscription")}
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
                  {t("Активна", "Active")}
                </div>
                <div className="mt-2 text-2xl font-semibold">
                  {t("до", "until")} {formatDate(status.active_until, lang)}
                </div>
                <div className="text-sm text-slate-400 mt-0.5">
                  {t(
                    `Осталось ${status.days_left} ${dayLabel(status.days_left, lang)}`,
                    `${status.days_left} ${dayLabel(status.days_left, lang)} left`,
                  )}
                </div>
                {status.trial_started_at && (
                  <div className="text-xs text-slate-500 mt-2">
                    {t(
                      `Пробный период активирован ${formatDate(status.trial_started_at, lang)}.`,
                      `Trial period activated ${formatDate(status.trial_started_at, lang)}.`,
                    )}
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="inline-flex items-center gap-1.5 text-sm text-red-300">
                  <Clock className="w-4 h-4" />
                  {t("Не активна", "Not active")}
                </div>
                <div className="mt-2 text-base text-slate-200">
                  {t(
                    "Уведомления приходят в режиме «1 в день», пока подписка не продлена.",
                    "Notifications arrive in \"1 per day\" mode until the subscription is renewed.",
                  )}
                </div>
              </>
            )}
          </div>
        )}

        {status && (
          <>
            <div className="text-xs uppercase tracking-wider text-slate-500 px-1">
              {t("Выберите тариф", "Choose a plan")}
            </div>
            <div className="space-y-2.5" role="radiogroup">
              {status.plans.map((plan) => {
                const isSelected = selectedPlan?.code === plan.code;
                const badge = plan.badge ? BADGE_STYLES[plan.badge] : null;
                const full = fullPrice(plan, status.plans);
                return (
                  <button
                    key={plan.code}
                    role="radio"
                    aria-checked={isSelected}
                    onClick={() => setSelectedCode(plan.code)}
                    className={`w-full text-left rounded-card border px-4 py-3.5 transition flex items-center gap-3 ${
                      isSelected
                        ? "border-accent bg-accent/10 ring-1 ring-accent/40"
                        : "border-bg-card bg-bg-card/30 hover:border-accent/50"
                    }`}
                  >
                    <span
                      className={`shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                        isSelected ? "border-accent" : "border-slate-500"
                      }`}
                    >
                      {isSelected && <span className="w-2.5 h-2.5 rounded-full bg-accent" />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <span className="font-medium">{planTitle(plan, lang)}</span>
                        {plan.badge && badge && (
                          <span
                            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wide ${badge.chip}`}
                          >
                            {plan.badge === "Популярный" && <Sparkles className="w-3 h-3" />}
                            {lang === "en" ? badge.en : plan.badge}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-slate-400 mt-0.5">
                        {planMonthlyHint(plan, lang)}
                        {plan.discount_pct > 0 && (
                          <span className="text-emerald-300"> · −{plan.discount_pct}%</span>
                        )}
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-xl font-semibold tabular-nums leading-tight">
                        {plan.price_rub} ₽
                      </div>
                      {full && (
                        <div className="text-xs text-slate-500 line-through tabular-nums">
                          {full} ₽
                        </div>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {!status.payments_configured && (
              <div className="rounded-card bg-amber-950/40 border border-amber-900 px-3 py-2 text-xs text-amber-200">
                {t(
                  "Платёжная система ещё не настроена администратором.",
                  "The payment system hasn't been set up by the admin yet.",
                )}
              </div>
            )}

            {awaitingPayment && (
              <div className="rounded-card bg-bg-card/40 border border-accent/40 px-3 py-2 text-xs text-slate-200">
                {t(
                  "Страница оплаты открыта в браузере. После оплаты вернитесь сюда — статус обновится автоматически.",
                  "The payment page opened in your browser. Come back here after paying — the status will update automatically.",
                )}
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
                ? t("Открываем оплату…", "Opening payment…")
                : selectedPlan
                  ? t(
                      `${status.is_active ? "Продлить" : "Оплатить"} за ${selectedPlan.price_rub} ₽`,
                      `${status.is_active ? "Renew" : "Pay"} ${selectedPlan.price_rub} RUB`,
                    )
                  : t("Выберите тариф", "Choose a plan")}
            </button>
            <div className="text-[11px] text-slate-500 text-center">
              {t(
                "Оплата картой или СБП через ЮKassa. Дни добавятся к текущему сроку сразу после оплаты. Оплатить можно и в чате бота — отправьте ему любое сообщение.",
                "Pay by card or SBP via YooKassa. Days are added to your current term right after payment. You can also pay in the bot chat — send it any message.",
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
