import { useEffect, useRef, useState } from "react";

const BOT_USERNAME = "ModelProAgency_bot";
const APP_URL = `https://t.me/${BOT_USERNAME}/app`;
const BOT_URL = `https://t.me/${BOT_USERNAME}`;

const GOLD = "#c9a96e";
const BLACK = "#111111";
const WHITE = "#ffffff";
const LIGHT = "#f7f7f5";

// ─── Slider ───────────────────────────────────────────────────────────────────

const SLIDES = [
  "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=640&q=80",
  "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=640&q=80",
  "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=640&q=80",
  "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=640&q=80",
];

function PhotoSlider() {
  const [active, setActive] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const go = (i: number) => setActive((i + SLIDES.length) % SLIDES.length);

  useEffect(() => {
    timer.current = setInterval(() => setActive((p) => (p + 1) % SLIDES.length), 4000);
    return () => { if (timer.current) clearInterval(timer.current); };
  }, []);

  return (
    <div style={{ position: "relative", overflow: "hidden", background: "#222" }}>
      <div
        style={{
          display: "flex",
          transform: `translateX(-${active * 25}%)`,
          transition: "transform 0.7s cubic-bezier(.77,0,.18,1)",
          width: `${SLIDES.length * 25}%`,
        }}
      >
        {SLIDES.map((src, i) => (
          <div key={i} style={{ width: `${100 / SLIDES.length}%`, aspectRatio: "3/4", overflow: "hidden" }}>
            <img
              src={src}
              alt=""
              style={{ width: "100%", height: "100%", objectFit: "cover", filter: "grayscale(30%)" }}
            />
          </div>
        ))}
      </div>

      {/* Arrows */}
      {[{ dir: -1, label: "←", pos: "left" }, { dir: 1, label: "→", pos: "right" }].map(({ dir, label, pos }) => (
        <button
          key={pos}
          onClick={() => go(active + dir)}
          style={{
            position: "absolute",
            top: "50%",
            [pos]: 20,
            transform: "translateY(-50%)",
            background: "rgba(255,255,255,0.85)",
            border: "none",
            width: 44,
            height: 44,
            borderRadius: "50%",
            cursor: "pointer",
            fontSize: 18,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: BLACK,
          }}
        >
          {label}
        </button>
      ))}

      {/* Dots */}
      <div style={{ position: "absolute", bottom: 16, left: "50%", transform: "translateX(-50%)", display: "flex", gap: 8 }}>
        {SLIDES.map((_, i) => (
          <button
            key={i}
            onClick={() => setActive(i)}
            style={{
              width: i === active ? 28 : 8,
              height: 8,
              borderRadius: 4,
              background: i === active ? GOLD : "rgba(255,255,255,0.5)",
              border: "none",
              cursor: "pointer",
              transition: "all 0.3s",
              padding: 0,
            }}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Main ──────────────────────────────────────────────────────────────────────

export function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <div style={{ background: WHITE, color: BLACK, fontFamily: "'Segoe UI', Arial, sans-serif", minHeight: "100vh" }}>

      {/* ── NAV ── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        height: 72,
        background: scrolled ? "rgba(255,255,255,0.97)" : WHITE,
        borderBottom: `1px solid ${scrolled ? "#e5e5e5" : "#e5e5e5"}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 48px",
        transition: "box-shadow 0.3s",
        boxShadow: scrolled ? "0 2px 16px rgba(0,0,0,0.08)" : "none",
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{
            width: 50, height: 50,
            background: BLACK,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            lineHeight: 1,
          }}>
            <span style={{ color: WHITE, fontWeight: 800, fontSize: 13, letterSpacing: 1 }}>MODEL</span>
            <span style={{ color: GOLD, fontWeight: 400, fontSize: 9, letterSpacing: 2 }}>PROMO</span>
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: 2, textTransform: "uppercase" }}>Model Promo</div>
            <div style={{ fontSize: 10, letterSpacing: 3, color: "#888", textTransform: "uppercase" }}>Agency</div>
          </div>
        </div>

        {/* Nav links */}
        <div style={{ display: "flex", gap: 36, alignItems: "center" }}>
          {["Кастинги", "Для кого", "Как работает", "О нас"].map((l) => (
            <a
              key={l}
              href={`#${l}`}
              style={{
                fontSize: 11, letterSpacing: 2, textTransform: "uppercase",
                color: BLACK, textDecoration: "none", fontWeight: 500,
                borderBottom: `2px solid transparent`, paddingBottom: 2,
                transition: "border-color 0.2s, color 0.2s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.borderBottomColor = GOLD;
                (e.currentTarget as HTMLElement).style.color = GOLD;
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.borderBottomColor = "transparent";
                (e.currentTarget as HTMLElement).style.color = BLACK;
              }}
            >
              {l}
            </a>
          ))}
          <a
            href={APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              fontSize: 11, letterSpacing: 2, textTransform: "uppercase",
              color: BLACK, textDecoration: "none", fontWeight: 600,
              border: `1px solid ${BLACK}`,
              padding: "10px 22px",
              transition: "background 0.2s, color 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = BLACK;
              (e.currentTarget as HTMLElement).style.color = WHITE;
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
              (e.currentTarget as HTMLElement).style.color = BLACK;
            }}
          >
            Открыть бота
          </a>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section style={{
        paddingTop: 72,
        minHeight: "100vh",
        background: "#0a0a0a",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* Фоновые градиентные блики */}
        <div style={{
          position: "absolute", top: "20%", left: "30%",
          width: 600, height: 600,
          background: "radial-gradient(circle, rgba(201,169,110,0.08) 0%, transparent 65%)",
          pointerEvents: "none",
        }} />
        <div style={{
          position: "absolute", bottom: "15%", right: "25%",
          width: 400, height: 400,
          background: "radial-gradient(circle, rgba(201,169,110,0.06) 0%, transparent 65%)",
          pointerEvents: "none",
        }} />

        {/* Центральный блок — рамка */}
        <div style={{
          border: "1px solid rgba(255,255,255,0.25)",
          padding: "64px 88px",
          textAlign: "center",
          position: "relative",
        }}>
          {/* Уголки как у рамки */}
          {[
            { top: -1, left: -1, borderTop: "2px solid " + GOLD, borderLeft: "2px solid " + GOLD },
            { top: -1, right: -1, borderTop: "2px solid " + GOLD, borderRight: "2px solid " + GOLD },
            { bottom: -1, left: -1, borderBottom: "2px solid " + GOLD, borderLeft: "2px solid " + GOLD },
            { bottom: -1, right: -1, borderBottom: "2px solid " + GOLD, borderRight: "2px solid " + GOLD },
          ].map((s, i) => (
            <div key={i} style={{ position: "absolute", width: 24, height: 24, ...s }} />
          ))}

          <h1 style={{
            fontSize: "clamp(52px, 8vw, 120px)",
            fontWeight: 800,
            lineHeight: 0.95,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            fontFamily: "Georgia, 'Times New Roman', serif",
            background: "linear-gradient(160deg, #ffffff 0%, #e8d5a3 40%, #c9a96e 70%, #ffffff 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            marginBottom: 20,
          }}>
            Model Pro
          </h1>

          <div style={{
            fontSize: "clamp(14px, 2.5vw, 26px)",
            letterSpacing: "0.55em",
            textTransform: "uppercase",
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontWeight: 400,
            background: "linear-gradient(90deg, rgba(255,255,255,0.5) 0%, rgba(201,169,110,0.9) 50%, rgba(255,255,255,0.5) 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}>
            Agency
          </div>
        </div>

        {/* Подзаголовок */}
        <p style={{
          marginTop: 52,
          fontSize: 14,
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "rgba(255,255,255,0.4)",
          textAlign: "center",
        }}>
          Агрегатор кастингов и вакансий
        </p>

        {/* Кнопки */}
        <div style={{ display: "flex", gap: 16, marginTop: 40, flexWrap: "wrap", justifyContent: "center" }}>
          <a
            href={APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex", alignItems: "center", gap: 10,
              background: GOLD, color: BLACK,
              padding: "16px 40px", textDecoration: "none",
              fontSize: 11, letterSpacing: 3, fontWeight: 700, textTransform: "uppercase",
              transition: "opacity 0.2s",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = "0.85"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = "1"; }}
          >
            <TgIcon /> Открыть Mini App
          </a>
          <a
            href="#как-работает"
            style={{
              display: "inline-flex", alignItems: "center",
              border: "1px solid rgba(255,255,255,0.2)",
              color: "rgba(255,255,255,0.7)", padding: "16px 32px", textDecoration: "none",
              fontSize: 11, letterSpacing: 3, fontWeight: 500, textTransform: "uppercase",
              transition: "border-color 0.2s, color 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = GOLD;
              (e.currentTarget as HTMLElement).style.color = GOLD;
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.2)";
              (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.7)";
            }}
          >
            Узнать больше
          </a>
        </div>

        {/* Статистика */}
        <div style={{ display: "flex", gap: 64, marginTop: 80 }}>
          {[["200+", "Каналов"], ["4", "Категории"], ["24/7", "Мониторинг"]].map(([n, l]) => (
            <div key={l} style={{ textAlign: "center" }}>
              <div style={{
                fontSize: 32, fontWeight: 800, letterSpacing: -1,
                background: `linear-gradient(135deg, ${WHITE}, ${GOLD})`,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}>{n}</div>
              <div style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginTop: 6 }}>{l}</div>
            </div>
          ))}
        </div>

        {/* Scroll indicator */}
        <div style={{
          position: "absolute", bottom: 32, left: "50%", transform: "translateX(-50%)",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
          color: "rgba(255,255,255,0.25)", fontSize: 10, letterSpacing: 3, textTransform: "uppercase",
        }}>
          <span>Scroll</span>
          <div style={{ width: 1, height: 40, background: `linear-gradient(to bottom, rgba(201,169,110,0.6), transparent)` }} />
        </div>
      </section>

      {/* ── GOLD DIVIDER ── */}
      <div style={{ height: 1, background: GOLD, margin: "0 48px" }} />

      {/* ── PHOTO GRID: "ПОСЛЕДНИЕ КАСТИНГИ" ── */}
      <section style={{ padding: "72px 48px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 40 }}>
          <h2 style={{ fontSize: 13, letterSpacing: 4, textTransform: "uppercase", fontWeight: 600 }}>
            Активные кастинги
          </h2>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none" }}>
            Смотреть все →
          </a>
        </div>
        <div style={{ position: "relative" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
            {[
              { img: "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=400&q=80", label: "Реклама — Москва" },
              { img: "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=400&q=80", label: "Съёмка — СПб" },
              { img: "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=400&q=80", label: "Event — Москва" },
              { img: "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=400&q=80", label: "Кино — Краснодар" },
            ].map(({ img, label }) => (
              <a
                key={label}
                href={APP_URL}
                target="_blank"
                rel="noopener noreferrer"
                style={{ display: "block", textDecoration: "none", color: "inherit", overflow: "hidden" }}
              >
                <div style={{ overflow: "hidden", aspectRatio: "3/4" }}>
                  <img
                    src={img}
                    alt={label}
                    style={{ width: "100%", height: "100%", objectFit: "cover", filter: "grayscale(40%)", transition: "transform 0.5s, filter 0.3s" }}
                    onMouseEnter={(e) => {
                      (e.currentTarget as HTMLElement).style.transform = "scale(1.04)";
                      (e.currentTarget as HTMLElement).style.filter = "grayscale(0%)";
                    }}
                    onMouseLeave={(e) => {
                      (e.currentTarget as HTMLElement).style.transform = "";
                      (e.currentTarget as HTMLElement).style.filter = "grayscale(40%)";
                    }}
                  />
                </div>
                <div style={{ paddingTop: 12, fontSize: 12, letterSpacing: 1, textTransform: "uppercase", color: "#555" }}>{label}</div>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* ── GOLD DIVIDER ── */}
      <div style={{ height: 1, background: GOLD, margin: "0 48px" }} />

      {/* ── SPLIT: СТАТЬ УЧАСТНИКОМ ── */}
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        {/* Photo */}
        <div style={{ overflow: "hidden", minHeight: 520 }}>
          <img
            src="https://images.unsplash.com/photo-1581044777550-4cfa60707c03?w=800&q=85"
            alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover", filter: "grayscale(20%)" }}
          />
        </div>
        {/* Text */}
        <div style={{ padding: "80px 72px", background: LIGHT, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ fontSize: 11, letterSpacing: 3, textTransform: "uppercase", color: GOLD, marginBottom: 20 }}>
            Telegram Mini App
          </div>
          <h2 style={{
            fontSize: "clamp(28px, 3vw, 44px)", fontWeight: 800,
            textTransform: "uppercase", letterSpacing: 2, lineHeight: 1.1,
            marginBottom: 24,
          }}>
            Стать участником
          </h2>
          <p style={{ fontSize: 15, lineHeight: 1.8, color: "#555", marginBottom: 40, maxWidth: 420 }}>
            Погрузись в мир кастингов и индустрию красоты. Заполни анкету
            в нашем Telegram Mini App за 2 минуты — и получай только
            те предложения, которые подходят именно тебе: по возрасту,
            параметрам, городу и категории.
          </p>
          <a
            href={APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-block", alignSelf: "flex-start",
              border: `1px solid ${BLACK}`, color: BLACK,
              padding: "14px 36px", textDecoration: "none",
              fontSize: 11, letterSpacing: 2, fontWeight: 600, textTransform: "uppercase",
              transition: "background 0.2s, color 0.2s",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = BLACK;
              (e.currentTarget as HTMLElement).style.color = WHITE;
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = "transparent";
              (e.currentTarget as HTMLElement).style.color = BLACK;
            }}
          >
            Заполнить анкету
          </a>
        </div>
      </section>

      {/* ── SPLIT: ПРОФЕССИОНАЛЬНЫЙ ПОДХОД (reverse) ── */}
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr" }}>
        {/* Text */}
        <div style={{ padding: "80px 72px", background: WHITE, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ fontSize: 11, letterSpacing: 3, textTransform: "uppercase", color: GOLD, marginBottom: 20 }}>
            Умный агрегатор
          </div>
          <h2 style={{
            fontSize: "clamp(28px, 3vw, 44px)", fontWeight: 800,
            textTransform: "uppercase", letterSpacing: 2, lineHeight: 1.1,
            marginBottom: 24,
          }}>
            Профессиональный<br />подход
          </h2>
          <p style={{ fontSize: 15, lineHeight: 1.8, color: "#555", marginBottom: 40, maxWidth: 420 }}>
            Мы анализируем огромную сеть каналов и агентств в реальном
            времени. ИИ разбирает каждое объявление, извлекает параметры
            вакансии и сравнивает их с твоей анкетой — так ты получаешь
            уведомления первым и только о подходящих предложениях.
          </p>
          <a
            href={APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-block", alignSelf: "flex-start",
              background: GOLD, color: WHITE,
              padding: "14px 36px", textDecoration: "none",
              fontSize: 11, letterSpacing: 2, fontWeight: 600, textTransform: "uppercase",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "#b8924f"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = GOLD; }}
          >
            Попробовать
          </a>
        </div>
        {/* Photo */}
        <div style={{ overflow: "hidden", minHeight: 520 }}>
          <img
            src="https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&q=85"
            alt=""
            style={{ width: "100%", height: "100%", objectFit: "cover", filter: "grayscale(20%)" }}
          />
        </div>
      </section>

      {/* ── GOLD DIVIDER ── */}
      <div style={{ height: 1, background: GOLD, margin: "0 48px" }} />

      {/* ── PHOTO SLIDER ── */}
      <section style={{ padding: "72px 48px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 40 }}>
          <h2 style={{ fontSize: 13, letterSpacing: 4, textTransform: "uppercase", fontWeight: 600 }}>
            Портфолио участников
          </h2>
        </div>
        <PhotoSlider />
      </section>

      {/* ── GOLD DIVIDER ── */}
      <div style={{ height: 1, background: GOLD, margin: "0 48px" }} />

      {/* ── CATEGORIES ── */}
      <section style={{ padding: "72px 48px" }} id="Кастинги">
        <h2 style={{ fontSize: 13, letterSpacing: 4, textTransform: "uppercase", fontWeight: 600, marginBottom: 40 }}>
          Категории
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
          {[
            {
              img: "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=600&q=85",
              title: "Актёры и модели",
              sub: "Кастинги в кино, сериалы, реклама",
            },
            {
              img: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=600&q=85",
              title: "Event-персонал",
              sub: "Хостес, промо, аниматоры",
            },
            {
              img: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=600&q=85",
              title: "Разнорабочие",
              sub: "Хелперы, клининг, логистика",
            },
          ].map(({ img, title, sub }) => (
            <a
              key={title}
              href={APP_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{ position: "relative", display: "block", overflow: "hidden", textDecoration: "none" }}
            >
              <div style={{ aspectRatio: "2/3", overflow: "hidden" }}>
                <img
                  src={img}
                  alt={title}
                  style={{
                    width: "100%", height: "100%", objectFit: "cover",
                    filter: "grayscale(60%) brightness(0.75)",
                    transition: "transform 0.6s, filter 0.3s",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.transform = "scale(1.05)";
                    (e.currentTarget as HTMLElement).style.filter = "grayscale(20%) brightness(0.65)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.transform = "";
                    (e.currentTarget as HTMLElement).style.filter = "grayscale(60%) brightness(0.75)";
                  }}
                />
              </div>
              <div style={{
                position: "absolute", bottom: 0, left: 0, right: 0,
                padding: "32px 28px",
                background: "linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 100%)",
              }}>
                <div style={{
                  fontSize: "clamp(18px, 2vw, 26px)", fontWeight: 800,
                  textTransform: "uppercase", letterSpacing: 2,
                  color: WHITE, marginBottom: 6,
                }}>
                  {title}
                </div>
                <div style={{ fontSize: 12, letterSpacing: 1, color: "rgba(255,255,255,0.7)" }}>{sub}</div>
                <div style={{ width: 32, height: 2, background: GOLD, marginTop: 14 }} />
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section id="как-работает" style={{ padding: "80px 48px", background: BLACK, color: WHITE }}>
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <div style={{ width: 48, height: 2, background: GOLD, marginBottom: 24 }} />
          <h2 style={{
            fontSize: "clamp(28px, 4vw, 52px)", fontWeight: 800,
            textTransform: "uppercase", letterSpacing: 2, marginBottom: 60,
          }}>
            Как это работает
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 32 }}>
            {[
              { n: "01", title: "Заполни анкету", desc: "Параметры, город, категория — 2 минуты в Telegram Mini App" },
              { n: "02", title: "Мы мониторим", desc: "200+ каналов и агентств — круглосуточно, без выходных" },
              { n: "03", title: "Только нужное", desc: "ИИ фильтрует и присылает только подходящие предложения" },
              { n: "04", title: "Быстрый отклик", desc: "Готовый текст отклика в один клик — по твоей анкете" },
            ].map(({ n, title, desc }) => (
              <div key={n}>
                <div style={{ fontSize: 40, fontWeight: 800, color: GOLD, lineHeight: 1, marginBottom: 20 }}>{n}</div>
                <div style={{ fontSize: 13, letterSpacing: 1, textTransform: "uppercase", fontWeight: 700, marginBottom: 12 }}>{title}</div>
                <div style={{ fontSize: 13, lineHeight: 1.7, color: "rgba(255,255,255,0.55)" }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section style={{
        padding: "100px 48px", background: LIGHT, textAlign: "center",
      }}>
        <div style={{ width: 48, height: 2, background: GOLD, margin: "0 auto 28px" }} />
        <h2 style={{
          fontSize: "clamp(32px, 5vw, 60px)", fontWeight: 800,
          textTransform: "uppercase", letterSpacing: 2, marginBottom: 20,
        }}>
          Начни сейчас
        </h2>
        <p style={{ fontSize: 15, color: "#666", marginBottom: 48, maxWidth: 500, margin: "0 auto 48px" }}>
          Запусти бота, заполни анкету за 2 минуты и получай кастинги раньше всех.
        </p>
        <a
          href={APP_URL}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-flex", alignItems: "center", gap: 12,
            background: BLACK, color: WHITE,
            padding: "20px 52px", textDecoration: "none",
            fontSize: 12, letterSpacing: 3, fontWeight: 700, textTransform: "uppercase",
            transition: "background 0.2s",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = GOLD; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = BLACK; }}
        >
          <TgIcon /> Открыть в Telegram
        </a>
      </section>

      {/* ── FOOTER ── */}
      <footer style={{ background: BLACK, color: WHITE, padding: "64px 48px 32px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "200px 1fr 1fr 200px", gap: 48, marginBottom: 48 }}>
          {/* Logo */}
          <div>
            <div style={{
              width: 50, height: 50, background: WHITE,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center",
              marginBottom: 16,
            }}>
              <span style={{ color: BLACK, fontWeight: 800, fontSize: 13, letterSpacing: 1 }}>MODEL</span>
              <span style={{ color: GOLD, fontWeight: 400, fontSize: 9, letterSpacing: 2 }}>PROMO</span>
            </div>
            <div style={{ fontSize: 11, letterSpacing: 3, color: "rgba(255,255,255,0.4)", textTransform: "uppercase" }}>
              Model Promo Agency
            </div>
          </div>

          {/* Nav 1 */}
          <div>
            <div style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", color: GOLD, marginBottom: 20 }}>Категории</div>
            {["Актёры и модели", "Event-персонал", "Разнорабочие", "Администрирование"].map((l) => (
              <div key={l} style={{ marginBottom: 10 }}>
                <a href={APP_URL} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", textDecoration: "none", transition: "color 0.2s" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = WHITE; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.6)"; }}
                >
                  {l}
                </a>
              </div>
            ))}
          </div>

          {/* Nav 2 */}
          <div>
            <div style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", color: GOLD, marginBottom: 20 }}>Навигация</div>
            {["Как работает", "О нас", "Telegram-бот"].map((l) => (
              <div key={l} style={{ marginBottom: 10 }}>
                <a href={l === "Telegram-бот" ? BOT_URL : "#"} target={l === "Telegram-бот" ? "_blank" : undefined}
                  rel="noopener noreferrer"
                  style={{ fontSize: 13, color: "rgba(255,255,255,0.6)", textDecoration: "none", transition: "color 0.2s" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = WHITE; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.6)"; }}
                >
                  {l}
                </a>
              </div>
            ))}
          </div>

          {/* Contacts */}
          <div>
            <div style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", color: GOLD, marginBottom: 20 }}>Контакты</div>
            <a
              href={BOT_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{ display: "flex", alignItems: "center", gap: 8, color: "rgba(255,255,255,0.6)", textDecoration: "none", fontSize: 13, marginBottom: 12, transition: "color 0.2s" }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = WHITE; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.6)"; }}
            >
              <TgIcon size={15} /> @{BOT_USERNAME}
            </a>
          </div>
        </div>

        {/* Bottom bar */}
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: 24, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", letterSpacing: 1 }}>
            © {new Date().getFullYear()} Model Promo Agency. Все права защищены. &nbsp;·&nbsp; ИП Рябов Семён Кириллович
          </div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.3)", letterSpacing: 1 }}>
            16+
          </div>
        </div>
      </footer>
    </div>
  );
}

function TgIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.018 9.51c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.881.711z" />
    </svg>
  );
}
