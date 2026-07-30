import { getInitData } from "./telegram";
import type {
  AdminMessageRow,
  AdminProfileRow,
  AdminStats,
  BroadcastAudience,
  BroadcastFilterBody,
  BroadcastStartResponse,
  CategoryCode,
  DeliverySettings,
  DigestClearResponse,
  DigestStartResponse,
  FavoriteShowResponse,
  FavoritesList,
  FavoritesSettings,
  ProblemActionResponse,
  ProblemsList,
  MeResponse,
  SubscriptionCheckout,
  SubscriptionStatus,
  Profile,
  Refs,
  Subscription,
} from "./types";

const BASE = "/api";

// ===== Текущий язык интерфейса, синхронизируется из i18n.tsx =====
// api.ts — обычный модуль (не React), поэтому язык хранится тут в
// переменной, а не в контексте. LangProvider вызывает setApiLang()
// синхронно при загрузке модуля и при каждом переключении.
type ApiLang = "ru" | "en";
let currentLang: ApiLang = "ru";
export function setApiLang(lang: ApiLang): void {
  currentLang = lang;
}

// ===== Перевод ошибок API в короткие сообщения =====

const FIELD_LABELS: Record<string, [string, string]> = {
  full_name: ["ФИО", "Full name"],
  gender: ["Пол", "Gender"],
  city: ["Город", "City"],
  ready_for_travel: ["Командировки", "Travel"],
  actual_age: ["Возраст", "Age"],
  play_age_min: ["Игровой возраст (от)", "Playing age (from)"],
  play_age_max: ["Игровой возраст (до)", "Playing age (to)"],
  project_types: ["Типы проектов", "Project types"],
  role_types: ["Типы ролей", "Role types"],
  min_rate: ["Минимальная ставка", "Minimum rate"],
  height_cm: ["Рост", "Height"],
  clothing_size: ["Размер одежды", "Clothing size"],
  shoe_size: ["Размер обуви", "Shoe size"],
  ethnicity: ["Этнос", "Ethnicity"],
  body_type: ["Телосложение", "Body type"],
  hair_color: ["Цвет волос", "Hair color"],
  hair_length: ["Длина волос", "Hair length"],
  has_experience: ["Опыт", "Experience"],
  education: ["Образование", "Education"],
  tax_status: ["Налоговый статус", "Tax status"],
  eye_color: ["Цвет глаз", "Eye color"],
  marks: ["Приметы", "Distinguishing marks"],
  skills_sport: ["Спорт", "Sport"],
  skills_dance: ["Танцы", "Dance"],
  skills_vocal: ["Вокал", "Vocal"],
  skills_instruments: ["Инструменты", "Instruments"],
  portfolio_url: ["Портфолио", "Portfolio"],
  video_url: ["Видеовизитка", "Video reel"],
  professional_url: ["Проф. ресурс", "Professional profile"],
  phone: ["Телефон", "Phone"],
  vk_url: ["VK", "VK"],
  email: ["Email", "Email"],
};

function fieldLabel(fieldKey: string | number | undefined): string {
  if (typeof fieldKey !== "string") return currentLang === "en" ? "Field" : "Поле";
  const pair = FIELD_LABELS[fieldKey];
  if (!pair) return fieldKey;
  return currentLang === "en" ? pair[1] : pair[0];
}

interface PydanticError {
  type: string;
  loc: (string | number)[];
  msg: string;
  ctx?: Record<string, unknown>;
}

function humanizeOne(err: PydanticError): string {
  const fieldKey = err.loc.filter((x) => x !== "body").pop();
  const label = fieldLabel(fieldKey);
  const ctx = err.ctx ?? {};
  const en = currentLang === "en";

  switch (err.type) {
    case "greater_than_equal":
      return en ? `${label}: minimum ${ctx.ge}` : `${label}: минимум ${ctx.ge}`;
    case "less_than_equal":
      return en ? `${label}: maximum ${ctx.le}` : `${label}: максимум ${ctx.le}`;
    case "greater_than":
      return en ? `${label}: greater than ${ctx.gt}` : `${label}: больше ${ctx.gt}`;
    case "less_than":
      return en ? `${label}: less than ${ctx.lt}` : `${label}: меньше ${ctx.lt}`;
    case "string_too_long":
      return en ? `${label}: value too long` : `${label}: слишком длинное значение`;
    case "string_too_short":
      return en ? `${label}: value too short` : `${label}: слишком короткое значение`;
    case "missing":
      return en ? `${label}: required field` : `${label}: обязательное поле`;
    case "int_parsing":
    case "int_type":
    case "float_parsing":
      return en ? `${label}: must be a number` : `${label}: должно быть числом`;
    case "value_error":
      // Pydantic email-валидация и кастомные validator'ы
      if (fieldKey === "email") return en ? "Invalid email" : "Некорректный email";
      return en ? `${label}: invalid value` : `${label}: некорректное значение`;
    case "literal_error":
    case "enum":
      return en ? `${label}: invalid value` : `${label}: недопустимое значение`;
    case "url_parsing":
    case "url_type":
      return en ? `${label}: invalid link format` : `${label}: неверный формат ссылки`;
    default:
      return en ? `${label}: ${err.msg || "error"}` : `${label}: ${err.msg || "ошибка"}`;
  }
}

function humanizeApiError(status: number, body: string): string {
  const en = currentLang === "en";
  if (status === 401) {
    return en
      ? "Telegram session expired — close the Mini App and reopen it."
      : "Сессия Telegram устарела — закройте Mini App и откройте заново.";
  }
  if (status >= 500) {
    return en
      ? "The server is temporarily unavailable. Please try again in a minute."
      : "Сервер временно недоступен. Попробуйте через минуту.";
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
  return body?.trim() ? body : (en ? `Error ${status}` : `Ошибка ${status}`);
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
  getRefs: () => request<Refs>(`/refs?lang=${currentLang}`),
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

  // Delivery settings
  getDeliverySettings: () =>
    request<DeliverySettings>("/delivery-settings"),
  putDeliverySettings: (settings: DeliverySettings) =>
    request<DeliverySettings>("/delivery-settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),
  startDigestReview: () =>
    request<DigestStartResponse>("/digest/start", {
      method: "POST",
      body: "{}",
    }),
  clearDigestQueue: () =>
    request<DigestClearResponse>("/digest/clear", {
      method: "POST",
      body: "{}",
    }),

  // Subscription
  getSubscriptionStatus: () =>
    request<SubscriptionStatus>("/subscription/status"),
  createSubscriptionCheckout: (planCode?: string) =>
    request<SubscriptionCheckout>("/subscription/checkout", {
      method: "POST",
      body: JSON.stringify({ plan_code: planCode ?? null }),
    }),

  // Favorites
  listFavorites: () => request<FavoritesList>("/favorites"),
  getFavoritesSettings: () =>
    request<FavoritesSettings>("/favorites/settings"),
  putFavoritesSettings: (settings: FavoritesSettings) =>
    request<FavoritesSettings>("/favorites/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    }),
  reportPerf: (event: string, total_ms: number, parts: Record<string, number>) =>
    request<{ ok: boolean }>("/perf", {
      method: "POST",
      body: JSON.stringify({
        event,
        total_ms: Math.round(total_ms),
        parts: Object.fromEntries(
          Object.entries(parts).map(([k, v]) => [k, Math.round(v)]),
        ),
        user_agent: navigator.userAgent.slice(0, 200),
      }),
    }).catch(() => ({ ok: false })),
  removeFavorite: (messageId: number) =>
    request<{ ok: boolean }>(`/favorites/${messageId}`, { method: "DELETE" }),
  showFavoriteInChat: (messageId: number) =>
    request<FavoriteShowResponse>(`/favorites/${messageId}/show-in-chat`, {
      method: "POST",
      body: "{}",
    }),

  // Problems
  reportProblem: (text: string) =>
    request<ProblemActionResponse>("/problems", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  listProblems: () => request<ProblemsList>("/problems"),
  resolveProblem: (problemId: number) =>
    request<ProblemActionResponse>(`/problems/${problemId}/resolve`, {
      method: "POST",
      body: "{}",
    }),
  showProblemInChat: (problemId: number) =>
    request<ProblemActionResponse>(`/problems/${problemId}/show-in-chat`, {
      method: "POST",
      body: "{}",
    }),

  // Admin
  adminStats: () => request<AdminStats>("/admin/stats"),
  adminProfiles: (limit = 50, offset = 0) =>
    request<AdminProfileRow[]>(`/admin/profiles?limit=${limit}&offset=${offset}`),
  adminMessages: (limit = 50, offset = 0, castingOnly = false) =>
    request<AdminMessageRow[]>(
      `/admin/messages?limit=${limit}&offset=${offset}&casting_only=${castingOnly}`,
    ),
  adminBroadcastAudience: (body: BroadcastFilterBody) =>
    request<BroadcastAudience>("/admin/broadcast/audience", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  adminBroadcastStart: (body: BroadcastFilterBody) =>
    request<BroadcastStartResponse>("/admin/broadcast/start", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
