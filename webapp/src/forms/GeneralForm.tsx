import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { baseMissing, useCategoryFormState, type Data } from "../hooks/useCategoryFormState";
import { CategoryFormShell } from "../components/CategoryFormShell";
import { BaseInfoNotice } from "../components/BaseInfoNotice";
import { useLang } from "../i18n";

interface Props {
  onDone: () => void;
  onOpenBase: () => void;
}

const TOTAL_REQUIRED = 3;

function validate(data: Data, t: (ru: string, en: string) => string): string[] {
  const missing: string[] = [];
  if (baseMissing(data)) missing.push(t("Основная информация", "Basic information"));
  if (!data.work_types || data.work_types.length === 0) missing.push(t("Типы работ", "Work types"));
  if (data.min_rate == null) missing.push(t("Минимальная ставка", "Minimum rate"));
  return missing;
}

export function GeneralForm({ onDone, onOpenBase }: Props) {
  const { t } = useLang();
  const { data, refs, loading, error, saving, update, finish } = useCategoryFormState({
    category: "general",
    validate: (data) => validate(data, t),
    onDone,
    initial: { work_types: [] },
  });

  if (loading || !refs) return <div className="p-6 text-slate-400">{t("Загрузка…", "Loading…")}</div>;

  const progressPct = Math.round(((TOTAL_REQUIRED - validate(data, t).length) / TOTAL_REQUIRED) * 100);

  return (
    <CategoryFormShell
      title={t("Анкета — Разнорабочие", "Application — General labor")}
      error={error}
      saving={saving}
      onSubmit={finish}
      progressPct={progressPct}
    >
      <BaseInfoNotice missing={baseMissing(data)} onOpen={onOpenBase} />

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Работа", "Work")}</h3>
        <MultiSelectField
          label={t("Типы работ", "Work types")}
          value={data.work_types ?? []}
          onChange={(v) => update({ work_types: v })}
          options={refs.work_types_general.map((w) => ({ value: w.code, label: w.label }))}
          required
        />
        <NumberFieldWithAutocomplete
          field="min_rate"
          label={t("Минимальная ставка, ₽", "Minimum rate, ₽")}
          value={data.min_rate ?? null}
          onChange={(v) => update({ min_rate: v })}
          min={0}
          placeholder={t("0 — любая ставка", "0 — any rate")}
          required
        />
        <label className="block space-y-1">
          <span className="text-sm text-slate-400">{t("Опыт работы", "Work experience")}</span>
          <textarea
            value={data.experience_text ?? ""}
            onChange={(e) => update({ experience_text: e.target.value })}
            placeholder={t(
              "Опиши свой опыт: где работал(а), сколько по времени, какие задачи выполнял(а)…",
              "Describe your experience: where you've worked, how long, what tasks you performed…",
            )}
            rows={4}
            maxLength={2000}
            className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent resize-none"
          />
        </label>
      </section>
    </CategoryFormShell>
  );
}
