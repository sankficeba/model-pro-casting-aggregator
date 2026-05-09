import { useEffect } from "react";
import { CheckCircle2 } from "lucide-react";

interface Props {
  message: string;
  onDismiss: () => void;
  durationMs?: number;
}

/** Inline-плашка в потоке страницы: рендерится сразу после баннера
 * подписки, не пересекается со скроллом / sticky-элементами. */
export function SuccessToast({ message, onDismiss, durationMs = 5000 }: Props) {
  useEffect(() => {
    const handle = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(handle);
  }, [onDismiss, durationMs]);

  return (
    <div className="px-4 pt-3">
      <div
        role="status"
        className="mx-auto max-w-md rounded-card border border-emerald-500/60 bg-emerald-950/40 px-4 py-3 flex items-center gap-3 shadow-lg animate-toast-in"
      >
        <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
        <div className="text-sm text-emerald-100 flex-1">{message}</div>
      </div>
    </div>
  );
}
