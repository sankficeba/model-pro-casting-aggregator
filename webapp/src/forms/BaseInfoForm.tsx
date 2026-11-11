import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Refs } from "../types";
import { TextFieldWithAutocomplete } from "../fields/TextFieldWithAutocomplete";
import { NumberFieldWithAutocomplete } from "../fields/NumberFieldWithAutocomplete";
import { SelectField } from "../fields/SelectField";
import { CITIES } from "../cities";
import { validateTelegramUser } from "../fields/telegramValidation";
import { BASE_FIELDS, type Data } from "../hooks/useCategoryFormState";
import { CategoryFormShell } from "../components/CategoryFormShell";
import { useSuggestionsRefresh } from "../contexts/SuggestionsContext";
import { useLang } from "../i18n";
import { getTelegramUsername } from "../telegram";

interface Props {
  onDone: () => void;
}

const TOTAL_REQUIRED = 7;

function validate(data: Data, t: (ru: string, en: string) => string): string[] {
  const missing: string[] = [];
  if (!data.full_name?.trim()) missing.push(t("ФИО", "Full name"));
  if (!data.gender) missing.push(t("Пол", "Gender"));
  if (data.actual_age == null) missing.push(t("Возраст", "Age"));
  if (!data.city?.trim()) missing.push(t("Город", "City"));
  if (!data.phone?.trim()) missing.push(t("Телефон", "Phone"));
  if (!data.telegram_user?.trim()) missing.push(t("Telegram", "Telegram"));
  else if (validateTelegramUser(data.telegram_user.trim(), t) !== null) {
    missing.push(t("Telegram (исправь формат)", "Telegram (fix format)"));
  }
  if (!data.email?.trim()) missing.push(t("Email", "Email"));
  return missing;
}

function pickBase(data: Data): Data {
  const out: Data = {};
  for (const f of BASE_FIELDS) if (f in data) out[f] = data[f];
  return out;
}

/** «Основная информация»: общие поля, которые сервер раскладывает во все
 * анкеты юзера. Автосейв с дебаунсом, как в формах категорий. */
export function BaseInfoForm({ onDone }: Props) {
  const { t } = useLang();
  const [data, setData] = useState<Data>({});
  const [refs, setRefs] = useState<Refs | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dataRef = useRef<Data>({});
  const refreshSuggestions = useSuggestionsRefresh();

  useEffect(() => {
    refreshSuggestions();
  }, [refreshSuggestions]);

  useEffect(() => {
    Promise.all([api.getBaseProfile(), api.getRefs()])
      .then(([b, r]) => {
        const loaded = pickBase(b as Data);
        // Telegram обязателен: если пусто — подставляем @username из Telegram
        // и сразу сохраняем (юзер может поправить).
        const tgUser = getTelegramUsername();
        if (!loaded.telegram_user?.trim() && tgUser) {
          loaded.telegram_user = tgUser;
          api.putBaseProfile(loaded).catch(() => {});
        }
        dataRef.current = loaded;
        setData(loaded);
        setRefs(r);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
    return () => {
      // Ушли с экрана до срабатывания автосейва — досохраняем, а не теряем.
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
        api.putBaseProfile(dataRef.current).catch(() => {});
      }
    };
  }, []);

  const update = (patch: Data) => {
    setData((prev) => {
      const next = { ...prev, ...patch };
      dataRef.current = next;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        debounceRef.current = null;
        api.putBaseProfile(next).catch(() => {});
      }, 400);
      return next;
    });
  };

  const finish = async () => {
    const missing = validate(data, t);
    if (missing.length > 0) {
      setError(t("Заполни обязательные поля: ", "Fill in the required fields: ") + missing.join(", "));
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = null;
      await api.putBaseProfile(data);
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  if (loading || !refs) return <div className="p-6 text-slate-400">{t("Загрузка…", "Loading…")}</div>;

  const progressPct = Math.round(((TOTAL_REQUIRED - validate(data, t).length) / TOTAL_REQUIRED) * 100);

  return (
    <CategoryFormShell
      title={t("Основная информация", "Basic information")}
      error={error}
      saving={saving}
      onSubmit={finish}
      progressPct={progressPct}
    >
      <p className="text-sm text-slate-400 -mt-3">
        {t(
          "Эти данные общие для всех направлений — заполняются один раз.",
          "This information is shared by all categories — you fill it in once.",
        )}
      </p>

      <section className="space-y-3">
        <h3 className="text-sm uppercase tracking-wider text-slate-500">{t("О себе", "About you")}</h3>
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
        <NumberFieldWithAutocomplete
          field="actual_age"
          label={t("Возраст", "Age")}
          value={data.actual_age ?? null}
          onChange={(v) => update({ actual_age: v })}
          min={14}
          max={80}
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
          required
        />
        <TextFieldWithAutocomplete
          field="vk_url"
          label={t("VK", "VK")}
          value={data.vk_url ?? ""}
          onChange={(v) => update({ vk_url: v })}
          placeholder="vk.com/username"
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
