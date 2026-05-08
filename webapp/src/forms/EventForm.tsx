import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { SelectField } from "../fields/SelectField";
import { CITIES } from "../cities";
import { validateTelegramUser } from "../fields/telegramValidation";
import { useCategoryFormState, type Data } from "../hooks/useCategoryFormState";
import { CategoryFormShell } from "../components/CategoryFormShell";

const WORK_TYPES = [
  { value: "hostess", label: "Хостес" },
  { value: "promo_model", label: "Промо-модель" },
  { value: "animator", label: "Аниматор" },
];

interface Props {
  onDone: () => void;
}

const TOTAL_REQUIRED = 7;

function validate(data: Data): string[] {
  const missing: string[] = [];
  if (!data.full_name?.trim()) missing.push("ФИО");
  if (!data.gender) missing.push("Пол");
  if (!data.city?.trim()) missing.push("Город");
  if (data.actual_age == null) missing.push("Возраст");
  if (!data.work_types || data.work_types.length === 0) missing.push("Должности");
  if (!data.phone?.trim()) missing.push("Телефон");
  if (!data.email?.trim()) missing.push("Email");
  if (
    data.telegram_user &&
    data.telegram_user.trim() &&
    validateTelegramUser(data.telegram_user.trim()) !== null
  ) {
    missing.push("Telegram (исправь формат)");
  }
  return missing;
}

export function EventForm({ onDone }: Props) {
  const { data, refs, loading, error, saving, update, finish } = useCategoryFormState({
    category: "event",
    validate,
    onDone,
    initial: { work_types: [] },
  });

  if (loading || !refs) return <div className="p-6 text-slate-400">Загрузка…</div>;

  const progressPct = Math.round(((TOTAL_REQUIRED - validate(data).length) / TOTAL_REQUIRED) * 100);

  return (
    <CategoryFormShell
      title="Анкета — Event-персонал"
      error={error}
      saving={saving}
      onSubmit={finish}
      progressPct={progressPct}
    >
      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">Основная информация</h3>
        <TextFieldWithAutocomplete
          field="full_name"
          label="ФИО"
          value={data.full_name ?? ""}
          onChange={(v) => update({ full_name: v })}
          required
        />
        <SelectField
          label="Пол"
          value={data.gender ?? null}
          onChange={(v) => update({ gender: v })}
          options={refs.genders.map((g) => ({ value: g.code, label: g.label }))}
          required
        />
        <TextFieldWithAutocomplete
          field="city"
          label="Город"
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
          Готов(а) к командировкам
        </label>
        <NumberFieldWithAutocomplete
          field="actual_age"
          label="Возраст"
          value={data.actual_age ?? null}
          onChange={(v) => update({ actual_age: v })}
          min={14}
          max={80}
          required
        />
        <NumberFieldWithAutocomplete
          field="min_rate"
          label="Минимальная ставка, ₽"
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
          Показывать кастинги без указания ставки
        </label>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={data.show_noncommercial ?? true}
            onChange={(e) => update({ show_noncommercial: e.target.checked })}
            className="w-4 h-4 accent-accent"
          />
          Показывать некоммерческие проекты
        </label>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">Параметры</h3>
        <NumberFieldWithAutocomplete
          field="height_cm"
          label="Рост, см"
          value={data.height_cm ?? null}
          onChange={(v) => update({ height_cm: v })}
          min={120}
          max={220}
        />
        <NumberFieldWithAutocomplete
          field="clothing_size"
          label="Размер одежды"
          value={data.clothing_size ?? null}
          onChange={(v) => update({ clothing_size: v })}
          min={20}
          max={80}
        />
        <NumberFieldWithAutocomplete
          field="shoe_size"
          label="Размер обуви"
          value={data.shoe_size ?? null}
          onChange={(v) => update({ shoe_size: v })}
          min={30}
          max={55}
        />
        <MultiSelectField
          label="Этнотип"
          value={data.ethnicity ?? []}
          onChange={(v) => update({ ethnicity: v })}
          options={refs.ethnicity.map((e) => ({ value: e.code, label: e.label }))}
        />
        <MultiSelectField
          label="Телосложение"
          value={data.body_type ?? []}
          onChange={(v) => update({ body_type: v })}
          options={refs.body_type.map((b) => ({ value: b.code, label: b.label }))}
        />
        <SelectField
          label="Цвет волос"
          value={data.hair_color ?? null}
          onChange={(v) => update({ hair_color: v })}
          options={refs.hair_colors.map((h) => ({ value: h.code, label: h.label }))}
        />
        <SelectField
          label="Длина волос"
          value={data.hair_length ?? null}
          onChange={(v) => update({ hair_length: v })}
          options={refs.hair_lengths.map((h) => ({ value: h.code, label: h.label }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">Опыт</h3>
        <MultiSelectField
          label="Выберите интересующие вас должности"
          value={data.work_types ?? []}
          onChange={(v) => update({ work_types: v })}
          options={WORK_TYPES}
          required
        />
        <label className="block space-y-1">
          <span className="text-sm text-slate-400">Опыт работы</span>
          <textarea
            value={data.experience_text ?? ""}
            onChange={(e) => update({ experience_text: e.target.value })}
            placeholder="Опиши свой опыт: где работал(а), сколько по времени, в каких форматах…"
            rows={4}
            maxLength={2000}
            className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent resize-none"
          />
        </label>
        <SelectField
          label="Налоговый статус"
          value={data.tax_status ?? null}
          onChange={(v) => update({ tax_status: v })}
          options={refs.tax_status.map((t) => ({ value: t.code, label: t.label }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">Контакты</h3>
        <TextFieldWithAutocomplete
          field="portfolio_url"
          label="Фото-портфолио"
          value={data.portfolio_url ?? ""}
          onChange={(v) => update({ portfolio_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="video_url"
          label="Видео-портфолио"
          value={data.video_url ?? ""}
          onChange={(v) => update({ video_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="phone"
          label="Телефон"
          value={data.phone ?? ""}
          onChange={(v) => update({ phone: v })}
          type="tel"
          required
        />
        <TextFieldWithAutocomplete
          field="telegram_user"
          label="Telegram"
          value={data.telegram_user ?? ""}
          onChange={(v) => update({ telegram_user: v })}
          placeholder="@username"
          error={validateTelegramUser(data.telegram_user ?? "") ?? undefined}
        />
        <TextFieldWithAutocomplete
          field="vk_url"
          label="VK"
          value={data.vk_url ?? ""}
          onChange={(v) => update({ vk_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="email"
          label="Email"
          value={data.email ?? ""}
          onChange={(v) => update({ email: v })}
          type="email"
          required
        />
      </section>
    </CategoryFormShell>
  );
}
