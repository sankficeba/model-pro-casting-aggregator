// Тонкая обёртка над window.Telegram.WebApp.
// Если открыли страницу не из Telegram — возвращаем заглушки, чтобы можно было
// разрабатывать локально в обычном браузере.

interface SafeAreaInset {
  top?: number;
  right?: number;
  bottom?: number;
  left?: number;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: { id: number; username?: string } };
  version?: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  // Bot API 6.1+ — открывает Telegram-ссылку (t.me/...) внутри клиента
  // БЕЗ закрытия Mini App.
  openTelegramLink?: (url: string) => void;
  // Bot API 6.1+ — открывает внешнюю ссылку. Mini App не закрывается.
  openLink?: (url: string, options?: { try_instant_view?: boolean }) => void;
  // Bot API 8.0+ (опц.). Полноэкранный режим — без полупрозрачного шита.
  requestFullscreen?: () => void;
  // Bot API 7.7+ (опц.). Запрещает свайп вниз закрывать форму, удобно при заполнении.
  disableVerticalSwipes?: () => void;
  // Bot API 8.0+ (опц.). Системные insets (статус-бар, нижний бар).
  safeAreaInset?: SafeAreaInset;
  // Bot API 8.0+ (опц.). Inset под чрезз кнопки самого Telegram (Close / menu) в fullscreen.
  contentSafeAreaInset?: SafeAreaInset;
  // Bot API 6.1+ event subscription. На старых клиентах undefined.
  onEvent?: (event: string, handler: () => void) => void;
  offEvent?: (event: string, handler: () => void) => void;
  colorScheme: "light" | "dark";
  MainButton: {
    text: string;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
    setText: (text: string) => void;
    showProgress: (leaveActive?: boolean) => void;
    hideProgress: () => void;
  };
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy") => void;
    notificationOccurred: (type: "error" | "success" | "warning") => void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

export const tg = window.Telegram?.WebApp;

/** Применить fullscreen / disable-swipe настройки. Идемпотентно — можно
 * звать сколько угодно раз. */
function applyTelegramChrome(): void {
  if (!tg) return;
  try { tg.expand(); } catch { /* noop */ }
  // Bot API 8.0+: настоящий полный экран на мобильном (поверх системной шторки).
  try { tg.requestFullscreen?.(); } catch { /* старый клиент */ }
  // Bot API 7.7+: запрещает закрытие свайпом вниз во время заполнения формы.
  try { tg.disableVerticalSwipes?.(); } catch { /* старый клиент */ }
}

/** Прокинуть Telegram safe-area insets в CSS-переменные на :root. CSS
 * подхватит их и применит padding к #root (см. index.css). Так контент
 * не уходит под статус-бар и под кнопки Telegram (Close/expand/menu) в
 * fullscreen-режиме. */
function applySafeAreaVars(): void {
  if (!tg) return;
  const safe = tg.safeAreaInset ?? {};
  const content = tg.contentSafeAreaInset ?? {};
  const root = document.documentElement;
  // Системный inset + дополнительный contentInset (под Telegram chrome).
  root.style.setProperty("--tg-safe-top", `${(safe.top ?? 0) + (content.top ?? 0)}px`);
  root.style.setProperty("--tg-safe-bottom", `${(safe.bottom ?? 0) + (content.bottom ?? 0)}px`);
  root.style.setProperty("--tg-safe-left", `${(safe.left ?? 0) + (content.left ?? 0)}px`);
  root.style.setProperty("--tg-safe-right", `${(safe.right ?? 0) + (content.right ?? 0)}px`);
}

// Eager init на загрузке модуля — Telegram script в index.html уже отработал
// к моменту когда наш bundle грузится. Это раньше чем React.useEffect, что
// исключает окно когда юзер может свайпнуть и свернуть приложение.
if (tg) {
  try { tg.ready(); } catch { /* noop */ }
  applyTelegramChrome();
  applySafeAreaVars();
  // Подписки на изменения insets (поворот экрана, переключение fullscreen).
  // Игнорим если onEvent отсутствует у старого клиента.
  try { tg.onEvent?.("safeAreaChanged", applySafeAreaVars); } catch { /* noop */ }
  try { tg.onEvent?.("contentSafeAreaChanged", applySafeAreaVars); } catch { /* noop */ }
  try { tg.onEvent?.("fullscreenChanged", applySafeAreaVars); } catch { /* noop */ }
  try { tg.onEvent?.("viewportChanged", applySafeAreaVars); } catch { /* noop */ }
}

export function initTelegram(): void {
  if (!tg) return;
  tg.ready();
  applyTelegramChrome();
  applySafeAreaVars();
}

export function getInitData(): string {
  // В Telegram — реальный initData. Иначе пустая строка (бэкенд вернёт 401,
  // но во фронте можно показать дев-баннер).
  return tg?.initData ?? "";
}

export function isInTelegram(): boolean {
  return Boolean(tg?.initData);
}

export function haptic(type: "light" | "medium" | "heavy" = "light") {
  tg?.HapticFeedback?.impactOccurred(type);
}

export function notify(type: "error" | "success" | "warning") {
  tg?.HapticFeedback?.notificationOccurred(type);
}

export function closeApp() {
  tg?.close();
}

/** Открыть Telegram-ссылку (t.me/...) НЕ закрывая Mini App.
 *  Вне Telegram — обычный window.open. */
export function openTelegramLink(url: string): void {
  if (tg?.openTelegramLink) {
    try {
      tg.openTelegramLink(url);
      return;
    } catch {
      /* fallback */
    }
  }
  window.open(url, "_blank", "noopener,noreferrer");
}
