import { useEffect, useState, useRef } from "react";
import { api } from "../api";
import type { Refs } from "../types";
import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { MultiSelectField } from "../fields/MultiSelectField";
import { SelectField } from "../fields/SelectField";

const WORK_TYPES = [
  { value: "helper", label: "Хелпер" },
  { value: "cleaning", label: "Клининг" },
  { value: "loader", label: "Грузчик" },
];

const PHYSICAL_FITNESS = [
  { value: "light", label: "До 5 кг" },
  { value: "medium", label: "5–20 кг" },
  { value: "heavy", label: "20+ кг" },
];

interface Props {
  onDone: () => void;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Data = Record<string, any>;

export function GeneralForm({ onDone }: Props) {
  const [data, setData] = useState<Data>({ work_types: [] });
  const [refs, setRefs] = useState<Refs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    Promise.all([api.getCategoryProfile("general"), api.getRefs()])
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
        api.putCategoryProfile("general", next).catch(() => {});
      }, 400);
      return next;
    });
  };

  const finish = async () => {
    setSaving(true);
    setError(null);
    try {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      await api.putCategoryProfile("general", data);
      await api.completeCategoryProfile("general");
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
      <h2 className="text-xl font-semibold">Анкета — Разнорабочие</h2>

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
          value={data.city ?? ""}
          onChange={(v) => update({ city: v })}
          required
        />
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
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={!!data.ready_for_travel}
            onChange={(e) => update({ ready_for_travel: e.target.checked })}
            className="accent-accent w-4 h-4"
          />
          Готов(а) к командировкам
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
        />
        <SelectField
          label="Физическая подготовка"
          value={data.physical_fitness ?? null}
          onChange={(v) => update({ physical_fitness: v })}
          options={PHYSICAL_FITNESS}
        />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">
          Опыт
        </h3>
        <MultiSelectField
          label="Типы работ"
          value={data.work_types ?? []}
          onChange={(v) => update({ work_types: v })}
          options={WORK_TYPES}
          required
        />
        <SelectField
          label="Опыт работы"
          value={expValue}
          onChange={expChange}
          options={[
            { value: "yes", label: "Есть" },
            { value: "no", label: "Нет" },
          ]}
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
      </section>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">
          Контакты
        </h3>
        <TextFieldWithAutocomplete
          field="phone"
          label="Телефон"
          value={data.phone ?? ""}
          onChange={(v) => update({ phone: v })}
          type="tel"
        />
        <TextFieldWithAutocomplete
          field="telegram_user"
          label="Telegram"
          value={data.telegram_user ?? ""}
          onChange={(v) => update({ telegram_user: v })}
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
