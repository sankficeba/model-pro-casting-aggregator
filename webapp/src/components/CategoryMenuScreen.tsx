import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, ShieldCheck, Plus, Bell, BellOff, UserRound, ChevronRight } from "lucide-react";
import { api } from "../api";
import type { CategoryCode, DeliverySettings, Subscription } from "../types";
import { CATEGORY_LABELS, CATEGORY_LABELS_EN } from "../types";
import { useLang } from "../i18n";
import { DigestReviewButton } from "./DigestReviewButton";

interface Props {
  subscriptions: Subscription[];
  onOpenForm: (c: CategoryCode) => void;
  onAddCategory: () => void;
  onOpenBase: () => void;
  onAdmin?: () => void;
  isAdmin?: boolean;
  onChange?: () => Promise<void> | void;
}

export function CategoryMenuScreen({
  subscriptions,
  onOpenForm,
  onAddCategory,
  onOpenBase,
  onAdmin,
  isAdmin,
  onChange,
}: Props) {
  const { t, lang, setLang } = useLang();
  const [pending, setPending] = useState<CategoryCode | null>(null);
  const canAdd = subscriptions.length < 4;
  const [delivery, setDelivery] = useState<DeliverySettings | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [base, setBase] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    // Ошибку глушим: кнопка дайджеста на главном экране необязательна.
    api.getDeliverySettings().then(setDelivery).catch(() => {});
    api.getBaseProfile().then(setBase).catch(() => {});
  }, []);

  const basePct = Math.max(0, Math.min(100, Number(base?.completion_pct ?? 0)));
  const baseDone = !!base?.completed;
  const baseSummary = [
    base?.full_name,
    base?.actual_age != null ? t(`${base.actual_age} лет`, `${base.actual_age} y.o.`) : null,
    base?.city,
  ].filter(Boolean).join(" · ");

  const toggle = async (sub: Subscription, e: React.MouseEvent) => {
    e.stopPropagation();
    setPending(sub.category);
    try {
      await api.patchSubscription(sub.category, !sub.enabled);
      if (onChange) await onChange();
    } finally {
      setPending(null);
    }
  };

  return (
    <div className="min-h-[100dvh] p-5 flex flex-col gap-4">
      <div className="flex justify-between items-center gap-2">
        <h1 className="text-2xl font-semibold">{t("Мои направления", "My categories")}</h1>
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => setLang(lang === "ru" ? "en" : "ru")}
            className="px-2.5 py-1.5 rounded-card text-xs font-medium border border-bg-card text-slate-300 hover:border-accent hover:text-accent transition"
            title={t("Сменить язык", "Switch language")}
          >
            {lang === "ru" ? "EN" : "RU"}
          </button>
          {isAdmin && (
            <button
              onClick={onAdmin}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-card text-xs text-accent hover:bg-accent/10 transition"
              title={t("Админка", "Admin panel")}
            >
              <ShieldCheck className="w-4 h-4" />
              {t("Админка", "Admin")}
            </button>
          )}
        </div>
      </div>
      {delivery?.delivery_mode === "digest" && (
        <div className="space-y-3">
          <DigestReviewButton
            pendingCount={delivery.pending_count}
            onEmpty={() => setDelivery((d) => (d ? { ...d, pending_count: 0 } : d))}
          />
        </div>
      )}

      {/* Основная информация — общие поля для всех анкет */}
      <button
        onClick={onOpenBase}
        className={`w-full p-4 rounded-card border-2 text-left transition ${
          baseDone ? "border-accent/40 bg-accent/5 hover:border-accent" : "border-amber-400/60 bg-amber-400/10"
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="shrink-0 w-10 h-10 rounded-full bg-accent/15 flex items-center justify-center">
            <UserRound className="w-5 h-5 text-accent" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-semibold">{t("Основная информация", "Basic information")}</div>
            <div className="text-xs text-slate-400 truncate">
              {baseDone && baseSummary
                ? baseSummary
                : t("Заполни один раз — подставится во все анкеты", "Fill in once — used in all applications")}
            </div>
          </div>
          {baseDone ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
          ) : (
            <span className="text-sm text-amber-400 tabular-nums shrink-0">{basePct}%</span>
          )}
          <ChevronRight className="w-4 h-4 text-slate-500 shrink-0" />
        </div>
        {!baseDone && (
          <div className="mt-3 h-1.5 w-full rounded-full bg-bg-card overflow-hidden">
            <div className="h-full bg-amber-400 transition-all" style={{ width: `${basePct}%` }} />
          </div>
        )}
      </button>

      {/* Направления — по центру оставшегося места */}
      <div className="flex-1 flex flex-col justify-center gap-3 py-2">
        <div className="text-xs uppercase tracking-wider text-slate-500 px-1">
          {t("Направления", "Categories")}
        </div>
        {subscriptions.map((s) => {
          const pct = Math.max(0, Math.min(100, s.completion_pct ?? (s.profile_completed ? 100 : 0)));
          const isComplete = s.profile_completed;
          const isPending = pending === s.category;
          return (
            <button
              key={s.category}
              onClick={() => onOpenForm(s.category)}
              className={`w-full p-4 rounded-card border transition text-left ${
                s.enabled
                  ? "border-bg-card hover:border-accent"
                  : "border-bg-card/40 opacity-60 hover:opacity-80"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <button
                  onClick={(e) => toggle(s, e)}
                  disabled={isPending}
                  className={`shrink-0 p-2 rounded-card transition ${
                    s.enabled
                      ? "text-accent hover:bg-accent/10"
                      : "text-slate-500 hover:text-slate-300 hover:bg-bg-card"
                  } ${isPending ? "opacity-50" : ""}`}
                  aria-label={s.enabled ? t("Выключить уведомления", "Turn off notifications") : t("Включить уведомления", "Turn on notifications")}
                  title={s.enabled ? t("Уведомления включены", "Notifications on") : t("Уведомления выключены", "Notifications off")}
                >
                  {s.enabled ? <Bell className="w-5 h-5" /> : <BellOff className="w-5 h-5" />}
                </button>
                <span className="font-medium flex-1 min-w-0">{t(CATEGORY_LABELS[s.category], CATEGORY_LABELS_EN[s.category])}</span>
                <span className="flex items-center gap-1.5 text-sm text-slate-400">
                  {isComplete ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      <span>{t("Заполнена", "Completed")}</span>
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
        {canAdd && (
          <button
            onClick={onAddCategory}
            className="w-full py-3 rounded-card border-2 border-dashed border-bg-card text-slate-400 hover:border-accent hover:text-accent transition flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {t("Добавить направление", "Add category")}
          </button>
        )}
      </div>
    </div>
  );
}
