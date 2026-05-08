import { getInitData } from "./telegram";
import type {
  AdminMessageRow,
  AdminProfileRow,
  AdminStats,
  CategoryCode,
  MeResponse,
  Profile,
  Refs,
  Subscription,
} from "./types";

const BASE = "/api";

// ===== Перевод ошибок API в короткие русские сообщения =====

const FIELD_LABELS: Record<string, string> = {
  full_name: "ФИО",
  gender: "Пол",
  city: "Город",
  ready_for_travel: "Командировки",
  actual_age: "Возраст",
  play_age_min: "Игровой возраст (от)",
  play_age_max: "Игровой возраст (до)",
  project_types: "Типы проектов",
  role_types: "Типы ролей",
  min_rate: "Минимальная ставка",
  height_cm: "Рост",
  clothing_size: "Размер одежды",
  shoe_size: "Размер обуви",
  ethnicity: "Этнос",
  body_type: "Телосложение",
  hair_color: "Цвет волос",
  hair_length: "Длина волос",
  has_experience: "Опыт",
  education: "Образование",
  tax_status: "Налоговый статус",
  eye_color: "Цвет глаз",
  marks: "Приметы",
  skills_sport: "Спорт",
  skills_dance: "Танцы",
  skills_vocal: "Вокал",
  skills_instruments: "Инструменты",
  portfolio_url: "Портфолио",
  video_url: "Видеовизитка",
  professional_url: "Проф. ресурс",
  phone: "Телефон",
  vk_url: "VK",
  email: "Email",
};

interface PydanticError {
  type: string;
  loc: (string | number)[];
  msg: string;
  ctx?: Record<string, unknown>;
}

function humanizeOne(err: PydanticError): string {
  const fieldKey = err.loc.filter((x) => x !== "body").pop();
  const label =
    typeof fieldKey === "string" ? FIELD_LABELS[fieldKey] ?? fieldKey : "Поле";
  const ctx = err.ctx ?? {};

  switch (err.type) {
    case "greater_than_equal":
      return `${label}: минимум ${ctx.ge}`;
    case "less_than_equal":
      return `${label}: максимум ${ctx.le}`;
    case "greater_than":
      return `${label}: больше ${ctx.gt}`;
    case "less_than":
      return `${label}: меньше ${ctx.lt}`;
    case "string_too_long":
      return `${label}: слишком длинное значение`;
    case "string_too_short":
      return `${label}: слишком короткое значение`;
    case "missing":
      return `${label}: обязательное поле`;
    case "int_parsing":
    case "int_type":
    case "float_parsing":
      return `${label}: должно быть числом`;
    case "value_error":
      // Pydantic email-валидация и кастомные validator'ы
      if (fieldKey === "email") return "Некорректный email";
      return `${label}: некорректное значение`;
    case "literal_error":
    case "enum":
      return `${label}: недопустимое значение`;
    case "url_parsing":
    case "url_type":
      return `${label}: неверный формат ссылки`;
    default:
      return `${label}: ${err.msg || "ошибка"}`;
  }
}

function humanizeApiError(status: number, body: string): string {
  if (status === 401) {
    return "Сессия Telegram устарела — закройте Mini App и откройте заново.";
  }
  if (status >= 500) {
    return "Сервер временно недоступен. Попробуйте через минуту.";
  }
  // Pydantic 422 / FastAPI validation
  try {
    const obj = JSON.parse(body) as { detail?: unknown };
    if (Array.isArray(obj.detail)) {
      const msgs = (obj.detail as PydanticError[])
        .map(humanizeOne)
        .filter(Boolean);
      if (msgs.length) return msgs.join("; ");
    }
    if (typeof obj.detail === "string") return obj.detail;
  } catch {
    /* not JSON */
  }
  return body?.trim() ? body : `Ошибка ${status}`;
}

// ===== HTTP =====

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Telegram-Init-Data": getInitData(),
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(humanizeApiError(res.status, text));
  }
  return (await res.json()) as T;
}

export const api = {
  getMe: () => request<MeResponse>("/me"),
  getRefs: () => request<Refs>("/refs"),
  getProfile: () => request<Profile>("/profile"),
  updateProfile: (data: Profile) =>
    request<Profile>("/profile", { method: "PUT", body: JSON.stringify(data) }),
  completeProfile: () =>
    request<Profile>("/profile/complete", { method: "POST" }),

  // Per-category profile + subscriptions
  getCategoryProfile: <T = Record<string, unknown>>(category: CategoryCode) =>
    request<T>(`/profile/${category}`),
  putCategoryProfile: <T = Record<string, unknown>>(
    category: CategoryCode,
    data: unknown,
  ) =>
    request<T>(`/profile/${category}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  completeCategoryProfile: <T = Record<string, unknown>>(category: CategoryCode) =>
    request<T>(`/profile/${category}/complete`, {
      method: "POST",
      body: "{}",
    }),
  createSubscriptions: (categories: CategoryCode[]) =>
    request<{ subscriptions: Subscription[] }>("/subscriptions", {
      method: "POST",
      body: JSON.stringify({ categories }),
    }),
  patchSubscription: (category: CategoryCode, enabled: boolean) =>
    request<{ ok: boolean }>(`/subscriptions/${category}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  getSuggestions: () =>
    request<{ suggestions: Record<string, unknown[]> }>("/profile/suggestions"),

  // Blacklist
  getBlacklist: () => request<{ words: string[] }>("/blacklist"),
  putBlacklist: (words: string[]) =>
    request<{ words: string[] }>("/blacklist", {
      method: "PUT",
      body: JSON.stringify({ words }),
    }),

  // Channel suggestion
  suggestChannel: (ref: string, comment?: string) =>
    request<{ ok: boolean; notified_admins: number }>("/channel-suggestion", {
      method: "POST",
      body: JSON.stringify({ ref, comment: comment || null }),
    }),

  // Admin
  adminStats: () => request<AdminStats>("/admin/stats"),
  adminProfiles: (limit = 50, offset = 0) =>
    request<AdminProfileRow[]>(`/admin/profiles?limit=${limit}&offset=${offset}`),
  adminMessages: (limit = 50, offset = 0, castingOnly = false) =>
    request<AdminMessageRow[]>(
      `/admin/messages?limit=${limit}&offset=${offset}&casting_only=${castingOnly}`,
    ),
};
