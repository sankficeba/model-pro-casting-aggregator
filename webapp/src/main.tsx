import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Warmup HTTPS-соединения с API: лёгкий GET /api/health (без auth).
// На cold-start первый fetch тратит ~8 сек на TLS handshake. Дёргаем
// сейчас в фоне, чтобы к моменту первого реального запроса коннект
// был тёплым → ответ ~200мс вместо 8с.
fetch("/api/health").catch(() => {});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
