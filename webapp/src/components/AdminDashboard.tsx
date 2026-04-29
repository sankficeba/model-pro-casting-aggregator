/* Простой read-only админ-дашборд:
 * - Статистика
 * - Список последних анкет
 * - Лента сообщений (с галочкой «только кастинги»)
 */
import { useEffect, useState } from "react";
import { api } from "../api";
import type { AdminMessageRow, AdminProfileRow, AdminStats } from "../types";

type Tab = "stats" | "profiles" | "messages";

export function AdminDashboard({ onBack }: { onBack: () => void }) {
  const [tab, setTab] = useState<Tab>("stats");

  return (
    <div className="min-h-screen flex flex-col">
      <div className="px-5 pt-5 pb-3 sticky top-0 bg-bg z-10 border-b border-bg-card">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="text-slate-400 hover:text-white transition"
            aria-label="Выйти"
          >
            ←
          </button>
          <h1 className="text-lg font-semibold flex-1">Админка</h1>
        </div>
        <div className="flex gap-2 mt-3">
          {(["stats", "profiles", "messages"] as const).map((t) => (
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
              {t === "stats" && "Статистика"}
              {t === "profiles" && "Анкеты"}
              {t === "messages" && "Сообщения"}
            </button>
          ))}
        </div>
      </div>

      <main className="flex-1 px-5 py-4 space-y-4">
        {tab === "stats" && <StatsTab />}
        {tab === "profiles" && <ProfilesTab />}
        {tab === "messages" && <MessagesTab />}
      </main>
    </div>
  );
}

// ===== Stats =====

function StatsTab() {
  const [data, setData] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.adminStats().then(setData).catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="text-red-400 text-sm">{error}</div>;
  if (!data) return <div className="text-slate-500 text-sm">Загрузка…</div>;

  const items: [string, number][] = [
    ["Всего анкет", data.profiles_total],
    ["Завершённых", data.profiles_completed],
    ["Сообщений в канале", data.messages_total],
    ["Из них кастинги", data.messages_casting],
    ["Уведомлений отправлено", data.notifications_total],
    ["…успешных", data.notifications_success],
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {items.map(([label, val]) => (
        <div key={label} className="rounded-card bg-bg-surface px-4 py-3">
          <div className="text-xs text-slate-400">{label}</div>
          <div className="text-2xl font-semibold tabular-nums mt-1">{val}</div>
        </div>
      ))}
    </div>
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
              {(m.gender ||
                m.age_min != null ||
                m.project_types.length > 0 ||
                m.role_types.length > 0 ||
                m.city ||
                m.rate != null) && (
                <div className="text-slate-400 text-xs mt-1.5 space-x-2 break-words">
                  {m.gender && <span>{m.gender === "male" ? "м" : "ж"}</span>}
                  {m.age_min != null && (
                    <span>
                      · {m.age_min}
                      {m.age_max !== m.age_min ? `–${m.age_max}` : ""} лет
                    </span>
                  )}
                  {m.city && <span>· {m.city}</span>}
                  {m.rate != null && <span>· {m.rate.toLocaleString("ru-RU")} ₽</span>}
                  {m.project_types.length > 0 && (
                    <span>· проекты: {m.project_types.join(",")}</span>
                  )}
                  {m.role_types.length > 0 && (
                    <span>· роли: {m.role_types.join(",")}</span>
                  )}
                </div>
              )}
              {m.vacancies.length > 0 && (
                <div className="mt-2 space-y-1">
                  <div className="text-xs text-slate-500">
                    Вакансии ({m.vacancies.length}):
                  </div>
                  <ul className="space-y-1">
                    {m.vacancies.map((v) => (
                      <li
                        key={v.id}
                        className="text-xs text-slate-300 bg-bg-card rounded px-2 py-1"
                      >
                        <span className="font-medium">
                          {v.role_label ?? v.role_types[0] ?? "Роль"}
                        </span>
                        {v.gender && <> · {v.gender === "male" ? "м" : "ж"}</>}
                        {v.age_min != null && (
                          <>
                            {" "}
                            · {v.age_min}
                            {v.age_max !== v.age_min ? `–${v.age_max}` : ""} лет
                          </>
                        )}
                        {v.rate != null && (
                          <> · {v.rate.toLocaleString("ru-RU")} ₽</>
                        )}
                        {v.role_types.length > 0 && (
                          <> · {v.role_types.join(",")}</>
                        )}
                        {v.description && (
                          <div className="text-slate-400 mt-0.5 break-words">
                            {v.description}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
