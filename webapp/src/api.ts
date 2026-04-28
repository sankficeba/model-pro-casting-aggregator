import { getInitData } from "./telegram";
import type { Profile, Refs } from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Telegram-Init-Data": getInitData(),
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  getRefs: () => request<Refs>("/refs"),
  getProfile: () => request<Profile>("/profile"),
  updateProfile: (data: Profile) =>
    request<Profile>("/profile", { method: "PUT", body: JSON.stringify(data) }),
};
