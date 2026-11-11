import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { SelectField } from "../fields/SelectField";
import { MultiSelectField } from "../fields/MultiSelectField";
import { baseMissing, useCategoryFormState, type Data } from "../hooks/useCategoryFormState";
import { CategoryFormShell } from "../components/CategoryFormShell";
import { BaseInfoNotice } from "../components/BaseInfoNotice";
import { useLang } from "../i18n";

interface Props {
  onDone: () => void;
  onOpenBase: () => void;
}

// Обязательны поля, которые указаны хотя бы в половине творческих вакансий
// (db/repository._REQUIRED_FIELDS["creative"]): проекты, роли, игровой
// возраст (от и до — два пункта), ставка. Основная информация — один пункт.
const TOTAL_REQUIRED = 6;

function validate(data: Data, t: (ru: string, en: string) => string): string[] {
  const missing: string[] = [];
  if (baseMissing(data)) missing.push(t("Основная информация", "Basic information"));
  if (!data.project_types || data.project_types.length === 0) missing.push(t("Типы проектов", "Project types"));
  if (!data.role_types || data.role_types.length === 0) missing.push(t("Типы ролей", "Role types"));
  if (data.play_age_min == null) missing.push(t("Игровой возраст: от", "Playing age: from"));
  if (data.play_age_max == null) missing.push(t("Игровой возраст: до", "Playing age: to"));
  if (data.play_age_min != null && data.play_age_max != null && data.play_age_min > data.play_age_max) {
    missing.push(t("Игровой возраст («от» больше «до»)", "Playing age (\"from\" is greater than \"to\")"));
  }
  if (data.min_rate == null) missing.push(t("Минимальная ставка", "Minimum rate"));
  return missing;
}

export function CreativeForm({ onDone, onOpenBase }: Props) {
  const { t } = useLang();
  const { data, refs, loading, error, saving, update, finish } = useCategoryFormState({
    category: "creative",
    validate: (data) => validate(data, t),
    onDone,
  });

  if (loading || !refs) return <div className="p-6 text-slate-400">{t("Загрузка…", "Loading…")}</div>;

  const progressPct = Math.round(((TOTAL_REQUIRED - validate(data, t).length) / TOTAL_REQUIRED) * 100);

  return (
    <CategoryFormShell
      title={t("Анкета — Творческие позиции", "Application — Creative roles")}
      error={error}
      saving={saving}
      onSubmit={finish}
      progressPct={progressPct}
    >
      <BaseInfoNotice missing={baseMissing(data)} onOpen={onOpenBase} />

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Кастинги", "Castings")}</h3>
        <MultiSelectField
          label={t("Типы проектов", "Project types")}
          value={data.project_types ?? []}
          onChange={(v) => update({ project_types: v })}
          options={refs.project_types.map((p) => ({ value: p.code, label: p.label }))}
          required
        />
        <MultiSelectField
          label={t("Типы ролей", "Role types")}
          value={data.role_types ?? []}
          onChange={(v) => update({ role_types: v })}
          options={refs.role_types.map((r) => ({ value: r.code, label: r.label }))}
          required
        />
        <div className="grid grid-cols-2 gap-3">
          <NumberFieldWithAutocomplete
            field="play_age_min"
            label={t("Игровой возраст: от", "Playing age: from")}
            value={data.play_age_min ?? null}
            onChange={(v) => update({ play_age_min: v })}
            min={0}
            max={120}
            required
          />
          <NumberFieldWithAutocomplete
            field="play_age_max"
            label={t("до", "to")}
            value={data.play_age_max ?? null}
            onChange={(v) => update({ play_age_max: v })}
            min={0}
            max={120}
            required
          />
        </div>
        <NumberFieldWithAutocomplete
          field="min_rate"
          label={t("Минимальная ставка, ₽", "Minimum rate, ₽")}
          value={data.min_rate ?? null}
          onChange={(v) => update({ min_rate: v })}
          min={0}
          placeholder={t("0 — любая ставка", "0 — any rate")}
          required
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Внешность — по желанию", "Appearance — optional")}</h3>
        <p className="text-xs text-slate-500 -mt-1">
          {t(
            "Помогает отсеять кастинги, где ищут конкретную внешность.",
            "Helps filter out castings looking for a specific look.",
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
