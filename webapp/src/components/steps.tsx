/* Шесть шагов формы анкеты — один файл, чтобы не плодить мелких. */
import type { Profile, Refs } from "../types";
import {
  ChipGroup,
  CityInput,
  Field,
  NumberInput,
  PairButtons,
  RangeInput,
  Section,
  SelectInput,
  TextInput,
  Toggle,
} from "./ui";

type StepProps = {
  profile: Profile;
  refs: Refs;
  patch: (p: Partial<Profile>) => void;
};

// ===== Step 1: Основная информация =====

export function Step1({ profile, refs, patch }: StepProps) {
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Основная информация</h1>

      <Field label="ФИО" required>
        <TextInput
          value={profile.full_name ?? ""}
          onChange={(e) => patch({ full_name: e.target.value })}
          placeholder="Иван Иванов"
        />
      </Field>

      <Field label="Пол" required>
        <PairButtons
          value={profile.gender ?? null}
          onChange={(v) => patch({ gender: v })}
          options={refs.genders.map((g) => ({ value: g.code as "male" | "female", label: g.label }))}
        />
      </Field>

      <Field label="Город проживания" required>
        <CityInput
          value={profile.city}
          onChange={(v) => patch({ city: v })}
          placeholder="Начните вводить — Москва, Санкт-Петербург…"
        />
      </Field>

      <Toggle
        label="Готов к командировкам"
        checked={profile.ready_for_travel}
        onChange={(v) => patch({ ready_for_travel: v })}
      />

      <Field label="Фактический возраст" required>
        <NumberInput
          value={profile.actual_age}
          onChange={(v) => patch({ actual_age: v })}
          placeholder="24"
          maxLength={3}
        />
      </Field>

      <Field label="Игровой возраст">
        <RangeInput
          min={profile.play_age_min}
          max={profile.play_age_max}
          onChange={({ min, max }) =>
            patch({ play_age_min: min, play_age_max: max })
          }
        />
      </Field>
    </div>
  );
}

// ===== Step 2: Какие кастинги подходят =====

export function Step2({ profile, refs, patch }: StepProps) {
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Какие кастинги вам подходят</h1>

      <Field label="Типы проектов" required hint="можно несколько">
        <ChipGroup
          value={profile.project_types}
          onChange={(v) => patch({ project_types: v })}
          options={refs.project_types}
        />
      </Field>

      <Field label="Типы ролей" required hint="можно несколько">
        <ChipGroup
          value={profile.role_types}
          onChange={(v) => patch({ role_types: v })}
          options={refs.role_types}
        />
      </Field>

      <Field label="Минимальная ставка (₽ / съёмочный день)">
        <NumberInput
          value={profile.min_rate}
          onChange={(v) => patch({ min_rate: v })}
          placeholder="0 — оставьте пустым, чтобы не фильтровать"
          maxLength={7}
        />
      </Field>

      <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
        {[
          ["Массовка", "1 500–3 000 ₽"],
          ["Групповка", "3 000–7 000 ₽"],
          ["Эпизод", "7 000–30 000 ₽"],
          ["Реклама", "25 000–400 000 ₽"],
        ].map(([title, range]) => (
          <div key={title} className="rounded-xl bg-bg-card p-3 text-center">
            <div className="text-slate-300">{title}</div>
            <div className="text-white text-sm font-medium">{range}</div>
          </div>
        ))}
      </div>

      <Toggle
        label="Показывать проекты с оплатой по договорённости"
        checked={profile.show_negotiable}
        onChange={(v) => patch({ show_negotiable: v })}
      />
      <Toggle
        label="Некоммерческие проекты"
        checked={profile.show_noncommercial}
        onChange={(v) => patch({ show_noncommercial: v })}
      />
      <Toggle
        label="Агентские проекты"
        checked={profile.show_agency}
        onChange={(v) => patch({ show_agency: v })}
      />
    </div>
  );
}

// ===== Step 3: Параметры для подбора =====

export function Step3({ profile, refs, patch }: StepProps) {
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Параметры для точного подбора</h1>

      <Field label="Игровой возраст">
        <RangeInput
          min={profile.play_age_min}
          max={profile.play_age_max}
          onChange={({ min, max }) =>
            patch({ play_age_min: min, play_age_max: max })
          }
        />
      </Field>

      <Field label="Рост (см)" required>
        <NumberInput
          value={profile.height_cm}
          onChange={(v) => patch({ height_cm: v })}
          placeholder="175"
          maxLength={3}
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Размер одежды">
          <NumberInput
            value={profile.clothing_size}
            onChange={(v) => patch({ clothing_size: v })}
            placeholder="48"
            maxLength={2}
          />
        </Field>
        <Field label="Размер обуви">
          <NumberInput
            value={profile.shoe_size}
            onChange={(v) => patch({ shoe_size: v })}
            placeholder="42"
            maxLength={2}
          />
        </Field>
      </div>

      <Field label="Этнос" required hint="можно несколько">
        <ChipGroup
          value={profile.ethnicity}
          onChange={(v) => patch({ ethnicity: v })}
          options={refs.ethnicity}
        />
      </Field>

      <Field label="Телосложение" required hint="можно несколько">
        <ChipGroup
          value={profile.body_type}
          onChange={(v) => patch({ body_type: v })}
          options={refs.body_type}
        />
      </Field>

      <Field label="Волосы" required>
        <div className="grid grid-cols-2 gap-3">
          <SelectInput
            value={profile.hair_color}
            onChange={(v) => patch({ hair_color: v })}
            options={refs.hair_colors}
            placeholder="Цвет волос"
          />
          <SelectInput
            value={profile.hair_length}
            onChange={(v) => patch({ hair_length: v })}
            options={refs.hair_lengths}
            placeholder="Длина волос"
          />
        </div>
      </Field>
    </div>
  );
}

// ===== Step 4: Профессиональные параметры =====

export function Step4({ profile, refs, patch }: StepProps) {
  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Профессиональные параметры</h1>

      <Field label="Опыт в съёмках">
        <PairButtons
          value={
            profile.has_experience === null || profile.has_experience === undefined
              ? null
              : profile.has_experience
              ? "yes"
              : "no"
          }
          onChange={(v) => patch({ has_experience: v === "yes" })}
          options={[
            { value: "yes" as const, label: "Да" },
            { value: "no" as const, label: "Пока нет" },
          ]}
        />
      </Field>

      <Field label="Актёрское образование">
        <div className="space-y-2">
          {refs.education.map((opt) => {
            const active = profile.education === opt.code;
            return (
              <button
                key={opt.code}
                type="button"
                onClick={() => patch({ education: active ? null : opt.code })}
                className={
                  "w-full text-left px-4 py-3 rounded-xl border transition " +
                  (active
                    ? "bg-bg-card border-accent text-accent"
                    : "bg-bg-card border-bg-card text-slate-300 hover:border-slate-700")
                }
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </Field>

      <Field label="Налоговый статус" hint="необязательно">
        <ChipGroup
          value={profile.tax_status ? [profile.tax_status] : []}
          onChange={(v) => patch({ tax_status: v[v.length - 1] ?? null })}
          options={refs.tax_status}
        />
      </Field>
    </div>
  );
}

// ===== Step 5: Дополнительные данные =====

export function Step5({ profile, refs, patch }: StepProps) {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Дополнительные данные</h1>
        <p className="text-xs text-slate-400 mt-1">
          Чем больше данных — тем точнее подбор кастингов.
        </p>
      </div>

      <Field label="Цвет глаз">
        <SelectInput
          value={profile.eye_color}
          onChange={(v) => patch({ eye_color: v })}
          options={refs.eye_colors}
          placeholder="Не выбрано"
        />
      </Field>

      <Section title="Приметы" emoji="✨">
        <ChipGroup
          value={profile.marks}
          onChange={(v) => patch({ marks: v })}
          options={refs.marks}
        />
      </Section>

      <Section title="Навыки" emoji="💪">
        <div className="space-y-3">
          <div>
            <div className="text-xs text-slate-400 mb-1.5">💪 Спорт</div>
            <ChipGroup
              value={profile.skills_sport}
              onChange={(v) => patch({ skills_sport: v })}
              options={refs.skills_sport}
            />
          </div>
          <div>
            <div className="text-xs text-slate-400 mb-1.5">💃 Танцы</div>
            <ChipGroup
              value={profile.skills_dance}
              onChange={(v) => patch({ skills_dance: v })}
              options={refs.skills_dance}
            />
          </div>
          <div>
            <div className="text-xs text-slate-400 mb-1.5">🎤 Вокал</div>
            <ChipGroup
              value={profile.skills_vocal}
              onChange={(v) => patch({ skills_vocal: v })}
              options={refs.skills_vocal}
            />
          </div>
          <div>
            <div className="text-xs text-slate-400 mb-1.5">🎸 Муз. инструменты</div>
            <ChipGroup
              value={profile.skills_instruments}
              onChange={(v) => patch({ skills_instruments: v })}
              options={refs.skills_instruments}
            />
          </div>
        </div>
      </Section>
    </div>
  );
}

// ===== Step 6: Материалы и контакты =====

export function Step6({ profile, patch }: StepProps) {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Материалы и контакты</h1>
        <p className="text-xs text-slate-400 mt-1">
          Чем полнее профиль — тем точнее подбор кастингов.
        </p>
      </div>

      <Field label="Ссылка на портфолио">
        <TextInput
          value={profile.portfolio_url ?? ""}
          onChange={(e) => patch({ portfolio_url: e.target.value || null })}
          placeholder="filmtoolz.com/profile или другая ссылка"
        />
      </Field>

      <Field label="Ссылка на видеовизитку">
        <TextInput
          value={profile.video_url ?? ""}
          onChange={(e) => patch({ video_url: e.target.value || null })}
          placeholder="YouTube, Vimeo или другая ссылка"
        />
      </Field>

      <Field label="Ссылка на проф. ресурс">
        <TextInput
          value={profile.professional_url ?? ""}
          onChange={(e) =>
            patch({ professional_url: e.target.value || null })
          }
          placeholder="kinopoisk, imdb и т.д."
        />
      </Field>

      <Field label="Телефон">
        <TextInput
          type="tel"
          value={profile.phone ?? ""}
          onChange={(e) => patch({ phone: e.target.value || null })}
          placeholder="+7 900 123 45 67"
        />
      </Field>

      <Field label="VK">
        <TextInput
          value={profile.vk_url ?? ""}
          onChange={(e) => patch({ vk_url: e.target.value || null })}
          placeholder="vk.com/username"
        />
      </Field>

      <Field label="Email" required>
        <TextInput
          type="email"
          value={profile.email ?? ""}
          onChange={(e) => patch({ email: e.target.value || null })}
          placeholder="email@example.com"
        />
      </Field>
    </div>
  );
}
