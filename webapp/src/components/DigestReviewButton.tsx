import { useEffect, useState } from "react";
import { PlayCircle } from "lucide-react";
import { api } from "../api";
import { tg } from "../telegram";
import { useLang } from "../i18n";

interface Props {
  pendingCount: number;
  // Вызывается, когда бэкенд сообщил, что очередь пуста.
  onEmpty?: () => void;
}

/** Кнопка «Пролистать накопленные объявления» (digest mode): просит бэкенд
 * прислать первое pending-объявление в чат с ботом и закрывает Mini App. */
export function DigestReviewButton({ pendingCount, onEmpty }: Props) {
  const { t } = useLang();
  const [reviewing, setReviewing] = useState(false);
  const [emptyQueue, setEmptyQueue] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!emptyQueue) return;
    const handle = setTimeout(() => setEmptyQueue(false), 3000);
    return () => clearTimeout(handle);
  }, [emptyQueue]);

  const startReview = async () => {
    setReviewing(true);
    setError(null);
    setEmptyQueue(false);
    try {
      const res = await api.startDigestReview();
      if (!res.sent) {
        setEmptyQueue(true);
        onEmpty?.();
        setReviewing(false);
        return;
      }
      tg?.close();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setReviewing(false);
    }
  };

  return (
    <>
      <button
        onClick={startReview}
        disabled={reviewing}
        className="w-full p-4 rounded-card border border-accent/40 text-left flex items-center gap-3 transition hover:border-accent disabled:opacity-50"
      >
        <PlayCircle className="w-5 h-5 text-accent shrink-0" />
        <div className="flex-1">
          <div className="font-medium">
            {reviewing
              ? t("Открываем…", "Opening…")
              : t(
                  `Пролистать накопленные объявления${
                    pendingCount > 0 ? ` (${pendingCount})` : ""
                  }`,
                  `Browse collected postings${
                    pendingCount > 0 ? ` (${pendingCount})` : ""
                  }`,
                )}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            {t(
              "Mini App закроется, и в чате с ботом начнут приходить накопленные кастинги.",
              "The Mini App will close, and collected castings will start arriving in the bot chat.",
            )}
          </div>
        </div>
      </button>
      {emptyQueue && (
        <div
          role="status"
          className="rounded-card border border-red-500/60 bg-red-950/30 text-red-200 text-sm px-3 py-2 animate-fade-in-out"
        >
          {t("Пока что новых объявлений нет.", "There are no new postings yet.")}
        </div>
      )}
      {error && (
        <div className="rounded-card border border-red-500/60 bg-red-950/30 text-red-200 text-sm px-3 py-2">
          {error}
        </div>
      )}
    </>
  );
}
