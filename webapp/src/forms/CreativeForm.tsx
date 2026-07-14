import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { SelectField } from "../fields/SelectField";
import { MultiSelectField } from "../fields/MultiSelectField";
import { CITIES } from "../cities";
import { validateTelegramUser } from "../fields/telegramValidation";
import { useCategoryFormState, type Data } from "../hooks/useCategoryFormState";
import { CategoryFormShell } from "../components/CategoryFormShell";
import { useLang } from "../i18n";

interface Props {
  onDone: () => void;
}

const TOTAL_REQUIRED = 13;

function validate(data: Data, t: (ru: string, en: string) => string): string[] {
  const missing: string[] = [];
  if (!data.full_name?.trim()) missing.push(t("ФИО", "Full name"));
  if (!data.gender) missing.push(t("Пол", "Gender"));
  if (!data.city?.trim()) missing.push(t("Город", "City"));
  if (data.actual_age == null) missing.push(t("Возраст", "Age"));
  if (!data.project_types || data.project_types.length === 0) missing.push(t("Типы проектов", "Project types"));
  if (!data.role_types || data.role_types.length === 0) missing.push(t("Типы ролей", "Role types"));
  if (data.height_cm == null) missing.push(t("Рост, см", "Height, cm"));
  if (!data.ethnicity || data.ethnicity.length === 0) missing.push(t("Этнотип", "Ethnicity"));
  if (!data.body_type || data.body_type.length === 0) missing.push(t("Телосложение", "Body type"));
  if (!data.hair_color) missing.push(t("Цвет волос", "Hair color"));
  if (!data.hair_length) missing.push(t("Длина волос", "Hair length"));
  if (!data.phone?.trim()) missing.push(t("Телефон", "Phone"));
  if (!data.email?.trim()) missing.push(t("Email", "Email"));
  if (
    data.telegram_user &&
    data.telegram_user.trim() &&
    validateTelegramUser(data.telegram_user.trim(), t) !== null
  ) {
    missing.push(t("Telegram (исправь формат)", "Telegram (fix format)"));
  }
  return missing;
}

export function CreativeForm({ onDone }: Props) {
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
      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Основная информация", "Basic information")}</h3>
        <TextFieldWithAutocomplete
          field="full_name"
          label={t("ФИО", "Full name")}
          value={data.full_name ?? ""}
          onChange={(v) => update({ full_name: v })}
          required
        />
        <SelectField
          label={t("Пол", "Gender")}
          value={data.gender ?? null}
          onChange={(v) => update({ gender: v })}
          options={refs.genders.map((g) => ({ value: g.code, label: g.label }))}
          required
        />
        <TextFieldWithAutocomplete
          field="city"
          label={t("Город", "City")}
          staticSuggestions={CITIES}
          value={data.city ?? ""}
          onChange={(v) => update({ city: v })}
          required
        />
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={!!data.ready_for_travel}
            onChange={(e) => update({ ready_for_travel: e.target.checked })}
            className="accent-accent w-4 h-4"
          />
          {t("Готов(а) к командировкам", "Ready for business trips")}
        </label>
        <NumberFieldWithAutocomplete
          field="actual_age"
          label={t("Возраст", "Age")}
          value={data.actual_age ?? null}
          onChange={(v) => update({ actual_age: v })}
          min={14}
          max={80}
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
      </section>

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
          field="min_rate"
          label={t("Минимальная ставка, ₽", "Minimum rate, ₽")}
          value={data.min_rate ?? null}
          onChange={(v) => update({ min_rate: v })}
          min={0}
        />
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={data.show_negotiable ?? false}
            onChange={(e) => update({ show_negotiable: e.target.checked })}
            className="w-4 h-4 accent-accent"
          />
          {t("Показывать кастинги без указания ставки (по договорённости)", "Show castings without a listed rate (negotiable)")}
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={data.show_noncommercial ?? true}
            onChange={(e) => update({ show_noncommercial: e.target.checked })}
            className="w-4 h-4 accent-accent"
          />
          {t("Показывать некоммерческие проекты", "Show non-commercial projects")}
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={data.show_agency ?? true}
            onChange={(e) => update({ show_agency: e.target.checked })}
            className="w-4 h-4 accent-accent"
          />
          {t("Показывать кастинги от агентств", "Show castings from agencies")}
        </label>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Параметры", "Parameters")}</h3>
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
        <MultiSelectField
          label={t("Особые приметы", "Distinguishing marks")}
          value={data.marks ?? []}
          onChange={(v) => update({ marks: v })}
          options={refs.marks.map((m) => ({ value: m.code, label: m.label }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Профессиональное", "Professional")}</h3>
        <label className="block space-y-1">
          <span className="text-sm text-slate-400">{t("Опыт работы", "Work experience")}</span>
          <textarea
            value={data.experience_text ?? ""}
            onChange={(e) => update({ experience_text: e.target.value })}
            placeholder={t(
              "Опиши свой опыт: где снимался(ась), какие проекты, роли, агентства…",
              "Describe your experience: where you've worked, what projects, roles, agencies…",
            )}
            rows={4}
            maxLength={2000}
            className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent resize-none"
          />
        </label>
        <SelectField
          label={t("Образование", "Education")}
          value={data.education ?? null}
          onChange={(v) => update({ education: v })}
          options={refs.education.map((e) => ({ value: e.code, label: e.label }))}
        />
        <SelectField
          label={t("Налоговый статус", "Tax status")}
          value={data.tax_status ?? null}
          onChange={(v) => update({ tax_status: v })}
          options={refs.tax_status.map((tx) => ({ value: tx.code, label: tx.label }))}
        />
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
        <MultiSelectField
          label={t("Вокал", "Vocals")}
          value={data.skills_vocal ?? []}
          onChange={(v) => update({ skills_vocal: v })}
          options={refs.skills_vocal.map((s) => ({ value: s.code, label: s.label }))}
        />
        <MultiSelectField
          label={t("Инструменты", "Instruments")}
          value={data.skills_instruments ?? []}
          onChange={(v) => update({ skills_instruments: v })}
          options={refs.skills_instruments.map((s) => ({ value: s.code, label: s.label }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Материалы и контакты", "Materials and contacts")}</h3>
        <TextFieldWithAutocomplete
          field="portfolio_url"
          label={t("Портфолио", "Portfolio")}
          value={data.portfolio_url ?? ""}
          onChange={(v) => update({ portfolio_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="video_url"
          label={t("Видеовизитка", "Video reel")}
          value={data.video_url ?? ""}
          onChange={(v) => update({ video_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="professional_url"
          label={t("Проф. ресурс (e.g. casting.ru)", "Pro resource (e.g. casting.ru)")}
          value={data.professional_url ?? ""}
          onChange={(v) => update({ professional_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="phone"
          label={t("Телефон", "Phone")}
          value={data.phone ?? ""}
          onChange={(v) => update({ phone: v })}
          type="tel"
          required
        />
        <TextFieldWithAutocomplete
          field="telegram_user"
          label={t("Telegram username", "Telegram username")}
          value={data.telegram_user ?? ""}
          onChange={(v) => update({ telegram_user: v })}
          placeholder="@username"
          error={validateTelegramUser(data.telegram_user ?? "", t) ?? undefined}
        />
        <TextFieldWithAutocomplete
          field="vk_url"
          label={t("VK", "VK")}
          value={data.vk_url ?? ""}
          onChange={(v) => update({ vk_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="email"
          label={t("Email", "Email")}
          value={data.email ?? ""}
          onChange={(v) => update({ email: v })}
          type="email"
          required
        />
      </section>
    </CategoryFormShell>
  );
}
