// Тонкая обёртка над window.Telegram.WebApp.
// Если открыли страницу не из Telegram — возвращаем заглушки, чтобы можно было
// разрабатывать локально в обычном браузере.

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: { id: number; username?: string } };
  version?: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  // Bot API 8.0+ (опц.). Полноэкранный режим — без полупрозрачного шита.
  requestFullscreen?: () => void;
  // Bot API 7.7+ (опц.). Запрещает свайп вниз закрывать форму, удобно при заполнении.
  disableVerticalSwipes?: () => void;
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

// Eager init на загрузке модуля — Telegram script в index.html уже отработал
// к моменту когда наш bundle грузится. Это раньше чем React.useEffect, что
// исключает окно когда юзер может свайпнуть и свернуть приложение.
if (tg) {
  try { tg.ready(); } catch { /* noop */ }
  applyTelegramChrome();
}

export function initTelegram(): void {
  if (!tg) return;
  tg.ready();
  applyTelegramChrome();
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
