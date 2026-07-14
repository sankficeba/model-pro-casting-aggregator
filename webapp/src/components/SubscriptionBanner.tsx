import { Crown, AlertTriangle } from "lucide-react";
import { useLang } from "../i18n";
import type { SubscriptionStatus } from "../types";

interface Props {
  status: SubscriptionStatus | null;
  onClick: () => void;
}

const formatDate = (iso: string | null, lang: "ru" | "en"): string => {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(lang === "en" ? "en-US" : "ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};

const pluralizeDays = (n: number): string => {
  const lastTwo = n % 100;
  if (lastTwo >= 11 && lastTwo <= 14) return "дней";
  const last = n % 10;
  if (last === 1) return "день";
  if (last >= 2 && last <= 4) return "дня";
  return "дней";
};

/** Sticky-плашка сверху с состоянием подписки. Прилипает к верхнему
 * краю прокручиваемого экрана. Тап = открыть экран подписки. */
export function SubscriptionBanner({ status, onClick }: Props) {
  const { t, lang } = useLang();
  if (!status) return null;
  const expiringSoon = status.is_active && status.days_left <= 3;
  const inactive = !status.is_active;
  const accent = inactive
    ? "border-red-500/50 bg-red-950/40"
    : expiringSoon
      ? "border-amber-500/50 bg-amber-950/30"
      : "border-bg-card bg-bg-surface";
  const icon = inactive || expiringSoon ? AlertTriangle : Crown;
  const Icon = icon;
  const iconColor = inactive
    ? "text-red-300"
    : expiringSoon
      ? "text-amber-300"
      : "text-accent";

  return (
    <button
      onClick={onClick}
      className={`sticky top-0 left-0 right-0 w-full z-30 border-b px-4 py-2.5 flex items-center gap-3 text-left transition active:opacity-80 backdrop-blur ${accent}`}
    >
      <Icon className={`w-4 h-4 shrink-0 ${iconColor}`} />
      <div className="flex-1 min-w-0">
        {inactive ? (
          <>
            <div className="text-sm font-medium text-red-200">
              {t("Подписка не активна", "Subscription not active")}
            </div>
            <div className="text-[11px] text-slate-400 truncate">
              {t(
                "Уведомления в режиме «1 в день» — продли, чтобы не пропускать кастинги",
                "Notifications in \"1 per day\" mode — renew to stop missing castings",
              )}
            </div>
          </>
        ) : (
          <>
            <div className="text-sm font-medium">
              {t(
                `Активна до ${formatDate(status.active_until, lang)}`,
                `Active until ${formatDate(status.active_until, lang)}`,
              )}
            </div>
            <div className="text-[11px] text-slate-400">
              {t(
                `Осталось ${status.days_left} ${pluralizeDays(status.days_left)}`,
                `${status.days_left} day${status.days_left === 1 ? "" : "s"} left`,
              )}
            </div>
          </>
        )}
      </div>
      <span className="text-xs text-slate-400">→</span>
    </button>
  );
}
