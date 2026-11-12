import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, ShieldCheck, Plus, BellOff, UserRound, ChevronRight, Lock } from "lucide-react";
import { api } from "../api";
import type { CategoryCode, DeliverySettings, Subscription } from "../types";
import {
  CATEGORY_DESCRIPTIONS,
  CATEGORY_DESCRIPTIONS_EN,
  CATEGORY_LABELS,
  CATEGORY_LABELS_EN,
} from "../types";

const ALL_CATEGORIES: CategoryCode[] = ["creative", "event", "general", "admin"];
import { useLang } from "../i18n";
import { DigestReviewButton } from "./DigestReviewButton";

interface Props {
  subscriptions: Subscription[];
  onOpenForm: (c: CategoryCode) => void;
  /** Невыбранное направление: подписать юзера и открыть анкету. */
  onStartCategory: (c: CategoryCode) => Promise<void>;
  onOpenBase: () => void;
  onAdmin?: () => void;
  isAdmin?: boolean;
}

function yearsRu(n: number): string {
  if (n % 100 >= 11 && n % 100 <= 14) return "лет";
  if (n % 10 === 1) return "год";
  if (n % 10 >= 2 && n % 10 <= 4) return "года";
  return "лет";
}

export function CategoryMenuScreen({
  subscriptions,
  onOpenForm,
  onStartCategory,
  onOpenBase,
  onAdmin,
  isAdmin,
}: Props) {
  const { t, lang, setLang } = useLang();
  const [starting, setStarting] = useState<CategoryCode | null>(null);

  const start = async (c: CategoryCode) => {
    if (starting) return;
    setStarting(c);
    try {
      await onStartCategory(c);
    } finally {
      setStarting(null);
    }
  };
  const [delivery, setDelivery] = useState<DeliverySettings | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [base, setBase] = useState<Record<string, any> | null>(null);
  // null — ещё грузим; false — не удалось получить (тогда не блокируем).
  const [baseLoaded, setBaseLoaded] = useState<boolean | null>(null);

  useEffect(() => {
    // Ошибку глушим: кнопка дайджеста на главном экране необязательна.
    api.getDeliverySettings().then(setDelivery).catch(() => {});
    api
      .getBaseProfile()
      .then((b) => {
        setBase(b);
        setBaseLoaded(true);
      })
      .catch(() => setBaseLoaded(false));
  }, []);

  const basePct = Math.max(0, Math.min(100, Number(base?.completion_pct ?? 0)));
  const baseDone = !!base?.completed;
  // Направления доступны только после «Основной информации».
  const locked = baseLoaded === null || (baseLoaded === true && !baseDone);
  const baseSummary = [
    base?.full_name,
    base?.actual_age != null
      ? t(`${base.actual_age} ${yearsRu(Number(base.actual_age))}`, `${base.actual_age} y.o.`)
      : null,
    base?.city,
  ].filter(Boolean).join(" · ");

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

      {/* Направления — сразу под «Основной информацией» */}
      <div className="flex flex-col gap-3 pt-2">
        <div className="text-xs uppercase tracking-wider text-slate-500 px-1">
          {t("Направления", "Categories")}
        </div>
        {locked && baseLoaded && (
          <div className="flex items-center gap-2 px-1 text-xs text-amber-400">
            <Lock className="w-3.5 h-3.5 shrink-0" />
            {t(
              "Сначала заполни основную информацию — потом откроются анкеты направлений.",
              "Fill in your basic information first — then the category forms unlock.",
            )}
          </div>
        )}
        {ALL_CATEGORIES.map((c) => {
          const s = subscriptions.find((x) => x.category === c);
          if (locked) {
            // До заполнения «Основной информации» анкеты закрыты: нажатие ведёт туда.
            return (
              <button
                key={c}
                onClick={onOpenBase}
                className="w-full p-4 rounded-card border border-bg-card text-left transition opacity-50 hover:opacity-70"
              >
                <div className="flex items-center gap-3">
                  <div className="shrink-0 p-2 text-slate-500">
                    <Lock className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-300">{t(CATEGORY_LABELS[c], CATEGORY_LABELS_EN[c])}</div>
                    <div className="text-xs text-slate-500 truncate">
                      {t(CATEGORY_DESCRIPTIONS[c], CATEGORY_DESCRIPTIONS_EN[c])}
                    </div>
                  </div>
                  {s?.profile_completed && <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />}
                </div>
              </button>
            );
          }
          if (!s) {
            // Направление ещё не выбрано: нажатие добавляет его и открывает анкету.
            return (
              <button
                key={c}
                onClick={() => start(c)}
                disabled={starting !== null}
                className="w-full p-4 rounded-card border border-dashed border-bg-card text-left transition hover:border-accent disabled:opacity-60"
              >
                <div className="flex items-center gap-3">
                  <div className="shrink-0 p-2 text-slate-500">
                    <Plus className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-slate-300">{t(CATEGORY_LABELS[c], CATEGORY_LABELS_EN[c])}</div>
                    <div className="text-xs text-slate-500 truncate">
                      {t(CATEGORY_DESCRIPTIONS[c], CATEGORY_DESCRIPTIONS_EN[c])}
                    </div>
                  </div>
                  <span className="text-sm text-accent shrink-0">
                    {starting === c ? t("Открываем…", "Opening…") : t("Заполнить", "Fill in")}
                  </span>
                </div>
              </button>
            );
          }
          const pct = Math.max(0, Math.min(100, s.completion_pct ?? (s.profile_completed ? 100 : 0)));
          const isComplete = s.profile_completed;
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
                <span className="font-medium flex-1 min-w-0">{t(CATEGORY_LABELS[s.category], CATEGORY_LABELS_EN[s.category])}</span>
                {!s.enabled && (
                  <span
                    className="flex items-center gap-1 text-xs text-slate-500"
                    title={t("Уведомления выключены", "Notifications off")}
                  >
                    <BellOff className="w-4 h-4" />
                  </span>
                )}
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
      </div>
    </div>
  );
}
