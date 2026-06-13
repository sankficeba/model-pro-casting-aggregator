import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { LandingPage } from "./LandingPage";
import "./index.css";

// /app и /app/* → Telegram Mini App, иначе → лендинг для браузера.
const isMiniApp = window.location.pathname === "/app" || window.location.pathname.startsWith("/app/");

if (isMiniApp) {
  // Warmup HTTPS-соединения с API: лёгкий GET /api/health (без auth).
  fetch("/api/health").catch(() => {});
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {isMiniApp ? <App /> : <LandingPage />}
  </React.StrictMode>
);
