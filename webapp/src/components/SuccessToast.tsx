import { useEffect } from "react";
import { CheckCircle2 } from "lucide-react";

interface Props {
  message: string;
  onDismiss: () => void;
  durationMs?: number;
}

export function SuccessToast({ message, onDismiss, durationMs = 5000 }: Props) {
  useEffect(() => {
    const handle = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(handle);
  }, [onDismiss, durationMs]);

  return (
    <div
      role="status"
      className="fixed left-4 right-4 z-40 rounded-card border border-emerald-500/60 bg-emerald-950/40 backdrop-blur px-4 py-3 flex items-center gap-3 shadow-lg animate-toast-in"
      style={{ top: "calc(var(--tg-safe-top, 0px) + 12px)" }}
    >
      <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
      <div className="text-sm text-emerald-100 flex-1">{message}</div>
    </div>
  );
}
