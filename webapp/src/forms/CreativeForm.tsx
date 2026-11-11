import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
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

const TOTAL_REQUIRED = 8;

function validate(data: Data, t: (ru: string, en: string) => string): string[] {
  const missing: string[] = [];
  if (baseMissing(data)) missing.push(t("Основная информация", "Basic information"));
  if (!data.project_types || data.project_types.length === 0) missing.push(t("Типы проектов", "Project types"));
  if (!data.role_types || data.role_types.length === 0) missing.push(t("Типы ролей", "Role types"));
  if (data.height_cm == null) missing.push(t("Рост, см", "Height, cm"));
  if (!data.ethnicity || data.ethnicity.length === 0) missing.push(t("Этнотип", "Ethnicity"));
  if (!data.body_type || data.body_type.length === 0) missing.push(t("Телосложение", "Body type"));
  if (!data.hair_color) missing.push(t("Цвет волос", "Hair color"));
  if (!data.hair_length) missing.push(t("Длина волос", "Hair length"));
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
        <NumberFieldWithAutocomplete
          field="play_age_min"
          label={t("Игровой возраст: от", "Playing age: from")}
          value={data.play_age_min ?? null}
          onChange={(v) => update({ play_age_min: v })}
          min={0}
          max={120}
        />
        <NumberFieldWithAutocomplete
          field="play_age_max"
          label={t("Игровой возраст: до", "Playing age: to")}
          value={data.play_age_max ?? null}
          onChange={(v) => update({ play_age_max: v })}
          min={0}
          max={120}
        />
        <NumberFieldWithAutocomplete
          field="min_rate"
          label={t("Минимальная ставка, ₽", "Minimum rate, ₽")}
          value={data.min_rate ?? null}
          onChange={(v) => update({ min_rate: v })}
          min={0}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Внешность", "Appearance")}</h3>
        <NumberFieldWithAutocomplete
          field="height_cm"
          label={t("Рост, см", "Height, cm")}
          value={data.height_cm ?? null}
          onChange={(v) => update({ height_cm: v })}
          min={120}
          max={220}
          required
        />
        <NumberFieldWithAutocomplete
          field="clothing_size"
          label={t("Размер одежды", "Clothing size")}
          value={data.clothing_size ?? null}
          onChange={(v) => update({ clothing_size: v })}
          min={20}
          max={80}
        />
        <NumberFieldWithAutocomplete
          field="shoe_size"
          label={t("Размер обуви", "Shoe size")}
          value={data.shoe_size ?? null}
          onChange={(v) => update({ shoe_size: v })}
          min={30}
          max={55}
        />
        <MultiSelectField
          label={t("Этнотип", "Ethnicity")}
          value={data.ethnicity ?? []}
          onChange={(v) => update({ ethnicity: v })}
          options={refs.ethnicity.map((e) => ({ value: e.code, label: e.label }))}
          required
        />
        <MultiSelectField
          label={t("Телосложение", "Body type")}
          value={data.body_type ?? []}
          onChange={(v) => update({ body_type: v })}
          options={refs.body_type.map((b) => ({ value: b.code, label: b.label }))}
          required
        />
        <SelectField
          label={t("Цвет волос", "Hair color")}
          value={data.hair_color ?? null}
          onChange={(v) => update({ hair_color: v })}
          options={refs.hair_colors.map((h) => ({ value: h.code, label: h.label }))}
          required
        />
        <SelectField
          label={t("Длина волос", "Hair length")}
          value={data.hair_length ?? null}
          onChange={(v) => update({ hair_length: v })}
          options={refs.hair_lengths.map((h) => ({ value: h.code, label: h.label }))}
          required
        />
        <SelectField
          label={t("Цвет глаз", "Eye color")}
          value={data.eye_color ?? null}
          onChange={(v) => update({ eye_color: v })}
          options={refs.eye_colors.map((e) => ({ value: e.code, label: e.label }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Навыки и портфолио", "Skills and portfolio")}</h3>
        <MultiSelectField
          label={t("Спорт", "Sports")}
          value={data.skills_sport ?? []}
          onChange={(v) => update({ skills_sport: v })}
          options={refs.skills_sport.map((s) => ({ value: s.code, label: s.label }))}
        />
        <MultiSelectField
          label={t("Танцы", "Dance")}
          value={data.skills_dance ?? []}
          onChange={(v) => update({ skills_dance: v })}
          options={refs.skills_dance.map((s) => ({ value: s.code, label: s.label }))}
        />
        <SelectField
          label={t("Образование", "Education")}
          value={data.education ?? null}
          onChange={(v) => update({ education: v })}
          options={refs.education.map((e) => ({ value: e.code, label: e.label }))}
        />
        <TextFieldWithAutocomplete
          field="portfolio_url"
          label={t("Портфолио", "Portfolio")}
          value={data.portfolio_url ?? ""}
          onChange={(v) => update({ portfolio_url: v })}
          type="url"
        />
      </section>
    </CategoryFormShell>
  );
}
