import { useEffect, useState } from "react";
import { api } from "./api";
import type { CategoryCode, MeResponse, Subscription } from "./types";
import {
  initTelegram,
  isInTelegram,
} from "./telegram";
import { AdminDashboard } from "./components/AdminDashboard";
import { CategorySurveyScreen } from "./components/CategorySurveyScreen";
import { CategoryMenuScreen } from "./components/CategoryMenuScreen";
import { SettingsScreen } from "./components/SettingsScreen";
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
  | { kind: "settings" }
  | { kind: "addCategory" }
  | { kind: "admin" };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ kind: "loading" });
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [isAdmin, setIsAdmin] = useState(false);

  const refreshMe = async () => {
    try {
      const me: MeResponse = await api.getMe();
      setSubscriptions(me.subscriptions ?? []);
      setIsAdmin(me.is_admin);
      if ((me.subscriptions ?? []).length === 0) {
        setScreen({ kind: "survey" });
      } else {
        setScreen({ kind: "menu" });
      }
    } catch (e) {
      setScreen({
        kind: "error",
        msg: e instanceof Error ? e.message : String(e),
      });
    }
  };

  useEffect(() => {
    initTelegram();
    refreshMe();
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
          onSettings={() => setScreen({ kind: "settings" })}
          onAdmin={() => setScreen({ kind: "admin" })}
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
              onClick={() => setScreen({ kind: "menu" })}
              className="px-4 py-3 text-slate-400 hover:text-white"
            >
              ← Назад
            </button>
          </div>
          <FormComponent onDone={refreshMe} />
        </div>
      );
    }

    if (screen.kind === "settings") {
      return (
        <SettingsScreen
          subscriptions={subscriptions}
          onChange={refreshMe}
          onEditForm={(c) => setScreen({ kind: "form", category: c })}
          onAddCategory={() => setScreen({ kind: "addCategory" })}
          onBack={() => setScreen({ kind: "menu" })}
        />
      );
    }

    return null;
  };

  return <SuggestionsProvider>{renderScreen()}</SuggestionsProvider>;
}
