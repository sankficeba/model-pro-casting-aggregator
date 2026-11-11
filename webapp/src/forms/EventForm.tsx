import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { SelectField } from "../fields/SelectField";
import { baseMissing, useCategoryFormState, type Data } from "../hooks/useCategoryFormState";
import { CategoryFormShell } from "../components/CategoryFormShell";
import { BaseInfoNotice } from "../components/BaseInfoNotice";
import { useLang } from "../i18n";

function getWorkTypes(t: (ru: string, en: string) => string) {
  return [
    { value: "hostess", label: t("Хостес", "Hostess") },
    { value: "promo_model", label: t("Промо-модель", "Promo model") },
    { value: "animator", label: t("Аниматор", "Entertainer") },
  ];
}

interface Props {
  onDone: () => void;
  onOpenBase: () => void;
}

const TOTAL_REQUIRED = 3;

function validate(data: Data, t: (ru: string, en: string) => string): string[] {
  const missing: string[] = [];
  if (baseMissing(data)) missing.push(t("Основная информация", "Basic information"));
  if (!data.work_types || data.work_types.length === 0) missing.push(t("Должности", "Positions"));
  if (data.min_rate == null) missing.push(t("Минимальная ставка", "Minimum rate"));
  return missing;
}

export function EventForm({ onDone, onOpenBase }: Props) {
  const { t } = useLang();
  const { data, refs, loading, error, saving, update, finish } = useCategoryFormState({
    category: "event",
    validate: (data) => validate(data, t),
    onDone,
    initial: { work_types: [] },
  });

  if (loading || !refs) return <div className="p-6 text-slate-400">{t("Загрузка…", "Loading…")}</div>;

  const progressPct = Math.round(((TOTAL_REQUIRED - validate(data, t).length) / TOTAL_REQUIRED) * 100);

  return (
    <CategoryFormShell
      title={t("Анкета — Event-персонал", "Application — Event staff")}
      error={error}
      saving={saving}
      onSubmit={finish}
      progressPct={progressPct}
    >
      <BaseInfoNotice missing={baseMissing(data)} onOpen={onOpenBase} />

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Работа", "Work")}</h3>
        <MultiSelectField
          label={t("Выберите интересующие вас должности", "Select the positions you're interested in")}
          value={data.work_types ?? []}
          onChange={(v) => update({ work_types: v })}
          options={getWorkTypes(t)}
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
              "Опиши свой опыт: где работал(а), сколько по времени, в каких форматах…",
              "Describe your experience: where you've worked, how long, in what formats…",
            )}
            rows={4}
            maxLength={2000}
            className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent resize-none"
          />
        </label>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Внешность — по желанию", "Appearance — optional")}</h3>
        <p className="text-xs text-slate-500 -mt-1">
          {t(
            "Помогает отсеять вакансии, где ищут конкретную внешность.",
            "Helps filter out postings looking for a specific look.",
          )}
        </p>
        <NumberFieldWithAutocomplete
          field="height_cm"
          label={t("Рост, см", "Height, cm")}
          value={data.height_cm ?? null}
          onChange={(v) => update({ height_cm: v })}
          min={120}
          max={220}
        />
        <MultiSelectField
          label={t("Этнотип", "Ethnicity")}
          value={data.ethnicity ?? []}
          onChange={(v) => update({ ethnicity: v })}
          options={refs.ethnicity.map((e) => ({ value: e.code, label: e.label }))}
        />
        <MultiSelectField
          label={t("Телосложение", "Body type")}
          value={data.body_type ?? []}
          onChange={(v) => update({ body_type: v })}
          options={refs.body_type.map((b) => ({ value: b.code, label: b.label }))}
        />
        <SelectField
          label={t("Цвет волос", "Hair color")}
          value={data.hair_color ?? null}
          onChange={(v) => update({ hair_color: v })}
          options={refs.hair_colors.map((h) => ({ value: h.code, label: h.label }))}
        />
        <SelectField
          label={t("Длина волос", "Hair length")}
          value={data.hair_length ?? null}
          onChange={(v) => update({ hair_length: v })}
          options={refs.hair_lengths.map((h) => ({ value: h.code, label: h.label }))}
        />
      </section>
    </CategoryFormShell>
  );
}
