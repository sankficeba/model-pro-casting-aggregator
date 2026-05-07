import { useEffect, useState, useRef } from "react";
import { api } from "../api";
import type { Refs } from "../types";
import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { SelectField } from "../fields/SelectField";
import { MultiSelectField } from "../fields/MultiSelectField";
import { CITIES } from "../cities";
import { useSuggestionsRefresh } from "../contexts/SuggestionsContext";
import { validateTelegramUser } from "../fields/telegramValidation";

interface Props {
  onDone: () => void;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Data = Record<string, any>;

export function CreativeForm({ onDone }: Props) {
  const [data, setData] = useState<Data>({});
  const [refs, setRefs] = useState<Refs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshSuggestions = useSuggestionsRefresh();

  useEffect(() => {
    refreshSuggestions();
  }, [refreshSuggestions]);

  useEffect(() => {
    Promise.all([api.getCategoryProfile("creative"), api.getRefs()])
      .then(([p, r]) => {
        setData(p as Data);
        setRefs(r);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const update = (patch: Data) => {
    setData((prev) => {
      const next = { ...prev, ...patch };
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        api.putCategoryProfile("creative", next).catch(() => {});
      }, 400);
      return next;
    });
  };

  const finish = async () => {
    setSaving(true);
    setError(null);
    try {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      await api.putCategoryProfile("creative", data);
      await api.completeCategoryProfile("creative");
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading || !refs)
    return <div className="p-6 text-slate-400">Загрузка…</div>;

  const expValue =
    data.has_experience === true
      ? "yes"
      : data.has_experience === false
        ? "no"
        : null;
  const expChange = (v: string | null) =>
    update({
      has_experience: v === "yes" ? true : v === "no" ? false : null,
    });

  return (
    <div className="min-h-screen p-5 pb-32 space-y-6">
      <h2 className="text-xl font-semibold">Анкета — Творческие позиции</h2>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">
          Основная информация
        </h3>
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
          field="play_age_min"
          label="Игровой возраст: от"
          value={data.play_age_min ?? null}
          onChange={(v) => update({ play_age_min: v })}
          min={0}
          max={120}
        />
        <NumberFieldWithAutocomplete
          field="play_age_max"
          label="Игровой возраст: до"
          value={data.play_age_max ?? null}
          onChange={(v) => update({ play_age_max: v })}
          min={0}
          max={120}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">
          Кастинги
        </h3>
        <MultiSelectField
          label="Типы проектов"
          value={data.project_types ?? []}
          onChange={(v) => update({ project_types: v })}
          options={refs.project_types.map((p) => ({
            value: p.code,
            label: p.label,
          }))}
          required
        />
        <MultiSelectField
          label="Типы ролей"
          value={data.role_types ?? []}
          onChange={(v) => update({ role_types: v })}
          options={refs.role_types.map((r) => ({
            value: r.code,
            label: r.label,
          }))}
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
          Показывать кастинги без указания ставки (по договорённости)
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
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={data.show_agency ?? true}
            onChange={(e) => update({ show_agency: e.target.checked })}
            className="w-4 h-4 accent-accent"
          />
          Показывать кастинги от агентств
        </label>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">
          Параметры
        </h3>
        <NumberFieldWithAutocomplete
          field="height_cm"
          label="Рост, см"
          value={data.height_cm ?? null}
          onChange={(v) => update({ height_cm: v })}
          min={120}
          max={220}
          required
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
          options={refs.ethnicity.map((e) => ({
            value: e.code,
            label: e.label,
          }))}
          required
        />
        <MultiSelectField
          label="Телосложение"
          value={data.body_type ?? []}
          onChange={(v) => update({ body_type: v })}
          options={refs.body_type.map((b) => ({
            value: b.code,
            label: b.label,
          }))}
          required
        />
        <SelectField
          label="Цвет волос"
          value={data.hair_color ?? null}
          onChange={(v) => update({ hair_color: v })}
          options={refs.hair_colors.map((h) => ({
            value: h.code,
            label: h.label,
          }))}
          required
        />
        <SelectField
          label="Длина волос"
          value={data.hair_length ?? null}
          onChange={(v) => update({ hair_length: v })}
          options={refs.hair_lengths.map((h) => ({
            value: h.code,
            label: h.label,
          }))}
          required
        />
        <SelectField
          label="Цвет глаз"
          value={data.eye_color ?? null}
          onChange={(v) => update({ eye_color: v })}
          options={refs.eye_colors.map((e) => ({
            value: e.code,
            label: e.label,
          }))}
        />
        <MultiSelectField
          label="Особые приметы"
          value={data.marks ?? []}
          onChange={(v) => update({ marks: v })}
          options={refs.marks.map((m) => ({ value: m.code, label: m.label }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">
          Профессиональное
        </h3>
        <SelectField
          label="Опыт"
          value={expValue}
          onChange={expChange}
          options={[
            { value: "yes", label: "Есть" },
            { value: "no", label: "Нет" },
          ]}
        />
        <SelectField
          label="Образование"
          value={data.education ?? null}
          onChange={(v) => update({ education: v })}
          options={refs.education.map((e) => ({
            value: e.code,
            label: e.label,
          }))}
        />
        <SelectField
          label="Налоговый статус"
          value={data.tax_status ?? null}
          onChange={(v) => update({ tax_status: v })}
          options={refs.tax_status.map((t) => ({
            value: t.code,
            label: t.label,
          }))}
        />
        <MultiSelectField
          label="Спорт"
          value={data.skills_sport ?? []}
          onChange={(v) => update({ skills_sport: v })}
          options={refs.skills_sport.map((s) => ({
            value: s.code,
            label: s.label,
          }))}
        />
        <MultiSelectField
          label="Танцы"
          value={data.skills_dance ?? []}
          onChange={(v) => update({ skills_dance: v })}
          options={refs.skills_dance.map((s) => ({
            value: s.code,
            label: s.label,
          }))}
        />
        <MultiSelectField
          label="Вокал"
          value={data.skills_vocal ?? []}
          onChange={(v) => update({ skills_vocal: v })}
          options={refs.skills_vocal.map((s) => ({
            value: s.code,
            label: s.label,
          }))}
        />
        <MultiSelectField
          label="Инструменты"
          value={data.skills_instruments ?? []}
          onChange={(v) => update({ skills_instruments: v })}
          options={refs.skills_instruments.map((s) => ({
            value: s.code,
            label: s.label,
          }))}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">
          Материалы и контакты
        </h3>
        <TextFieldWithAutocomplete
          field="portfolio_url"
          label="Портфолио"
          value={data.portfolio_url ?? ""}
          onChange={(v) => update({ portfolio_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="video_url"
          label="Видеовизитка"
          value={data.video_url ?? ""}
          onChange={(v) => update({ video_url: v })}
          type="url"
        />
        <TextFieldWithAutocomplete
          field="professional_url"
          label="Проф. ресурс (e.g. casting.ru)"
          value={data.professional_url ?? ""}
          onChange={(v) => update({ professional_url: v })}
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
          label="Telegram username"
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

      {error && (
        <div className="rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <button
        onClick={finish}
        disabled={saving}
        className="w-full py-3 rounded-card bg-accent text-white font-medium disabled:opacity-50"
      >
        {saving ? "Сохраняем…" : "Сохранить анкету"}
      </button>
    </div>
  );
}
