/* Админ-дашборд:
 *  - сверху подборка ключевых чисел;
 *  - блок «Рассылка» с фильтром по аудитории и кнопкой «Подготовить»;
 *  - вкладки «Анкеты» / «Сообщения» для деталей. */
import { useEffect, useState } from "react";
import {
  ChevronLeft,
  Megaphone,
  Send,
  Users,
  CheckCircle2,
  Inbox,
  MessagesSquare,
  Sparkles,
  ListChecks,
} from "lucide-react";
import { api } from "../api";
import { tg } from "../telegram";
import type {
  AdminMessageRow,
  AdminProfileRow,
  AdminStats,
  BroadcastFilter,
  BroadcastFilterBody,
} from "../types";

type Tab = "profiles" | "messages";

const FILTER_OPTIONS: { code: BroadcastFilter; label: string; hint: string }[] = [
  { code: "all", label: "Все пользователи", hint: "Все, кто открывал бота" },
  { code: "creative", label: "Творческие позиции", hint: "Актёры, модели" },
  { code: "event", label: "Event-персонал", hint: "Хостес, промо, аниматоры" },
  { code: "general", label: "Разнорабочие", hint: "Хелперы, клининг, грузчики" },
  { code: "admin", label: "Администрирование", hint: "Операторы, супервайзеры" },
];

export function AdminDashboard({ onBack }: { onBack: () => void }) {
  const [tab, setTab] = useState<Tab>("profiles");

  return (
    <div className="min-h-screen flex flex-col">
      <div className="px-5 pt-5 pb-3 sticky top-0 bg-bg/95 backdrop-blur z-10 border-b border-bg-card">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="text-slate-400 hover:text-white transition"
            aria-label="Назад"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <h1 className="text-lg font-semibold flex-1">Админка</h1>
        </div>
      </div>

      <main className="flex-1 px-5 py-4 space-y-5">
        <StatsBlock />
        <BroadcastBlock />

        <div>
          <div className="flex gap-2 mb-3">
            {(["profiles", "messages"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={
                  "px-3 py-1.5 rounded-chip text-sm border transition " +
                  (tab === t
                    ? "bg-bg-card border-accent text-accent"
                    : "bg-bg-card border-bg-card text-slate-400")
                }
              >
                {t === "profiles" ? "Анкеты" : "Сообщения"}
              </button>
            ))}
          </div>
          {tab === "profiles" && <ProfilesTab />}
          {tab === "messages" && <MessagesTab />}
        </div>
      </main>
    </div>
  );
}

// ===== Stats =====

function StatCard({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  hint?: string;
}) {
  return (
    <div className="rounded-card bg-bg-surface px-4 py-3">
      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-2xl font-semibold tabular-nums mt-1">{value}</div>
      {hint && (
        <div className="text-[11px] text-slate-500 mt-0.5">{hint}</div>
      )}
    </div>
  );
}

function StatsBlock() {
  const [data, setData] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminStats().then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="text-red-400 text-sm">{error}</div>;
  if (!data) return <div className="text-slate-500 text-sm">Загрузка…</div>;

  const subs = data.active_subscriptions_by_category;
  const subsHint = (["creative", "event", "general", "admin"] as const)
    .map((c) => `${c[0].toUpperCase()}${subs[c] ?? 0}`)
    .join(" · ");

  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        icon={<Users className="w-3.5 h-3.5" />}
        label="Пользователей"
        value={data.users_total}
      />
      <StatCard
        icon={<CheckCircle2 className="w-3.5 h-3.5" />}
        label="Завершили анкету"
        value={data.profiles_completed}
        hint={`из ${data.profiles_total} начатых`}
      />
      <StatCard
        icon={<MessagesSquare className="w-3.5 h-3.5" />}
        label="Сообщений из каналов"
        value={data.messages_total}
        hint={`из них кастингов: ${data.messages_casting}`}
      />
      <StatCard
        icon={<Send className="w-3.5 h-3.5" />}
        label="Уведомлений ушло"
        value={data.notifications_success}
        hint={`всего попыток: ${data.notifications_total}`}
      />
      <StatCard
        icon={<Inbox className="w-3.5 h-3.5" />}
        label="В очереди (digest)"
        value={data.pending_notifications_total}
        hint={`в digest-режиме: ${data.users_digest}`}
      />
      <StatCard
        icon={<ListChecks className="w-3.5 h-3.5" />}
        label="Активные подписки"
        value={Object.values(subs).reduce((a, b) => a + b, 0)}
        hint={subsHint}
      />
    </div>
  );
}

// ===== Broadcast =====

function BroadcastBlock() {
  const [filter, setFilter] = useState<BroadcastFilter>("all");
  const [ageMin, setAgeMin] = useState<string>("");
  const [ageMax, setAgeMax] = useState<string>("");
  const [heightMin, setHeightMin] = useState<string>("");
  const [heightMax, setHeightMax] = useState<string>("");
  const [nameQuery, setNameQuery] = useState<string>("");
  const [audience, setAudience] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const buildBody = (): BroadcastFilterBody => {
    const numOrNull = (s: string) => {
      const n = parseInt(s, 10);
      return Number.isFinite(n) ? n : null;
    };
    return {
      filter,
      age_min: numOrNull(ageMin),
      age_max: numOrNull(ageMax),
      height_min: numOrNull(heightMin),
      height_max: numOrNull(heightMax),
      name_query: nameQuery.trim() ? nameQuery.trim() : null,
    };
  };

  // Дебаунсим — пересчитываем аудиторию через 300 мс после ввода.
  useEffect(() => {
    setAudience(null);
    setError(null);
    const handle = setTimeout(() => {
      api
        .adminBroadcastAudience(buildBody())
        .then((r) => setAudience(r.count))
        .catch((e) => setError(String(e)));
    }, 300);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, ageMin, ageMax, heightMin, heightMax, nameQuery]);

  const submit = async () => {
    if (audience === null || audience === 0 || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.adminBroadcastStart(buildBody());
      tg?.close();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setSubmitting(false);
    }
  };

  return (
    <section className="space-y-3">
      <h2 className="text-sm uppercase tracking-wider text-slate-500 inline-flex items-center gap-1.5">
        <Megaphone className="w-4 h-4" />
        Рассылка
      </h2>
      <div className="text-xs text-slate-400 -mt-1">
        Выбери аудиторию — Mini App закроется и в чате с ботом нужно будет
        прислать сообщение для рассылки. Можно текст, фото, видео, гифку
        с премиум-эмодзи.
      </div>

      <div className="space-y-2">
        {FILTER_OPTIONS.map((opt) => (
          <label
            key={opt.code}
            className={`block rounded-card border p-3 cursor-pointer transition ${
              filter === opt.code
                ? "border-accent bg-accent/10"
                : "border-bg-card"
            }`}
          >
            <div className="flex items-center gap-3">
              <input
                type="radio"
                name="broadcast-filter"
                checked={filter === opt.code}
                onChange={() => setFilter(opt.code)}
                className="accent-accent"
              />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm">{opt.label}</div>
                <div className="text-xs text-slate-400 mt-0.5">{opt.hint}</div>
              </div>
            </div>
          </label>
        ))}
      </div>

      <div className="space-y-2 pt-1">
        <div className="text-xs uppercase tracking-wider text-slate-500">
          Дополнительные фильтры
        </div>
        <div className="grid grid-cols-2 gap-2">
          <NumberRange
            label="Возраст"
            from={ageMin}
            to={ageMax}
            onFrom={setAgeMin}
            onTo={setAgeMax}
            placeholderFrom="от"
            placeholderTo="до"
          />
          <NumberRange
            label="Рост, см"
            from={heightMin}
            to={heightMax}
            onFrom={setHeightMin}
            onTo={setHeightMax}
            placeholderFrom="от"
            placeholderTo="до"
          />
        </div>
        <label className="block">
          <span className="text-xs text-slate-400">ФИО содержит</span>
          <input
            type="text"
            value={nameQuery}
            onChange={(e) => setNameQuery(e.target.value)}
            placeholder="Иванов"
            className="mt-1 w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent text-sm"
          />
        </label>
        <div className="text-xs text-slate-500">
          Доп.фильтры применяются к юзерам с заполненной анкетой выбранной
          категории. Рост есть только в Творческих, Event и Разнорабочих —
          для Администрирования он игнорируется.
        </div>
      </div>

      {error && (
        <div className="rounded-card bg-red-950/40 border border-red-900 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <button
        onClick={submit}
        disabled={submitting || audience === null || audience === 0}
        className="w-full rounded-card bg-accent text-bg font-medium py-3 transition disabled:opacity-50 hover:opacity-90 inline-flex items-center justify-center gap-2"
      >
        <Sparkles className="w-4 h-4" />
        {submitting
          ? "Открываем чат с ботом…"
          : audience === 0
            ? "Аудитория пуста"
            : `Подготовить рассылку${audience !== null ? ` (${audience})` : ""}`}
      </button>
    </section>
  );
}

function NumberRange({
  label,
  from,
  to,
  onFrom,
  onTo,
  placeholderFrom,
  placeholderTo,
}: {
  label: string;
  from: string;
  to: string;
  onFrom: (v: string) => void;
  onTo: (v: string) => void;
  placeholderFrom: string;
  placeholderTo: string;
}) {
  const sanitize = (v: string) => v.replace(/[^\d]/g, "");
  return (
    <label className="block">
      <span className="text-xs text-slate-400">{label}</span>
      <div className="mt-1 flex gap-1">
        <input
          type="text"
          inputMode="numeric"
          value={from}
          onChange={(e) => onFrom(sanitize(e.target.value))}
          placeholder={placeholderFrom}
          className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent text-sm tabular-nums"
        />
        <input
          type="text"
          inputMode="numeric"
          value={to}
          onChange={(e) => onTo(sanitize(e.target.value))}
          placeholder={placeholderTo}
          className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent text-sm tabular-nums"
        />
      </div>
    </label>
  );
}

// ===== Profiles =====

function ProfilesTab() {
  const [rows, setRows] = useState<AdminProfileRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminProfiles(50, 0).then(setRows).catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="text-red-400 text-sm">{error}</div>;
  if (!rows) return <div className="text-slate-500 text-sm">Загрузка…</div>;
  if (rows.length === 0) return <div className="text-slate-500 text-sm">Анкет пока нет.</div>;

  return (
    <ul className="space-y-2">
      {rows.map((p) => (
        <li key={p.user_id} className="rounded-card bg-bg-surface p-3 text-sm">
          <div className="flex items-baseline justify-between gap-2">
            <div className="font-medium">
              {p.full_name || <span className="text-slate-500">— без имени —</span>}
            </div>
            <div
              className={
                "text-xs px-2 py-0.5 rounded " +
                (p.completed_at
                  ? "bg-green-900/60 text-green-300"
                  : "bg-slate-800 text-slate-500")
              }
            >
              {p.completed_at ? "завершена" : "draft"}
            </div>
          </div>
          <div className="text-slate-400 text-xs mt-1 space-x-2">
            <span>id: {p.user_id}</span>
            {p.gender && <span>· {p.gender === "male" ? "м" : "ж"}</span>}
            {p.actual_age != null && <span>· {p.actual_age} лет</span>}
            {p.city && <span>· {p.city}</span>}
          </div>
          {(p.project_types.length > 0 || p.role_types.length > 0) && (
            <div className="text-slate-300 text-xs mt-1.5 break-words">
              {p.project_types.length > 0 && <>Проекты: {p.project_types.join(", ")} </>}
              {p.role_types.length > 0 && <>· Роли: {p.role_types.join(", ")}</>}
            </div>
          )}
          {p.email && <div className="text-slate-500 text-xs mt-1">{p.email}</div>}
        </li>
      ))}
    </ul>
  );
}

// ===== Messages =====

function MessagesTab() {
  const [rows, setRows] = useState<AdminMessageRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [castingOnly, setCastingOnly] = useState(false);

  useEffect(() => {
    setRows(null);
    api
      .adminMessages(50, 0, castingOnly)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, [castingOnly]);

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
        <input
          type="checkbox"
          checked={castingOnly}
          onChange={(e) => setCastingOnly(e.target.checked)}
        />
        Только кастинги
      </label>

      {error && <div className="text-red-400 text-sm">{error}</div>}
      {!rows && !error && <div className="text-slate-500 text-sm">Загрузка…</div>}
      {rows && rows.length === 0 && (
        <div className="text-slate-500 text-sm">Нет сообщений.</div>
      )}

      {rows && (
        <ul className="space-y-2">
          {rows.map((m) => (
            <li key={m.id} className="rounded-card bg-bg-surface p-3 text-sm">
              <div className="flex items-baseline justify-between gap-2 text-xs text-slate-400">
                <span>
                  @{m.tg_chat_username ?? "?"} · #{m.tg_message_id}
                </span>
                <span className="tabular-nums">
                  {new Date(m.received_at).toLocaleString("ru-RU")}
                </span>
              </div>
              <div className="mt-1 flex flex-wrap gap-1.5">
                <span
                  className={
                    "text-[10px] px-1.5 py-0.5 rounded " +
                    (m.is_casting
                      ? "bg-green-900/60 text-green-300"
                      : "bg-slate-800 text-slate-500")
                  }
                >
                  {m.is_casting ? "casting" : "non-casting"}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  conf {m.confidence.toFixed(2)}
                </span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  → {m.notified_count} польз.
                </span>
              </div>
              <div className="mt-2 text-slate-200 break-words">
                {m.summary || m.text.slice(0, 200)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
