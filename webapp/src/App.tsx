import { useEffect, useRef, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { api } from "./api";
import type {
  CategoryCode,
  MeResponse,
  Subscription,
} from "./types";
import {
  initTelegram,
  isInTelegram,
} from "./telegram";
import { AdminDashboard } from "./components/AdminDashboard";
import { BackgroundShapes } from "./components/BackgroundShapes";
import { BotChatRequiredBanner } from "./components/BotChatRequiredBanner";
import { CategoryMenuScreen } from "./components/CategoryMenuScreen";
import { SuccessToast } from "./components/SuccessToast";
import { SuggestionsProvider } from "./contexts/SuggestionsContext";
import { CreativeForm } from "./forms/CreativeForm";
import { EventForm } from "./forms/EventForm";
import { GeneralForm } from "./forms/GeneralForm";
import { AdminForm } from "./forms/AdminForm";
import { BaseInfoForm } from "./forms/BaseInfoForm";
import { useLang } from "./i18n";

type Screen =
  | { kind: "loading" }
  | { kind: "error"; msg: string }
  | { kind: "menu" }
  | { kind: "form"; category: CategoryCode }
  // returnTo — анкета направления, из которой открыли «Основную информацию».
  | { kind: "base"; returnTo?: CategoryCode }
  | { kind: "admin" };

export default function App() {
  const { t, syncWithServer } = useLang();
  const [screen, setScreen] = useState<Screen>({ kind: "loading" });
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  // Подписка и её оплата живут в боте (главное меню); в Mini App остаётся
  // только тост после возврата из ЮKassa.
  const [paymentToast, setPaymentToast] = useState<string | null>(null);

  const [botChatActive, setBotChatActive] = useState<boolean>(true);

  // Язык с сервера применяем один раз при старте: при последующих /me
  // рефетчах он мог бы откатить только что сделанное переключение, если
  // PUT /me/language ещё не долетел.
  const langSynced = useRef(false);

  const fetchSubscriptions = async (): Promise<Subscription[]> => {
    const me: MeResponse = await api.getMe();
    if (!langSynced.current) {
      langSynced.current = true;
      syncWithServer(me.language);
    }
    setSubscriptions(me.subscriptions ?? []);
    setIsAdmin(me.is_admin);
    setBotChatActive(me.bot_chat_active !== false);
    return me.subscriptions ?? [];
  };

  const refreshMe = async () => {
    try {
      // Отдельного экрана выбора направлений нет: все 4 видны в меню,
      // невыбранное добавляется по нажатию.
      await fetchSubscriptions();
      setScreen({ kind: "menu" });
    } catch (e) {
      setScreen({
        kind: "error",
        msg: e instanceof Error ? e.message : String(e),
      });
    }
  };

  /** Возврат в меню с обновлением подписок (но без сброса в опросник).
   * Используется при «← Назад» с формы — чтобы прогресс-бары обновились. */
  const goToMenu = async () => {
    fetchSubscriptions().catch(() => {});  // обновим в фоне, ошибки игнорим
    setScreen({ kind: "menu" });
  };

  // Keepalive ping каждые 30 сек: iOS WebKit агрессивно закрывает
  // idle HTTP/2 connections. Без этого следующий клик после ~30с idle
  // снова попадает на cold-start TLS handshake (~8с).
  useEffect(() => {
    const id = window.setInterval(() => {
      fetch("/api/health").catch(() => {});
    }, 30_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    initTelegram();
    refreshMe();
    // Если юзер только что вернулся из ЮKassa после успешной оплаты —
    // показываем toast. Маркер ?paid=1 чистим из URL, чтобы при
    // случайном refresh не показывать тост повторно.
    const params = new URLSearchParams(window.location.search);
    if (params.get("paid") === "1") {
      params.delete("paid");
      const cleanSearch = params.toString();
      const cleanUrl =
        window.location.pathname +
        (cleanSearch ? `?${cleanSearch}` : "") +
        window.location.hash;
      window.history.replaceState({}, "", cleanUrl);
      setPaymentToast(
        t("✅ Оплата прошла. Подписка активирована!", "✅ Payment successful. Subscription activated!")
      );
    }
  }, []);

  const renderScreen = () => {
    if (screen.kind === "loading") {
      return (
        <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">
          {t("Загружаем…", "Loading…")}
        </div>
      );
    }

    if (screen.kind === "error") {
      return (
        <div className="min-h-screen p-6 space-y-4">
          <h1 className="text-xl font-semibold text-red-400">
            {t("Не удалось загрузить", "Failed to load")}
          </h1>
          <p className="text-sm text-slate-300 break-words">{screen.msg}</p>
          {!isInTelegram() && (
            <p className="text-xs text-slate-500">
              {t(
                "Похоже, страница открыта вне Telegram — initData отсутствует, бэкенд возвращает 401. Откройте Mini App из бота.",
                "Looks like the page was opened outside Telegram — initData is missing, the backend returns 401. Open the Mini App from the bot.",
              )}
            </p>
          )}
        </div>
      );
    }

    if (screen.kind === "admin") {
      return <AdminDashboard onBack={() => setScreen({ kind: "menu" })} />;
    }

    if (screen.kind === "menu") {
      return (
        <CategoryMenuScreen
          subscriptions={subscriptions}
          isAdmin={isAdmin}
          onOpenForm={(c) => setScreen({ kind: "form", category: c })}
          onStartCategory={async (c) => {
            try {
              await api.createSubscriptions([c]);
              await fetchSubscriptions();
              setScreen({ kind: "form", category: c });
            } catch (e) {
              setScreen({ kind: "error", msg: e instanceof Error ? e.message : String(e) });
            }
          }}
          onOpenBase={() => setScreen({ kind: "base" })}
          onAdmin={() => setScreen({ kind: "admin" })}
          onChange={async () => { await fetchSubscriptions(); }}
        />
      );
    }

    const backBar = (onBack: () => void) => (
      <div className="sticky top-0 z-20 bg-bg/90 backdrop-blur border-b border-bg-card">
        <button
          onClick={onBack}
          className="flex items-center gap-1 px-4 py-3 text-slate-400 hover:text-white"
        >
          <ChevronLeft className="w-5 h-5" />
          {t("Назад", "Back")}
        </button>
      </div>
    );

    if (screen.kind === "form") {
      const FormComponent = {
        creative: CreativeForm,
        event: EventForm,
        general: GeneralForm,
        admin: AdminForm,
      }[screen.category];
      const category = screen.category;
      return (
        <div>
          {backBar(goToMenu)}
          <FormComponent
            key={category}
            onDone={refreshMe}
            onOpenBase={() => setScreen({ kind: "base", returnTo: category })}
          />
        </div>
      );
    }

    if (screen.kind === "base") {
      const returnTo = screen.returnTo;
      const back = () =>
        returnTo ? setScreen({ kind: "form", category: returnTo }) : goToMenu();
      return (
        <div>
          {backBar(back)}
          <BaseInfoForm
            onDone={async () => {
              await fetchSubscriptions().catch(() => {});
              back();
            }}
          />
        </div>
      );
    }


    return null;
  };

  return (
    <SuggestionsProvider>
      <BackgroundShapes />
      {!botChatActive && screen.kind !== "loading" && screen.kind !== "error" && (
        <BotChatRequiredBanner />
      )}
      {paymentToast && (
        <SuccessToast
          message={paymentToast}
          onDismiss={() => setPaymentToast(null)}
        />
      )}
      {renderScreen()}
    </SuggestionsProvider>
  );
}
