import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { LandingPage } from "./LandingPage";
import { OfferPage, PrivacyPage, ContactsPage } from "./LegalPages";
import { LangProvider } from "./i18n";
import "./index.css";

const path = window.location.pathname;
const isMiniApp = path === "/app" || path.startsWith("/app/");

if (isMiniApp) {
  fetch("/api/health").catch(() => {});
}

function Root() {
  if (isMiniApp)       return <App />;
  if (path === "/offer")    return <OfferPage />;
  if (path === "/privacy")  return <PrivacyPage />;
  if (path === "/contacts") return <ContactsPage />;
  return <LandingPage />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LangProvider>
      <Root />
    </LangProvider>
  </React.StrictMode>
);
