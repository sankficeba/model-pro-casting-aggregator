import { AlertCircle } from "lucide-react";
import { useLang } from "../i18n";

/** Плашка вверху экрана: пользователь не открыл чат с ботом, поэтому
 *  Telegram отклоняет наши send_message — нотификации/рассылки до него
 *  не доходят. Просим нажать /start в личном чате с ботом. */
export function BotChatRequiredBanner() {
  const { t } = useLang();
  return (
    <div className="mx-4 mt-3 rounded-card border border-amber-700/60 bg-amber-950/40 text-amber-100 px-3 py-2.5 text-sm flex items-start gap-2">
      <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-amber-300" />
      <div className="space-y-1">
        <div className="font-medium">{t("Бот не сможет вам писать", "The bot won't be able to message you")}</div>
        <div className="text-amber-200/90 text-xs leading-snug">
          {t("Откройте чат с ботом и отправьте сообщение", "Open a chat with the bot and send")}{" "}
          <span className="font-mono bg-amber-900/40 px-1 rounded">/start</span>,
          {t(
            " иначе уведомления о новых вакансиях не будут доходить.",
            " otherwise notifications about new jobs won't reach you.",
          )}
        </div>
      </div>
    </div>
  );
}
