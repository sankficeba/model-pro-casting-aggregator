import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { SelectField } from "../fields/SelectField";
import { CITIES } from "../cities";
import { validateTelegramUser } from "../fields/telegramValidation";
import { useCategoryFormState, type Data } from "../hooks/useCategoryFormState";
import { CategoryFormShell } from "../components/CategoryFormShell";
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
}

const TOTAL_REQUIRED = 7;

function validate(data: Data, t: (ru: string, en: string) => string): string[] {
  const missing: string[] = [];
  if (!data.full_name?.trim()) missing.push(t("ФИО", "Full name"));
  if (!data.gender) missing.push(t("Пол", "Gender"));
  if (!data.city?.trim()) missing.push(t("Город", "City"));
  if (data.actual_age == null) missing.push(t("Возраст", "Age"));
  if (!data.work_types || data.work_types.length === 0) missing.push(t("Должности", "Positions"));
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

export function EventForm({ onDone }: Props) {
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
          {t("Показывать кастинги без указания ставки", "Show castings without a listed rate")}
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

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Опыт", "Experience")}</h3>
        <MultiSelectField
          label={t("Выберите интересующие вас должности", "Select the positions you're interested in")}
          value={data.work_types ?? []}
          onChange={(v) => update({ work_types: v })}
          options={getWorkTypes(t)}
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
        <SelectField
          label={t("Налоговый статус", "Tax status")}
          value={data.tax_status ?? null}
          onChange={(v) => update({ tax_status: v })}
          options={refs.tax_status.map((tx) => ({ value: tx.code, label: tx.label }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Контакты", "Contacts")}</h3>
        <TextFieldWithAutocomplete
          field="portfolio_url"
          label={t("Фото-портфолио", "Photo portfolio")}
          value={data.portfolio_url ?? ""}
          onChange={(v) => update({ portfolio_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="video_url"
          label={t("Видео-портфолио", "Video portfolio")}
          value={data.video_url ?? ""}
          onChange={(v) => update({ video_url: v })}
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
          label={t("Telegram", "Telegram")}
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
