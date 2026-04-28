import { useEffect, useState } from "react";
import { api } from "./api";
import { EMPTY_PROFILE, type Profile, type Refs } from "./types";
import { getInitData, haptic, initTelegram, isInTelegram } from "./telegram";
import { Step1, Step2, Step3, Step4, Step5, Step6 } from "./components/steps";
import { PrimaryButton, ProgressBar } from "./components/ui";

const TOTAL_STEPS = 6;

const PROGRESS_HINTS: Record<number, string> = {
  1: "Мы начинаем подбирать для вас кастинги.",
  2: "Уточняем тип проектов и условия.",
  3: "Отлично — параметры помогут точнее подбирать.",
  4: "Профессиональный профиль почти заполнен.",
  5: "Чем больше навыков — тем точнее подбор.",
  6: "Заполните email, чтобы завершить регистрацию.",
};

export default function App() {
  const [step, setStep] = useState<number>(1);
  const [refs, setRefs] = useState<Refs | null>(null);
  const [profile, setProfile] = useState<Profile>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedToast, setSavedToast] = useState<string | null>(null);

  // Старт
  useEffect(() => {
    initTelegram();
    (async () => {
      try {
        const [r, p] = await Promise.all([api.getRefs(), api.getProfile()]);
        setRefs(r);
        setProfile({ ...EMPTY_PROFILE, ...p });
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function patch(p: Partial<Profile>) {
    setProfile((prev) => ({ ...prev, ...p }));
  }

  async function save(showToast = true): Promise<boolean> {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateProfile(profile);
      setProfile({ ...EMPTY_PROFILE, ...updated });
      if (showToast) {
        setSavedToast("Сохранено");
        setTimeout(() => setSavedToast(null), 1800);
      }
      return true;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function next() {
    haptic("light");
    if (step < TOTAL_STEPS) {
      const ok = await save(false);
      if (ok) setStep(step + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      await save(true);
    }
  }

  function back() {
    haptic("light");
    if (step > 1) setStep(step - 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ----- Render -----

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">
        Загружаем анкету…
      </div>
    );
  }

  if (error && !refs) {
    return (
      <div className="min-h-screen p-6 space-y-4">
        <h1 className="text-xl font-semibold text-red-400">Не удалось загрузить</h1>
        <p className="text-sm text-slate-300 break-words">{error}</p>
        {!isInTelegram() && (
          <p className="text-xs text-slate-500">
            Похоже, страница открыта вне Telegram — initData отсутствует, бэкенд
            возвращает 401. Откройте Mini App из бота.
          </p>
        )}
      </div>
    );
  }

  const progressPct = profile.completion_pct ?? 0;
  const stepProps = { profile, refs: refs!, patch };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <div className="px-5 pt-5 pb-3 sticky top-0 bg-bg z-10">
        <div className="flex items-center gap-3 mb-3">
          {step > 1 && (
            <button
              onClick={back}
              className="text-slate-400 hover:text-white transition"
              aria-label="Назад"
            >
              ←
            </button>
          )}
          <ProgressBar pct={(step / TOTAL_STEPS) * 100} />
          <span className="text-xs text-slate-500 tabular-nums">
            {step}/{TOTAL_STEPS}
          </span>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 px-5 pb-32">
        {step === 1 && <Step1 {...stepProps} />}
        {step === 2 && <Step2 {...stepProps} />}
        {step === 3 && <Step3 {...stepProps} />}
        {step === 4 && <Step4 {...stepProps} />}
        {step === 5 && <Step5 {...stepProps} />}
        {step === 6 && <Step6 {...stepProps} />}

        {/* Хинт прогресса */}
        <div className="mt-6 rounded-card bg-bg-surface px-4 py-3 flex items-baseline gap-3">
          <span className="text-accent text-lg font-bold">{progressPct}%</span>
          <span className="text-sm text-slate-300">
            {PROGRESS_HINTS[step] ?? `${progressPct}% профиля заполнено`}
          </span>
        </div>

        {error && (
          <div className="mt-4 rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}
      </main>

      {/* Toast */}
      {savedToast && (
        <div className="fixed bottom-24 left-1/2 -translate-x-1/2 px-4 py-2 rounded-full bg-green-700 text-white text-sm shadow-lg">
          ✓ {savedToast}
        </div>
      )}

      {/* Bottom action */}
      <div className="fixed bottom-0 inset-x-0 px-5 py-4 bg-bg/90 backdrop-blur border-t border-bg-card">
        <PrimaryButton onClick={next} disabled={saving}>
          {saving ? "Сохраняем…" : step < TOTAL_STEPS ? "Продолжить" : "Завершить"}
        </PrimaryButton>
        {!isInTelegram() && (
          <p className="text-[10px] text-slate-500 mt-2 text-center">
            dev-режим: initData={getInitData() ? "✓" : "—"}
          </p>
        )}
      </div>
    </div>
  );
}
