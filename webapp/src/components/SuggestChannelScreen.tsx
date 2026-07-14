import { useState } from "react";
import { ChevronLeft, Send } from "lucide-react";
import { api } from "../api";
import { useLang } from "../i18n";

interface Props {
  onBack: () => void;
}

export function SuggestChannelScreen({ onBack }: Props) {
  const { t } = useLang();
  const [ref, setRef] = useState("");
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const submit = async () => {
    const trimmed = ref.trim();
    if (!trimmed) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.suggestChannel(trimmed, comment.trim() || undefined);
      setSuccess(true);
      setRef("");
      setComment("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen pb-5">
      <div className="sticky top-0 z-20 bg-bg/90 backdrop-blur border-b border-bg-card">
        <button
          onClick={onBack}
          className="flex items-center gap-1 px-4 py-3 text-slate-400 hover:text-white transition"
        >
          <ChevronLeft className="w-5 h-5" />
          {t("Назад", "Back")}
        </button>
      </div>

      <div className="p-5 space-y-4">
        <h1 className="text-2xl font-semibold">{t("Предложить канал", "Suggest a channel")}</h1>
        <p className="text-sm text-slate-400">
          {t(
            "Знаешь канал с кастингами/вакансиями, которого ещё нет в нашем списке? Отправь ссылку — мы рассмотрим.",
            "Know a castings/jobs channel that's not on our list yet? Send the link — we'll take a look.",
          )}
        </p>

        <label className="block space-y-1">
          <span className="text-sm text-slate-400">
            {t("Ссылка или @username", "Link or @username")}
            <span className="text-red-400 ml-0.5">*</span>
          </span>
          <input
            type="text"
            value={ref}
            onChange={(e) => setRef(e.target.value)}
            placeholder={t("@my_channel или https://t.me/my_channel", "@my_channel or https://t.me/my_channel")}
            className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm text-slate-400">{t("Комментарий (необязательно)", "Comment (optional)")}</span>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={t("Например: «здесь много event-кастингов»", 'E.g.: "lots of event castings here"')}
            rows={3}
            maxLength={500}
            className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent resize-none"
          />
        </label>

        {error && (
          <div className="rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {success && (
          <div className="rounded-card bg-emerald-950/40 border border-emerald-900 px-4 py-3 text-sm text-emerald-300">
            {t("Спасибо! Предложение отправлено админу.", "Thanks! Your suggestion has been sent to the admin.")}
          </div>
        )}

        <button
          onClick={submit}
          disabled={!ref.trim() || submitting}
          className="w-full py-3 rounded-card bg-accent text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Send className="w-4 h-4" />
          {submitting ? t("Отправляем…", "Sending…") : t("Отправить админу", "Send to admin")}
        </button>
      </div>
    </div>
  );
}
