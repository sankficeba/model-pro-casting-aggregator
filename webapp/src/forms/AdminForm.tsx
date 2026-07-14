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
    { value: "registration_operator", label: t("Оператор регистрации", "Registration operator") },
    { value: "supervisor", label: t("Супервайзер", "Supervisor") },
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
  if (!data.work_types || data.work_types.length === 0) missing.push(t("Типы работ", "Work types"));
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

export function AdminForm({ onDone }: Props) {
  const { t } = useLang();
  const { data, refs, loading, error, saving, update, finish } = useCategoryFormState({
    category: "admin",
    validate: (data) => validate(data, t),
    onDone,
    initial: { work_types: [] },
  });

  if (loading || !refs) return <div className="p-6 text-slate-400">{t("Загрузка…", "Loading…")}</div>;

  const progressPct = Math.round(((TOTAL_REQUIRED - validate(data, t).length) / TOTAL_REQUIRED) * 100);

  return (
    <CategoryFormShell
      title={t("Анкета — Администрирование", "Application — Administration")}
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
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("Опыт", "Experience")}</h3>
        <SelectField
          label={t("Образование", "Education")}
          value={data.education ?? null}
          onChange={(v) => update({ education: v })}
          options={refs.education.map((e) => ({ value: e.code, label: e.label }))}
        />
        <MultiSelectField
          label={t("Типы работ", "Work types")}
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
              "Опиши свой опыт: где работал(а), сколько по времени, какие задачи выполнял(а)…",
              "Describe your experience: where you've worked, how long, what tasks you performed…",
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
