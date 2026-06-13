import { useEffect, useState } from "react";

const BOT_USERNAME = "ModelsProAgency_bot";
const BOT_URL = `https://t.me/${BOT_USERNAME}`;
const APP_URL = `https://t.me/${BOT_USERNAME}/app`;

function useScrollY() {
  const [y, setY] = useState(0);
  useEffect(() => {
    const onScroll = () => setY(window.scrollY);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  return y;
}

export function LandingPage() {
  const scrollY = useScrollY();

  return (
    <div className="min-h-screen" style={{ background: "#0d1326", color: "#f0f4ff" }}>
      {/* ===== NAVBAR ===== */}
      <nav
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          padding: "0 24px",
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          backdropFilter: "blur(12px)",
          background: scrollY > 20 ? "rgba(13,19,38,0.9)" : "transparent",
          transition: "background 0.3s",
          borderBottom: scrollY > 20 ? "1px solid rgba(255,255,255,0.06)" : "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 34,
              height: 34,
              background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: 14,
              color: "#fff",
            }}
          >
            MP
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: 0.5 }}>
            Model Promo Agency
          </span>
        </div>
        <a
          href={APP_URL}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
            color: "#fff",
            padding: "8px 20px",
            borderRadius: 24,
            textDecoration: "none",
            fontSize: 13,
            fontWeight: 600,
            whiteSpace: "nowrap",
          }}
        >
          Открыть в Telegram
        </a>
      </nav>

      {/* ===== HERO ===== */}
      <section
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "80px 24px 60px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Фоновые градиентные пятна */}
        <div
          style={{
            position: "absolute",
            top: "10%",
            left: "20%",
            width: 400,
            height: 400,
            background: "radial-gradient(circle, rgba(167,139,250,0.15) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "15%",
            right: "15%",
            width: 350,
            height: 350,
            background: "radial-gradient(circle, rgba(96,165,250,0.12) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        <div style={{ position: "relative", maxWidth: 680 }}>
          <div
            style={{
              display: "inline-block",
              padding: "6px 18px",
              borderRadius: 20,
              border: "1px solid rgba(167,139,250,0.4)",
              fontSize: 13,
              color: "#a78bfa",
              marginBottom: 32,
              fontWeight: 500,
            }}
          >
            Агрегатор кастингов и вакансий
          </div>

          <h1
            style={{
              fontSize: "clamp(36px, 6vw, 72px)",
              fontWeight: 800,
              lineHeight: 1.1,
              marginBottom: 24,
              background: "linear-gradient(135deg, #f0f4ff 0%, #a78bfa 50%, #60a5fa 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Первым узнавай
            <br />
            о кастингах
          </h1>

          <p
            style={{
              fontSize: "clamp(15px, 2vw, 19px)",
              color: "#94a3b8",
              lineHeight: 1.7,
              marginBottom: 44,
              maxWidth: 560,
              margin: "0 auto 44px",
            }}
          >
            Model Promo Agency — Telegram-бот, который в реальном времени
            мониторит сотни каналов и присылает подходящие кастинги,
            съёмки и event-вакансии прямо тебе.
          </p>

          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            <a
              href={APP_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 10,
                background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
                color: "#fff",
                padding: "16px 36px",
                borderRadius: 32,
                textDecoration: "none",
                fontSize: 16,
                fontWeight: 700,
                boxShadow: "0 8px 32px rgba(167,139,250,0.35)",
                transition: "transform 0.2s, box-shadow 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
                (e.currentTarget as HTMLElement).style.boxShadow = "0 12px 40px rgba(167,139,250,0.5)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.transform = "";
                (e.currentTarget as HTMLElement).style.boxShadow = "0 8px 32px rgba(167,139,250,0.35)";
              }}
            >
              <TelegramIcon />
              Начать в Telegram
            </a>
            <a
              href="#how-it-works"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                border: "1px solid rgba(255,255,255,0.15)",
                color: "#cbd5e1",
                padding: "16px 32px",
                borderRadius: 32,
                textDecoration: "none",
                fontSize: 16,
                fontWeight: 500,
                transition: "border-color 0.2s, color 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(167,139,250,0.5)";
                (e.currentTarget as HTMLElement).style.color = "#f0f4ff";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.15)";
                (e.currentTarget as HTMLElement).style.color = "#cbd5e1";
              }}
            >
              Как это работает
            </a>
          </div>
        </div>

        {/* Карточки с цифрами */}
        <div
          style={{
            display: "flex",
            gap: 20,
            marginTop: 80,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {[
            { value: "200+", label: "Каналов" },
            { value: "4", label: "Категории" },
            { value: "24/7", label: "Мониторинг" },
          ].map((stat) => (
            <div
              key={stat.label}
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 16,
                padding: "20px 36px",
                textAlign: "center",
                backdropFilter: "blur(8px)",
              }}
            >
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 800,
                  background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                {stat.value}
              </div>
              <div style={{ fontSize: 13, color: "#64748b", marginTop: 4 }}>{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ===== КАТЕГОРИИ ===== */}
      <section style={{ padding: "80px 24px", maxWidth: 1100, margin: "0 auto" }}>
        <SectionTitle>Для кого это</SectionTitle>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 20,
            marginTop: 48,
          }}
        >
          {[
            {
              emoji: "📸",
              title: "Актёры и модели",
              desc: "Кастинги в кино, сериалы, рекламные съёмки. Отбираем только релевантные под твои параметры.",
              accent: "#a78bfa",
            },
            {
              emoji: "🎉",
              title: "Event-персонал",
              desc: "Промо-модели, хостес, аниматоры. Мероприятия, выставки, корпоративы.",
              accent: "#60a5fa",
            },
            {
              emoji: "🛠",
              title: "Разнорабочие",
              desc: "Хелперы, клининг, грузчики. Ежедневные вакансии в Москве и регионах.",
              accent: "#34d399",
            },
            {
              emoji: "💻",
              title: "Администрирование",
              desc: "Операторы регистрации, супервайзеры, координаторы съёмок.",
              accent: "#fb923c",
            },
          ].map((card) => (
            <div
              key={card.title}
              style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderRadius: 20,
                padding: "28px 24px",
                transition: "border-color 0.2s, transform 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = card.accent + "66";
                (e.currentTarget as HTMLElement).style.transform = "translateY(-4px)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.07)";
                (e.currentTarget as HTMLElement).style.transform = "";
              }}
            >
              <div style={{ fontSize: 36, marginBottom: 16 }}>{card.emoji}</div>
              <h3
                style={{
                  fontSize: 17,
                  fontWeight: 700,
                  marginBottom: 10,
                  color: card.accent,
                }}
              >
                {card.title}
              </h3>
              <p style={{ fontSize: 14, color: "#64748b", lineHeight: 1.6 }}>{card.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ===== КАК ЭТО РАБОТАЕТ ===== */}
      <section
        id="how-it-works"
        style={{
          padding: "80px 24px",
          background: "rgba(255,255,255,0.02)",
          borderTop: "1px solid rgba(255,255,255,0.05)",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
        }}
      >
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <SectionTitle>Как это работает</SectionTitle>
          <div style={{ marginTop: 48, display: "flex", flexDirection: "column", gap: 0 }}>
            {[
              {
                step: "01",
                title: "Открой бота и заполни анкету",
                desc: "Укажи параметры: категорию, город, возраст, рост и предпочтения. Занимает 2 минуты.",
              },
              {
                step: "02",
                title: "Мы мониторим каналы",
                desc: "Бот круглосуточно парсит более 200 Telegram-каналов с кастингами и вакансиями.",
              },
              {
                step: "03",
                title: "Получай только нужное",
                desc: "Уведомления приходят только по твоим параметрам. Никакого спама, только релевантные предложения.",
              },
              {
                step: "04",
                title: "Откликайся одним кликом",
                desc: "Бот готовит персональный отклик на основе твоей анкеты — копируй и отправляй кастинг-директору.",
              },
            ].map((item, idx, arr) => (
              <div
                key={item.step}
                style={{
                  display: "flex",
                  gap: 24,
                  paddingBottom: idx < arr.length - 1 ? 36 : 0,
                  marginBottom: idx < arr.length - 1 ? 36 : 0,
                  borderBottom: idx < arr.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none",
                }}
              >
                <div
                  style={{
                    flexShrink: 0,
                    width: 52,
                    height: 52,
                    borderRadius: 14,
                    background: "linear-gradient(135deg, rgba(167,139,250,0.15), rgba(96,165,250,0.15))",
                    border: "1px solid rgba(167,139,250,0.3)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: 13,
                    fontWeight: 800,
                    color: "#a78bfa",
                    letterSpacing: 1,
                  }}
                >
                  {item.step}
                </div>
                <div>
                  <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 8 }}>{item.title}</h3>
                  <p style={{ fontSize: 14, color: "#64748b", lineHeight: 1.65 }}>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== ВОЗМОЖНОСТИ ===== */}
      <section style={{ padding: "80px 24px", maxWidth: 1100, margin: "0 auto" }}>
        <SectionTitle>Что внутри</SectionTitle>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 16,
            marginTop: 48,
          }}
        >
          {[
            { icon: "🎯", text: "Умная фильтрация по твоим параметрам" },
            { icon: "⭐", text: "Избранное — сохраняй лучшие предложения" },
            { icon: "🚫", text: "Чёрный список нежелательных слов" },
            { icon: "📊", text: "Дайджест — все новинки одним списком" },
            { icon: "💌", text: "Готовый текст отклика за секунду" },
            { icon: "🔔", text: "Мгновенные уведомления о новых кастингах" },
          ].map((feat) => (
            <div
              key={feat.text}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 14,
                padding: "18px 20px",
              }}
            >
              <span style={{ fontSize: 24, flexShrink: 0 }}>{feat.icon}</span>
              <span style={{ fontSize: 14, color: "#cbd5e1", lineHeight: 1.5 }}>{feat.text}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section
        style={{
          padding: "80px 24px 100px",
          textAlign: "center",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            width: 600,
            height: 400,
            background: "radial-gradient(ellipse, rgba(167,139,250,0.12) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <div style={{ position: "relative", maxWidth: 560, margin: "0 auto" }}>
          <h2
            style={{
              fontSize: "clamp(28px, 5vw, 48px)",
              fontWeight: 800,
              marginBottom: 20,
              lineHeight: 1.2,
            }}
          >
            Готов попробовать?
          </h2>
          <p style={{ fontSize: 16, color: "#64748b", marginBottom: 40, lineHeight: 1.65 }}>
            Запусти бота, заполни анкету за 2 минуты и получай кастинги раньше всех.
          </p>
          <a
            href={APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 12,
              background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
              color: "#fff",
              padding: "18px 44px",
              borderRadius: 36,
              textDecoration: "none",
              fontSize: 17,
              fontWeight: 700,
              boxShadow: "0 8px 40px rgba(167,139,250,0.4)",
              transition: "transform 0.2s, box-shadow 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
              (e.currentTarget as HTMLElement).style.boxShadow = "0 14px 50px rgba(167,139,250,0.55)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "";
              (e.currentTarget as HTMLElement).style.boxShadow = "0 8px 40px rgba(167,139,250,0.4)";
            }}
          >
            <TelegramIcon size={22} />
            Открыть Mini App
          </a>
          <div style={{ marginTop: 20, fontSize: 13, color: "#475569" }}>
            или найди нас:{" "}
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#a78bfa", textDecoration: "none" }}
            >
              @{BOT_USERNAME}
            </a>
          </div>
        </div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer
        style={{
          borderTop: "1px solid rgba(255,255,255,0.06)",
          padding: "32px 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
          maxWidth: 1100,
          margin: "0 auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 28,
              height: 28,
              background: "linear-gradient(135deg, #a78bfa, #60a5fa)",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: 11,
              color: "#fff",
            }}
          >
            MP
          </div>
          <span style={{ fontSize: 13, color: "#475569" }}>
            © {new Date().getFullYear()} Model Promo Agency
          </span>
        </div>
        <a
          href={BOT_URL}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            fontSize: 13,
            color: "#a78bfa",
            textDecoration: "none",
          }}
        >
          <TelegramIcon size={16} />
          Telegram-бот
        </a>
      </footer>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2
      style={{
        fontSize: "clamp(24px, 4vw, 40px)",
        fontWeight: 800,
        textAlign: "center",
        marginBottom: 0,
      }}
    >
      {children}
    </h2>
  );
}

function TelegramIcon({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      style={{ flexShrink: 0 }}
    >
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.018 9.51c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.881.711z" />
    </svg>
  );
}
