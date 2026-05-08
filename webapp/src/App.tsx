import { useEffect, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { api } from "./api";
import type {
  CategoryCode,
  MeResponse,
  Subscription,
  SubscriptionStatus,
} from "./types";
import {
  initTelegram,
  isInTelegram,
} from "./telegram";
import { AdminDashboard } from "./components/AdminDashboard";
import { BackgroundShapes } from "./components/BackgroundShapes";
import { BlacklistScreen } from "./components/BlacklistScreen";
import { CategorySurveyScreen } from "./components/CategorySurveyScreen";
import { CategoryMenuScreen } from "./components/CategoryMenuScreen";
import { DeliverySettingsScreen } from "./components/DeliverySettingsScreen";
import { SubscriptionBanner } from "./components/SubscriptionBanner";
import { SubscriptionScreen } from "./components/SubscriptionScreen";
import { SuggestChannelScreen } from "./components/SuggestChannelScreen";
import { SuggestionsProvider } from "./contexts/SuggestionsContext";
import { CreativeForm } from "./forms/CreativeForm";
import { EventForm } from "./forms/EventForm";
import { GeneralForm } from "./forms/GeneralForm";
import { AdminForm } from "./forms/AdminForm";

type Screen =
  | { kind: "loading" }
  | { kind: "error"; msg: string }
  | { kind: "survey" }
  | { kind: "menu" }
  | { kind: "form"; category: CategoryCode }
  | { kind: "blacklist" }
  | { kind: "suggestChannel" }
  | { kind: "delivery" }
  | { kind: "subscription" }
  | { kind: "addCategory" }
  | { kind: "admin" };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: "loading" });
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);
  const [subStatus, setSubStatus] = useState<SubscriptionStatus | null>(null);

  const fetchSubStatus = async () => {
    try {
      setSubStatus(await api.getSubscriptionStatus());
    } catch {
      // не валим экран если ручка ещё не задеплоена
    }
  };

  const fetchSubscriptions = async (): Promise<Subscription[]> => {
    const me: MeResponse = await api.getMe();
    setSubscriptions(me.subscriptions ?? []);
    setIsAdmin(me.is_admin);
    return me.subscriptions ?? [];
  };

  const refreshMe = async () => {
    try {
      const subs = await fetchSubscriptions();
      setScreen(subs.length === 0 ? { kind: "survey" } : { kind: "menu" });
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

  useEffect(() => {
    initTelegram();
    refreshMe();
    fetchSubStatus();
  }, []);

  const renderScreen = () => {
    if (screen.kind === "loading") {
      return (
        <div className="min-h-screen flex items-center justify-center text-slate-400 text-sm">
          Загружаем…
        </div>
      );
    }

    if (screen.kind === "error") {
      return (
        <div className="min-h-screen p-6 space-y-4">
          <h1 className="text-xl font-semibold text-red-400">
            Не удалось загрузить
          </h1>
          <p className="text-sm text-slate-300 break-words">{screen.msg}</p>
          {!isInTelegram() && (
            <p className="text-xs text-slate-500">
              Похоже, страница открыта вне Telegram — initData отсутствует,
              бэкенд возвращает 401. Откройте Mini App из бота.
            </p>
          )}
        </div>
      );
    }

    if (screen.kind === "admin") {
      return <AdminDashboard onBack={() => setScreen({ kind: "menu" })} />;
    }

    if (screen.kind === "survey") {
      return <CategorySurveyScreen onDone={refreshMe} />;
    }

    if (screen.kind === "addCategory") {
      return (
        <CategorySurveyScreen
          excludeCategories={subscriptions.map((s) => s.category)}
          onDone={refreshMe}
          title="Добавить категорию"
        />
      );
    }

    if (screen.kind === "menu") {
      return (
        <CategoryMenuScreen
          subscriptions={subscriptions}
          isAdmin={isAdmin}
          onOpenForm={(c) => setScreen({ kind: "form", category: c })}
          onAddCategory={() => setScreen({ kind: "addCategory" })}
          onAdmin={() => setScreen({ kind: "admin" })}
          onBlacklist={() => setScreen({ kind: "blacklist" })}
          onSuggestChannel={() => setScreen({ kind: "suggestChannel" })}
          onDelivery={() => setScreen({ kind: "delivery" })}
          onChange={async () => { await fetchSubscriptions(); }}
        />
      );
    }

    if (screen.kind === "blacklist") {
      return <BlacklistScreen onBack={goToMenu} />;
    }

    if (screen.kind === "suggestChannel") {
      return <SuggestChannelScreen onBack={goToMenu} />;
    }

    if (screen.kind === "delivery") {
      return <DeliverySettingsScreen onBack={goToMenu} />;
    }

    if (screen.kind === "subscription") {
      return (
        <SubscriptionScreen
          onBack={async () => {
            await fetchSubStatus();
            setScreen({ kind: "menu" });
          }}
        />
      );
    }

    if (screen.kind === "form") {
      const FormComponent = {
        creative: CreativeForm,
        event: EventForm,
        general: GeneralForm,
        admin: AdminForm,
      }[screen.category];
      return (
        <div>
          <div className="sticky top-0 z-20 bg-bg/90 backdrop-blur border-b border-bg-card">
            <button
              onClick={goToMenu}
              className="flex items-center gap-1 px-4 py-3 text-slate-400 hover:text-white"
            >
              <ChevronLeft className="w-5 h-5" />
              Назад
            </button>
          </div>
          <FormComponent onDone={refreshMe} />
        </div>
      );
    }


    return null;
  };

  // Плашка подписки видна только на главных «оседлых» экранах:
  // меню/чёрный список/предложение канала/доставка. На формах и опроснике
  // прячем — там и так нижние бары, и она заслонит контент.
  const showBanner =
    screen.kind === "menu" ||
    screen.kind === "blacklist" ||
    screen.kind === "suggestChannel" ||
    screen.kind === "delivery";

  return (
    <SuggestionsProvider>
      <BackgroundShapes />
      <div className={showBanner ? "pb-20" : ""}>{renderScreen()}</div>
      {showBanner && (
        <SubscriptionBanner
          status={subStatus}
          onClick={() => setScreen({ kind: "subscription" })}
        />
      )}
    </SuggestionsProvider>
  );
}
