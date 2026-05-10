import { useState } from "react";
import { ChevronLeft, Send } from "lucide-react";
import { api } from "../api";

interface Props {
  onBack: () => void;
}

export function ReportProblemScreen({ onBack }: Props) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const submit = async () => {
    const trimmed = text.trim();
    if (trimmed.length < 3) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.reportProblem(trimmed);
      setSuccess(true);
      setText("");
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
          Назад
        </button>
      </div>

      <div className="p-5 space-y-4">
        <h1 className="text-2xl font-semibold">Сообщить о проблеме</h1>
        <p className="text-sm text-slate-400">
          Опиши, что пошло не так. Админ получит уведомление и
          свяжется при необходимости.
        </p>

        <label className="block space-y-1">
          <span className="text-sm text-slate-400">
            Описание проблемы
            <span className="text-red-400 ml-0.5">*</span>
          </span>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Например: не приходят уведомления по моей категории"
            rows={6}
            maxLength={2000}
            className="w-full bg-bg-card rounded-card px-3 py-2 outline-none focus:ring-1 ring-accent resize-none"
          />
          <span className="text-xs text-slate-500 block text-right">
            {text.length}/2000
          </span>
        </label>

        {error && (
          <div className="rounded-card bg-red-950/40 border border-red-900 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {success && (
          <div className="rounded-card bg-emerald-950/40 border border-emerald-900 px-4 py-3 text-sm text-emerald-300">
            Спасибо! Админ получил уведомление.
          </div>
        )}

        <button
          onClick={submit}
          disabled={text.trim().length < 3 || submitting}
          className="w-full py-3 rounded-card bg-accent text-white font-medium disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <Send className="w-4 h-4" />
          {submitting ? "Отправляем…" : "Отправить"}
        </button>
      </div>
    </div>
  );
}
