import { AlertCircle } from "lucide-react";

/** Плашка вверху экрана: пользователь не открыл чат с ботом, поэтому
 *  Telegram отклоняет наши send_message — нотификации/рассылки до него
 *  не доходят. Просим нажать /start в личном чате с ботом. */
export function BotChatRequiredBanner() {
  return (
    <div className="mx-4 mt-3 rounded-card border border-amber-700/60 bg-amber-950/40 text-amber-100 px-3 py-2.5 text-sm flex items-start gap-2">
      <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-amber-300" />
      <div className="space-y-1">
        <div className="font-medium">Бот не сможет вам писать</div>
        <div className="text-amber-200/90 text-xs leading-snug">
          Откройте чат с ботом и отправьте сообщение{" "}
          <span className="font-mono bg-amber-900/40 px-1 rounded">/start</span>,
          иначе уведомления о новых вакансиях не будут доходить.
        </div>
      </div>
    </div>
  );
}
