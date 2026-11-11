import { CheckCircle2, UserRound } from "lucide-react";
import { useLang } from "../i18n";

interface Props {
  missing: boolean;
  onOpen: () => void;
}

/** Плашка в начале анкеты направления: ссылка на «Основную информацию»
 * (общие поля теперь редактируются только там). */
export function BaseInfoNotice({ missing, onOpen }: Props) {
  const { t } = useLang();
  return (
    <button
      onClick={onOpen}
      className={`w-full p-3 rounded-card border text-left flex items-center gap-3 transition ${
        missing ? "border-amber-400/60 bg-amber-400/10" : "border-bg-card hover:border-accent"
      }`}
    >
      {missing ? (
        <UserRound className="w-5 h-5 text-amber-400 shrink-0" />
      ) : (
        <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
      )}
      <div className="flex-1 min-w-0 text-sm">
        <div className="font-medium">{t("Основная информация", "Basic information")}</div>
        <div className="text-xs text-slate-400">
          {missing
            ? t("Сначала заполни ФИО, возраст, город и контакты →", "Fill in your name, age, city and contacts first →")
            : t("ФИО, возраст, город и контакты — общие для всех анкет", "Name, age, city and contacts — shared by all applications")}
        </div>
      </div>
    </button>
  );
}
