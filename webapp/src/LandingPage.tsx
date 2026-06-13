import { useEffect, useState } from "react";

const BOT_USERNAME = "ModelProAgency_bot";
const APP_URL = `https://t.me/${BOT_USERNAME}/app`;
const BOT_URL = `https://t.me/${BOT_USERNAME}`;

const GOLD = "#c9a96e";
const BLACK = "#080808";
const WHITE = "#ffffff";
const CREAM = "#f4f2ee";

const SERIF = "'Playfair Display', 'Cormorant Garamond', Georgia, serif";
const SANS  = "'Inter', 'Segoe UI', Arial, sans-serif";

// ── Unsplash photos ──────────────────────────────────────────────────────────
const P = {
  h1:      "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=1400&q=90",
  h2:      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1400&q=90",
  h3:      "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=1400&q=90",
  girl1:   "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=900&q=85",
  girl2:   "https://images.unsplash.com/photo-1524638431109-93d95c968f03?w=900&q=85",
  man1:    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=900&q=85",
  man2:    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=900&q=85",
  event1:  "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=900&q=85",
  event2:  "https://images.unsplash.com/photo-1519671282429-b44660ead0a7?w=900&q=85",
  studio:  "https://images.unsplash.com/photo-1581044777550-4cfa60707c03?w=900&q=85",
  shoot1:  "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=900&q=85",
  shoot2:  "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=900&q=85",
};

// Mixkit fashion videos (free, no attribution required)
const VIDEOS = {
  hero: "https://assets.mixkit.co/videos/preview/mixkit-portrait-of-a-fashion-woman-with-silver-makeup-39875-large.mp4",
  mid:  "https://assets.mixkit.co/videos/preview/mixkit-fashion-model-posing-in-studio-41534-large.mp4",
};

// ── Inject CSS animations ────────────────────────────────────────────────────
function useGlobalStyles() {
  useEffect(() => {
    const el = document.createElement("style");
    el.textContent = `
      *, *::before, *::after { box-sizing: border-box; }
      html { scroll-behavior: smooth; }

      @keyframes marquee {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-50%); }
      }
      @keyframes marqueeRev {
        0%   { transform: translateX(-50%); }
        100% { transform: translateX(0); }
      }
      @keyframes heroFade {
        0%, 28%  { opacity: 1; }
        33%, 95% { opacity: 0; }
        100%     { opacity: 1; }
      }
      @keyframes fadeUp {
        from { opacity: 0; transform: translateY(40px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      @keyframes lineGrow {
        from { width: 0; }
        to   { width: 100%; }
      }
      @keyframes pulseGold {
        0%, 100% { opacity: 0.6; }
        50%      { opacity: 1; }
      }

      .hero-img {
        position: absolute; inset: 0;
        width: 100%; height: 100%; object-fit: cover;
        filter: brightness(0.22) grayscale(20%);
        opacity: 0;
        animation: heroFade 18s infinite;
      }
      .hero-img:nth-child(1) { animation-delay: 0s; }
      .hero-img:nth-child(2) { animation-delay: 6s; }
      .hero-img:nth-child(3) { animation-delay: 12s; }

      .hero-video {
        position: absolute; inset: 0;
        width: 100%; height: 100%; object-fit: cover;
        filter: brightness(0.22) grayscale(30%);
      }

      .marquee-track {
        display: flex;
        width: max-content;
        animation: marquee 28s linear infinite;
      }
      .marquee-track-rev {
        display: flex;
        width: max-content;
        animation: marqueeRev 24s linear infinite;
      }
      .marquee-track:hover,
      .marquee-track-rev:hover { animation-play-state: paused; }

      .nav-link {
        background: none; border: none; cursor: pointer; padding: 0;
        font-family: ${SANS};
        font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
        font-weight: 500; transition: color 0.25s;
        position: relative;
      }
      .nav-link::after {
        content: ''; position: absolute; bottom: -4px; left: 0;
        height: 1px; width: 0; background: ${GOLD};
        transition: width 0.3s;
      }
      .nav-link:hover::after { width: 100%; }

      .photo-card { position: relative; overflow: hidden; }
      .photo-card img {
        display: block; width: 100%; height: 100%; object-fit: cover;
        transition: transform 0.7s cubic-bezier(0.25,0.46,0.45,0.94),
                    filter 0.5s;
        filter: grayscale(40%) brightness(0.8);
      }
      .photo-card:hover img {
        transform: scale(1.06);
        filter: grayscale(10%) brightness(0.75);
      }
      .photo-card .overlay {
        position: absolute; bottom: 0; left: 0; right: 0;
        padding: 48px 28px 28px;
        background: linear-gradient(to top, rgba(0,0,0,0.8) 0%, transparent 100%);
      }
      .photo-card .gold-bar {
        height: 2px; background: ${GOLD}; width: 24px;
        margin-top: 10px; transition: width 0.35s;
      }
      .photo-card:hover .gold-bar { width: 52px; }

      .gold-btn {
        display: inline-flex; align-items: center; gap: 10px;
        background: ${GOLD}; color: ${BLACK};
        padding: 16px 40px; text-decoration: none;
        font-size: 11px; letter-spacing: 3px; font-weight: 700;
        text-transform: uppercase; font-family: ${SANS};
        transition: background 0.2s, transform 0.15s;
        border: none; cursor: pointer;
      }
      .gold-btn:hover { background: #b8924f; transform: translateY(-1px); }

      .outline-btn {
        display: inline-flex; align-items: center; gap: 10px;
        background: transparent;
        border: 1px solid rgba(255,255,255,0.25);
        color: rgba(255,255,255,0.7);
        padding: 16px 36px; text-decoration: none;
        font-size: 11px; letter-spacing: 3px; font-weight: 500;
        text-transform: uppercase; font-family: ${SANS};
        transition: border-color 0.25s, color 0.25s, transform 0.15s;
      }
      .outline-btn:hover {
        border-color: ${GOLD}; color: ${GOLD};
        transform: translateY(-1px);
      }

      .outline-btn-dark {
        display: inline-flex; align-items: center; gap: 10px;
        background: transparent;
        border: 1px solid rgba(0,0,0,0.25);
        color: rgba(0,0,0,0.6);
        padding: 16px 36px; text-decoration: none;
        font-size: 11px; letter-spacing: 3px; font-weight: 500;
        text-transform: uppercase; font-family: ${SANS};
        transition: border-color 0.25s, color 0.25s;
      }
      .outline-btn-dark:hover { border-color: ${GOLD}; color: ${GOLD}; }

      .feat-item {
        border-top: 1px solid rgba(255,255,255,0.08);
        padding: 40px 0;
        display: flex; gap: 32px;
        transition: background 0.2s;
      }

      .section-animate {
        opacity: 0;
        transform: translateY(32px);
        transition: opacity 0.8s ease, transform 0.8s ease;
      }
      .section-animate.visible {
        opacity: 1;
        transform: translateY(0);
      }
    `;
    document.head.appendChild(el);
    return () => document.head.removeChild(el);
  }, []);
}

// ── Intersection observer for scroll animations ───────────────────────────────
function useScrollReveal() {
  useEffect(() => {
    const els = document.querySelectorAll(".section-animate");
    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("visible"); }),
      { threshold: 0.12 }
    );
    els.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);
}

// ── Scroll Y ─────────────────────────────────────────────────────────────────
function useScrollY() {
  const [y, setY] = useState(0);
  useEffect(() => {
    const fn = () => setY(window.scrollY);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);
  return y;
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

// ── Marquee Strip ─────────────────────────────────────────────────────────────
function Marquee({
  items, size = 80, gap = 80, color = WHITE, bg = BLACK, reverse = false, outline = false,
}: {
  items: string[]; size?: number; gap?: number;
  color?: string; bg?: string; reverse?: boolean; outline?: boolean;
}) {
  const text = items.join(`  ·  `);
  const chunk = (
    <span style={{
      fontSize: size, fontWeight: 900, fontFamily: SERIF,
      letterSpacing: outline ? 8 : 2,
      color: outline ? "transparent" : color,
      WebkitTextStroke: outline ? `2px ${color}` : undefined,
      textTransform: "uppercase",
      whiteSpace: "nowrap",
      paddingRight: gap,
      lineHeight: 1.1,
      userSelect: "none",
    }}>
      {text}
    </span>
  );
  return (
    <div style={{ background: bg, overflow: "hidden", padding: "0" }}>
      <div className={reverse ? "marquee-track-rev" : "marquee-track"}>
        {chunk}{chunk}{chunk}{chunk}
      </div>
    </div>
  );
}

// ── Label chip ────────────────────────────────────────────────────────────────
function Label({ children, light }: { children: React.ReactNode; light?: boolean }) {
  return (
    <div style={{
      fontSize: 10, letterSpacing: 5, textTransform: "uppercase", marginBottom: 20,
      color: light ? "rgba(255,255,255,0.35)" : "rgba(0,0,0,0.35)",
      fontFamily: SANS,
    }}>
      — {children}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
export function LandingPage() {
  useGlobalStyles();
  const scrollY = useScrollY();

  useEffect(() => {
    const timer = setTimeout(() => {
      const els = document.querySelectorAll(".section-animate");
      const observer = new IntersectionObserver(
        (entries) => entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("visible"); }),
        { threshold: 0.1 }
      );
      els.forEach((el) => observer.observe(el));
      return () => observer.disconnect();
    }, 200);
    return () => clearTimeout(timer);
  }, []);

  const navSolid = scrollY > 80;

  return (
    <div style={{ background: WHITE, fontFamily: SANS, color: BLACK, minHeight: "100vh", overflowX: "hidden" }}>

      {/* ══ NAV ══════════════════════════════════════════════════════════════ */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 200,
        height: 72,
        background: navSolid ? "rgba(255,255,255,0.97)" : "transparent",
        borderBottom: navSolid ? "1px solid rgba(0,0,0,0.07)" : "none",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 52px",
        transition: "background 0.5s, box-shadow 0.5s",
        boxShadow: navSolid ? "0 2px 24px rgba(0,0,0,0.06)" : "none",
      }}>
        {/* Logo */}
        <div onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          style={{ display: "flex", alignItems: "center", gap: 14, cursor: "pointer" }}>
          <div style={{
            width: 48, height: 48,
            border: `1px solid ${navSolid ? BLACK : "rgba(255,255,255,0.4)"}`,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            transition: "border-color 0.5s",
          }}>
            <span style={{
              fontFamily: SERIF, fontWeight: 700, fontSize: 14, letterSpacing: 1,
              color: navSolid ? BLACK : WHITE, transition: "color 0.5s",
            }}>MP</span>
            <span style={{ fontSize: 7, letterSpacing: 3, color: GOLD }}>AGENCY</span>
          </div>
          <span style={{
            fontFamily: SERIF, fontWeight: 700, fontSize: 15, letterSpacing: 2,
            textTransform: "uppercase",
            color: navSolid ? BLACK : WHITE, transition: "color 0.5s",
          }}>Model Pro</span>
        </div>

        {/* Nav links */}
        <div style={{ display: "flex", gap: 36, alignItems: "center" }}>
          {[
            { label: "Кастинги",   id: "castings" },
            { label: "Категории",  id: "categories" },
            { label: "Как работает", id: "how" },
          ].map(({ label, id }) => (
            <button key={id} className="nav-link"
              onClick={() => scrollTo(id)}
              style={{ color: navSolid ? "rgba(0,0,0,0.55)" : "rgba(255,255,255,0.65)" }}>
              {label}
            </button>
          ))}
          <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="gold-btn"
            style={{ padding: "11px 28px" }}>
            <TgIcon /> Открыть бота
          </a>
        </div>
      </nav>

      {/* ══ HERO — video + crossfade photos + framed logo ══════════════════ */}
      <section style={{ minHeight: "100vh", position: "relative", overflow: "hidden", display: "flex", alignItems: "center", justifyContent: "center" }}>
        {/* Video bg — fallback to crossfade photos if video fails */}
        <video className="hero-video" autoPlay muted loop playsInline
          poster={P.h1}
          onError={(e) => { (e.currentTarget as HTMLVideoElement).style.display = "none"; }}>
          <source src={VIDEOS.hero} type="video/mp4" />
        </video>
        {/* Crossfade photo fallback */}
        <img className="hero-img" src={P.h1} alt="" />
        <img className="hero-img" src={P.h2} alt="" />
        <img className="hero-img" src={P.h3} alt="" />
        {/* Vignette */}
        <div style={{
          position: "absolute", inset: 0,
          background: "radial-gradient(ellipse at 50% 60%, transparent 20%, rgba(0,0,0,0.7) 100%)",
          pointerEvents: "none",
        }} />

        {/* Content */}
        <div style={{ position: "relative", textAlign: "center", padding: "0 24px" }}>
          <div style={{
            fontSize: 11, letterSpacing: 6, textTransform: "uppercase",
            color: "rgba(255,255,255,0.35)", marginBottom: 48,
            fontFamily: SANS,
            animation: "fadeUp 1.2s ease forwards",
          }}>
            Telegram · Mini App
          </div>

          {/* Frame */}
          <div style={{ position: "relative", display: "inline-block", padding: "52px 88px" }}>
            {/* Corner accents */}
            {[
              { top: 0, left: 0, borderTop: `2px solid ${GOLD}`, borderLeft: `2px solid ${GOLD}` },
              { top: 0, right: 0, borderTop: `2px solid ${GOLD}`, borderRight: `2px solid ${GOLD}` },
              { bottom: 0, left: 0, borderBottom: `2px solid ${GOLD}`, borderLeft: `2px solid ${GOLD}` },
              { bottom: 0, right: 0, borderBottom: `2px solid ${GOLD}`, borderRight: `2px solid ${GOLD}` },
            ].map((s, i) => (
              <div key={i} style={{ position: "absolute", width: 32, height: 32, ...s }} />
            ))}
            <div style={{ position: "absolute", inset: 0, border: "1px solid rgba(255,255,255,0.1)" }} />

            <h1 style={{
              fontFamily: SERIF, fontWeight: 900,
              fontSize: "clamp(64px, 10vw, 148px)",
              lineHeight: 0.9, letterSpacing: "0.02em",
              textTransform: "uppercase", margin: 0,
              background: `linear-gradient(160deg, #fff 0%, #e8d5a3 40%, ${GOLD} 65%, #fff 100%)`,
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
              animation: "fadeUp 1s 0.3s ease both",
            }}>
              Model<br />Pro
            </h1>
            <div style={{
              fontFamily: SERIF, fontStyle: "italic", fontWeight: 400,
              fontSize: "clamp(16px, 2.5vw, 30px)",
              letterSpacing: "0.5em", textTransform: "uppercase",
              color: "rgba(255,255,255,0.5)", marginTop: 20,
              animation: "fadeUp 1s 0.5s ease both",
            }}>
              Agency
            </div>
          </div>

          <p style={{
            marginTop: 40, fontSize: 13, letterSpacing: 3,
            textTransform: "uppercase", color: "rgba(255,255,255,0.32)",
            fontFamily: SANS,
            animation: "fadeUp 1s 0.7s ease both",
          }}>
            Агрегатор кастингов · 200+ Telegram-каналов
          </p>

          <div style={{
            display: "flex", gap: 16, marginTop: 48, justifyContent: "center", flexWrap: "wrap",
            animation: "fadeUp 1s 0.9s ease both",
          }}>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="gold-btn">
              <TgIcon /> Открыть Mini App
            </a>
            <a href={BOT_URL} target="_blank" rel="noopener noreferrer" className="outline-btn">
              Узнать больше
            </a>
          </div>

          {/* Scroll cue */}
          <div style={{
            marginTop: 80, display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
            animation: "fadeUp 1s 1.2s ease both",
          }}>
            <span style={{ fontSize: 9, letterSpacing: 4, color: "rgba(255,255,255,0.2)", fontFamily: SANS }}>SCROLL</span>
            <div style={{ width: 1, height: 56, background: `linear-gradient(to bottom, ${GOLD}, transparent)` }} />
          </div>
        </div>
      </section>

      {/* ══ MARQUEE 1 — чёрный, большие буквы ════════════════════════════════ */}
      <Marquee
        items={["Актёры и Модели", "Event-персонал", "Кастинги", "Хелперы", "Реклама"]}
        size={72} bg={BLACK} color={WHITE}
      />

      {/* ══ TAGLINE — золотая полоса ══════════════════════════════════════════ */}
      <div style={{
        background: GOLD, padding: "15px 52px",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 40, flexWrap: "wrap",
      }}>
        {["Кастинги · Съёмки · Реклама", "Event · Хостес · Промо", "Актёры и Модели"].map((t, i, arr) => (
          <span key={t} style={{ display: "flex", alignItems: "center", gap: 40 }}>
            <span style={{ fontSize: 11, letterSpacing: 3, textTransform: "uppercase", fontWeight: 600, color: BLACK, fontFamily: SANS }}>{t}</span>
            {i < arr.length - 1 && <span style={{ width: 4, height: 4, borderRadius: "50%", background: "rgba(0,0,0,0.2)", display: "inline-block" }} />}
          </span>
        ))}
      </div>

      {/* ══ EDITORIAL GRID ═══════════════════════════════════════════════════ */}
      <section id="castings" style={{ padding: "88px 52px 0" }}>
        <div className="section-animate" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 40 }}>
          <div>
            <Label>Последние публикации</Label>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(32px, 4vw, 56px)", margin: 0, lineHeight: 1 }}>
              Кастинги<br /><em style={{ fontWeight: 400, color: "rgba(0,0,0,0.45)" }}>сегодня</em>
            </h2>
          </div>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 3, fontFamily: SANS }}>
            Смотреть все →
          </a>
        </div>

        <div className="section-animate" style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1fr", gridTemplateRows: "1fr 1fr", gap: 6 }}>
          {/* Large left */}
          <div className="photo-card" style={{ gridRow: "1 / 3", aspectRatio: "3/4" }}>
            <img src={P.girl1} alt="Актрисы" />
            <div className="overlay">
              <div style={{ fontFamily: SERIF, fontSize: 22, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>Актрисы и модели</div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", letterSpacing: 1, marginTop: 4 }}>Кино · Реклама · Съёмки</div>
              <div className="gold-bar" />
            </div>
          </div>
          {/* 4 small */}
          {[
            { src: P.shoot2, t: "Реклама",    s: "Москва" },
            { src: P.event1, t: "Event",       s: "Хостес · Промо" },
            { src: P.man1,   t: "Мужское",     s: "Fashion" },
            { src: P.shoot1, t: "Съёмки",      s: "Студия" },
          ].map(({ src, t, s }) => (
            <a key={t} href={APP_URL} target="_blank" rel="noopener noreferrer"
              className="photo-card" style={{ textDecoration: "none", aspectRatio: "4/3" }}>
              <img src={src} alt={t} />
              <div className="overlay">
                <div style={{ fontFamily: SERIF, fontSize: 16, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>{t}</div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.45)", letterSpacing: 1, marginTop: 2 }}>{s}</div>
                <div className="gold-bar" />
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* ══ MARQUEE 2 — outline на светлом ════════════════════════════════════ */}
      <div style={{ paddingTop: 72, background: WHITE }}>
        <Marquee
          items={["Стать участником", "Получать кастинги", "Подать анкету"]}
          size={68} bg={WHITE} color={BLACK} outline reverse
        />
      </div>

      {/* ══ SPLIT: СТАТЬ УЧАСТНИКОМ ══════════════════════════════════════════ */}
      <section style={{ display: "grid", gridTemplateColumns: "55% 45%", marginTop: 6 }}>
        <div className="photo-card" style={{ minHeight: 600 }}>
          <img src={P.studio} alt="Студия" style={{ height: "100%" }} />
        </div>
        <div style={{ background: CREAM, padding: "80px 72px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div className="section-animate">
            <Label>Telegram Mini App</Label>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(32px, 3.5vw, 52px)", lineHeight: 1.05, textTransform: "uppercase", marginBottom: 28 }}>
              Стать<br />участником
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.9, color: "#555", marginBottom: 36, maxWidth: 360, fontFamily: SANS }}>
              Заполни анкету в нашем Telegram Mini App — укажи категорию, параметры и город.
              Бот сразу начнёт присылать только подходящие кастинги из&nbsp;200+ каналов.
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="gold-btn">
              <TgIcon /> Заполнить анкету
            </a>
            <div style={{ marginTop: 44, display: "flex", flexDirection: "column", gap: 16 }}>
              {["Актёры и модели", "Event-персонал", "Хелперы и разнорабочие", "Административный персонал"].map((item) => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: SANS }}>
                  <div style={{ width: 20, height: 1, background: GOLD, flexShrink: 0 }} />
                  <span style={{ fontSize: 13, color: "#444", letterSpacing: 0.3 }}>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══ STATS ════════════════════════════════════════════════════════════ */}
      <div style={{ background: BLACK, padding: "64px 52px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", maxWidth: 1100, margin: "0 auto", textAlign: "center" }}>
          {[
            ["200+", "Telegram-каналов"],
            ["4",    "Направления"],
            ["24/7", "Мониторинг"],
            ["2 мин","Заполнить анкету"],
          ].map(([n, l], i, arr) => (
            <div key={l} className="section-animate" style={{
              padding: "0 32px",
              borderRight: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.07)" : "none",
            }}>
              <div style={{
                fontFamily: SERIF, fontSize: "clamp(36px, 4.5vw, 60px)", fontWeight: 900, lineHeight: 1,
                background: `linear-gradient(135deg, ${WHITE} 0%, ${GOLD} 100%)`,
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
              }}>{n}</div>
              <div style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginTop: 16, fontFamily: SANS }}>{l}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ══ VIDEO / DARK BANNER — "АНКЕТА" ════════════════════════════════════ */}
      <div style={{ position: "relative", overflow: "hidden", height: 460 }}>
        <video
          autoPlay muted loop playsInline
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", filter: "brightness(0.22) grayscale(40%)" }}
          onError={(e) => {
            (e.currentTarget as HTMLVideoElement).style.display = "none";
            const img = document.createElement("img");
            img.src = P.event2;
            img.style.cssText = "position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:brightness(0.22) grayscale(40%)";
            e.currentTarget.parentElement?.appendChild(img);
          }}
        >
          <source src={VIDEOS.mid} type="video/mp4" />
        </video>
        <img src={P.event2} alt="" style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          objectFit: "cover", filter: "brightness(0.22) grayscale(40%)",
        }} />
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          textAlign: "center",
        }}>
          <h2 style={{
            fontFamily: SERIF, fontWeight: 900,
            fontSize: "clamp(52px, 10vw, 140px)",
            textTransform: "uppercase", letterSpacing: "0.12em",
            color: WHITE, margin: 0, lineHeight: 1,
            animation: "pulseGold 4s ease-in-out infinite",
          }}>
            Анкета
          </h2>
          <div style={{ width: 80, height: 2, background: GOLD, margin: "28px auto" }} />
          <p style={{ fontSize: 13, letterSpacing: 3, color: "rgba(255,255,255,0.4)", marginBottom: 44, fontFamily: SANS }}>
            Занимает 2 минуты
          </p>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="gold-btn">
            <TgIcon /> Заполнить в Telegram
          </a>
        </div>
      </div>

      {/* ══ SPLIT reverse: умный агрегатор ═══════════════════════════════════ */}
      <section style={{ display: "grid", gridTemplateColumns: "45% 55%" }}>
        <div style={{ background: WHITE, padding: "80px 72px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div className="section-animate">
            <Label>Технологии</Label>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 3vw, 48px)", lineHeight: 1.05, textTransform: "uppercase", marginBottom: 24 }}>
              Умный<br />агрегатор
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.9, color: "#555", marginBottom: 36, maxWidth: 380, fontFamily: SANS }}>
              ИИ анализирует каждое объявление, сравнивает с твоей анкетой и присылает уведомление раньше всех — только то, что действительно подходит.
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="outline-btn-dark">
              Попробовать →
            </a>
          </div>
        </div>
        <div className="photo-card" style={{ minHeight: 520 }}>
          <img src={P.girl2} alt="Модель" style={{ height: "100%" }} />
        </div>
      </section>

      {/* ══ CATEGORIES ═══════════════════════════════════════════════════════ */}
      <section id="categories" style={{ padding: "88px 52px 0" }}>
        <div className="section-animate" style={{ textAlign: "center", marginBottom: 56 }}>
          <Label>Для кого</Label>
          <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(32px, 4vw, 56px)", margin: 0, lineHeight: 1 }}>
            Категории
          </h2>
        </div>
        <div className="section-animate" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
          {[
            { src: P.girl1,  t: "Актрисы и модели",  s: "Кино · Реклама · Съёмки" },
            { src: P.man2,   t: "Актёры и модели",   s: "Мужское направление" },
            { src: P.event2, t: "Event-персонал",    s: "Хостес · Промо · Event" },
            { src: P.girl2,  t: "Разнорабочие",      s: "Хелперы · Клининг" },
          ].map(({ src, t, s }) => (
            <a key={t} href={APP_URL} target="_blank" rel="noopener noreferrer"
              className="photo-card" style={{ textDecoration: "none", aspectRatio: "2/3" }}>
              <img src={src} alt={t} />
              <div className="overlay">
                <div style={{ fontFamily: SERIF, fontSize: 18, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>{t}</div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.45)", letterSpacing: 1, marginTop: 4 }}>{s}</div>
                <div className="gold-bar" />
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* ══ MARQUEE 3 — HOW IT WORKS separator ═══════════════════════════════ */}
      <div style={{ paddingTop: 88 }}>
        <Marquee
          items={["Как это работает", "Кастинги каждый день", "Первым узнавай"]}
          size={64} bg={BLACK} color={WHITE}
        />
      </div>

      {/* ══ HOW IT WORKS ═════════════════════════════════════════════════════ */}
      <section id="how" style={{ background: BLACK, padding: "88px 52px" }}>
        <div style={{ maxWidth: 1140, margin: "0 auto" }}>
          <div className="section-animate" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 72, flexWrap: "wrap", gap: 24 }}>
            <div>
              <Label light>Инструкция</Label>
              <h2 style={{
                fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(32px, 4.5vw, 60px)",
                textTransform: "uppercase", color: WHITE, margin: 0, lineHeight: 1,
              }}>
                Как это<br /><em style={{ fontWeight: 400, color: GOLD }}>работает</em>
              </h2>
            </div>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="gold-btn">
              <TgIcon /> Начать сейчас
            </a>
          </div>

          <div className="section-animate" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2 }}>
            {[
              { n: "01", t: "Открой бота",      d: "Нажми кнопку ниже или найди @ModelProAgency_bot в Telegram и запусти командой /start." },
              { n: "02", t: "Заполни анкету",   d: "В Mini App укажи категорию, параметры, город и предпочтения. Занимает ровно 2 минуты." },
              { n: "03", t: "Получай кастинги", d: "Бот круглосуточно мониторит 200+ каналов и присылает только подходящие предложения." },
              { n: "04", t: "Отправь отклик",   d: "Кнопка «Сгенерировать отклик» готовит текст по твоей анкете — копируй и отправляй." },
            ].map(({ n, t, d }, i, arr) => (
              <div key={n} style={{
                padding: "44px 36px",
                background: "rgba(255,255,255,0.025)",
                borderRight: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none",
              }}>
                <div style={{ fontFamily: SERIF, fontSize: 56, fontWeight: 900, color: GOLD, opacity: 0.7, lineHeight: 1, marginBottom: 28 }}>{n}</div>
                <div style={{ fontSize: 12, letterSpacing: 2, textTransform: "uppercase", fontWeight: 700, color: WHITE, marginBottom: 16, fontFamily: SANS }}>{t}</div>
                <div style={{ fontSize: 13, lineHeight: 1.8, color: "rgba(255,255,255,0.4)", fontFamily: SANS }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FEATURES — numbered list, dark ═══════════════════════════════════ */}
      <section style={{ background: "#111", padding: "88px 52px" }}>
        <div style={{ maxWidth: 1140, margin: "0 auto" }}>
          <div className="section-animate" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 72, flexWrap: "wrap", gap: 24 }}>
            <div>
              <Label light>Возможности</Label>
              <h2 style={{
                fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 4vw, 52px)",
                textTransform: "uppercase", margin: 0, lineHeight: 1,
                background: `linear-gradient(135deg, ${WHITE} 0%, ${GOLD} 100%)`,
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
              }}>
                Что внутри<br />бота
              </h2>
            </div>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 2, fontFamily: SANS }}>
              Попробовать →
            </a>
          </div>

          <div className="section-animate" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 80px" }}>
            {[
              { n: "01", t: "Умная фильтрация",       d: "ИИ анализирует каждый кастинг и сравнивает с твоими параметрами — рост, возраст, тип внешности, город." },
              { n: "02", t: "Избранное",               d: "Сохраняй лучшие предложения одним нажатием, чтобы вернуться к ним позже." },
              { n: "03", t: "Чёрный список",           d: "Добавляй слова-исключения — бот перестанет присылать нежелательные объявления." },
              { n: "04", t: "Готовый отклик",          d: "Одна кнопка — персональный текст отклика по данным твоей анкеты готов к отправке." },
              { n: "05", t: "Дайджест",                d: "Не хочешь уведомления в моменте? /review покажет все новинки одним списком." },
              { n: "06", t: "Мгновенные уведомления",  d: "Кастинг появился в канале — ты узнаёшь первым. Бот работает круглосуточно." },
            ].map(({ n, t, d }) => (
              <div key={n} className="feat-item">
                <div style={{ fontFamily: SERIF, fontSize: 44, fontWeight: 900, color: GOLD, opacity: 0.5, lineHeight: 1, flexShrink: 0 }}>{n}</div>
                <div>
                  <div style={{ fontSize: 12, letterSpacing: 2, textTransform: "uppercase", fontWeight: 700, color: WHITE, marginBottom: 14, fontFamily: SANS }}>{t}</div>
                  <div style={{ fontSize: 14, lineHeight: 1.8, color: "rgba(255,255,255,0.4)", fontFamily: SANS }}>{d}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ WIDE PHOTO CTA — "НАЧНИ ЗАРАБАТЫВАТЬ" ═══════════════════════════ */}
      <div style={{ position: "relative", overflow: "hidden", height: 480 }}>
        <img src={P.event1} alt="" style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          objectFit: "cover",
          filter: "brightness(0.28) grayscale(30%)",
          transform: `translateY(${(scrollY - 4000) * 0.1}px)`,
        }} />
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          textAlign: "center",
        }}>
          <div style={{ fontSize: 10, letterSpacing: 5, color: "rgba(255,255,255,0.25)", marginBottom: 28, fontFamily: SANS }}>Model Pro Agency</div>
          <h2 style={{
            fontFamily: SERIF, fontWeight: 900,
            fontSize: "clamp(36px, 7vw, 96px)",
            textTransform: "uppercase", color: WHITE, margin: 0, lineHeight: 1, letterSpacing: 4,
          }}>
            Начни зарабатывать
          </h2>
          <div style={{ width: 64, height: 2, background: GOLD, margin: "32px auto" }} />
          <p style={{ fontSize: 14, letterSpacing: 2, color: "rgba(255,255,255,0.4)", marginBottom: 48, fontFamily: SANS }}>
            Тысячи кастингов каждый день — не пропускай своё
          </p>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="gold-btn">
            <TgIcon /> Открыть в Telegram
          </a>
        </div>
      </div>

      {/* ══ FOOTER ═══════════════════════════════════════════════════════════ */}
      <footer style={{ background: BLACK, color: WHITE, padding: "80px 52px 36px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "230px 1fr 1fr 1fr", gap: 52, marginBottom: 64 }}>
          <div>
            <div style={{
              width: 54, height: 54, border: `1px solid ${GOLD}`,
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", marginBottom: 24,
            }}>
              <span style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 15, letterSpacing: 1, color: WHITE }}>MP</span>
              <span style={{ fontSize: 7, letterSpacing: 3, color: GOLD }}>AGENCY</span>
            </div>
            <div style={{ fontSize: 11, letterSpacing: 1.5, color: "rgba(255,255,255,0.25)", lineHeight: 2, fontFamily: SANS }}>
              Model Promo Agency<br />Telegram Mini App
            </div>
          </div>

          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 28, fontFamily: SANS }}>Категории</div>
            {["Актёры и модели", "Event-персонал", "Разнорабочие", "Администрирование"].map((l) => (
              <div key={l} style={{ marginBottom: 14 }}>
                <a href={APP_URL} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", textDecoration: "none", fontFamily: SANS, transition: "color 0.2s" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = GOLD; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.4)"; }}>
                  {l}
                </a>
              </div>
            ))}
          </div>

          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 28, fontFamily: SANS }}>Telegram</div>
            {[
              { label: "Открыть бота", href: BOT_URL },
              { label: "Mini App",     href: APP_URL },
              { label: "@" + BOT_USERNAME, href: BOT_URL },
            ].map(({ label, href }) => (
              <div key={label} style={{ marginBottom: 14 }}>
                <a href={href} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", textDecoration: "none", fontFamily: SANS, transition: "color 0.2s" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = GOLD; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.4)"; }}>
                  {label}
                </a>
              </div>
            ))}
          </div>

          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 28, fontFamily: SANS }}>Начать</div>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.35)", lineHeight: 1.8, marginBottom: 28, fontFamily: SANS }}>
              Запусти бота и заполни анкету — кастинги придут сами.
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="gold-btn" style={{ padding: "13px 28px" }}>
              <TgIcon /> Открыть
            </a>
          </div>
        </div>

        <div style={{ height: 1, background: "rgba(255,255,255,0.07)", marginBottom: 28 }} />
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.18)", fontFamily: SANS }}>
            © {new Date().getFullYear()} Model Promo Agency. Все права защищены. · ИП Рябов Семён Кириллович
          </div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.18)", fontFamily: SANS }}>16+</div>
        </div>
      </footer>
    </div>
  );
}

function TgIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.018 9.51c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.881.711z" />
    </svg>
  );
}
