// Тонкая обёртка над window.Telegram.WebApp.
// Если открыли страницу не из Telegram — возвращаем заглушки, чтобы можно было
// разрабатывать локально в обычном браузере.

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: { id: number; username?: string } };
  ready: () => void;
  expand: () => void;
  close: () => void;
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

export function initTelegram(): void {
  if (!tg) return;
  tg.ready();
  tg.expand();
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
