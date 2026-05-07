const TELEGRAM_RE = /^@[A-Za-z][A-Za-z0-9_]{4,31}$/;

/**
 * Validate Telegram username. Empty string is OK (field optional).
 * Returns error message in Russian or null if valid.
 */
export function validateTelegramUser(value: string): string | null {
  const v = value.trim();
  if (v === "") return null;
  if (TELEGRAM_RE.test(v)) return null;
  return "Должно начинаться с @, латиница/цифры/_, 5–32 символа. Пример: @ivan_p";
}
