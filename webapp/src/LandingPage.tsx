import { useEffect, useState } from "react";

const BOT_USERNAME = "ModelProAgency_bot";
const APP_URL = `https://t.me/${BOT_USERNAME}/app`;
const BOT_URL = `https://t.me/${BOT_USERNAME}`;

const GOLD  = "#c9a96e";
const BLACK = "#111111";
const WHITE = "#ffffff";
const CREAM = "#f4f2ee";

const SERIF = "'Playfair Display', 'Cormorant Garamond', Georgia, serif";
const SANS  = "'Inter', 'Segoe UI', Arial, sans-serif";

// Warm dark→gold gradient — same on hero text and accents everywhere
const GRAD_TEXT = `linear-gradient(145deg, #1a1208 0%, #5c3a1e 45%, ${GOLD} 100%)`;
const GRAD_WARM = `linear-gradient(135deg, #1a1208 0%, #6b3d1e 50%, ${GOLD} 100%)`;

const P = {
  h1:     "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=1400&q=90",
  h2:     "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=1400&q=90",
  h3:     "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=1400&q=90",
  girl1:  "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=900&q=85",
  girl2:  "https://images.unsplash.com/photo-1524638431109-93d95c968f03?w=900&q=85",
  man1:   "https://images.unsplash.com/photo-1488161628813-04466f872be2?w=900&q=85",
  man2:   "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=900&q=85",
  event1: "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=900&q=85",
  event2: "https://images.unsplash.com/photo-1529543544282-ea669407fca3?w=900&q=85",
  studio: "https://images.unsplash.com/photo-1581044777550-4cfa60707c03?w=900&q=85",
  shoot1: "https://images.unsplash.com/photo-1574717024653-61fd2cf4d44d?w=900&q=85",
  shoot2: "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=900&q=85",
};

const CLIP_PHOTOS = [P.h1, P.h2, P.h3, P.studio, P.event1, P.shoot2];

// ── Global styles ─────────────────────────────────────────────────────────────
function useGlobalStyles() {
  useEffect(() => {
    const el = document.createElement("style");
    el.textContent = `
      *, *::before, *::after { box-sizing: border-box; margin: 0; }
      html { scroll-behavior: smooth; }

      @keyframes mq  { from { transform: translateX(0); } to { transform: translateX(-50%); } }
      @keyframes mqR { from { transform: translateX(-50%); } to { transform: translateX(0); } }

      @keyframes fadeUp {
        from { opacity: 0; transform: translateY(36px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      @keyframes blobPulse {
        0%,100% { transform: scale(1)   rotate(0deg); }
        50%      { transform: scale(1.08) rotate(3deg); }
      }
      @keyframes heroFade {
        0%,28%  { opacity:1; }
        33%,95% { opacity:0; }
        100%    { opacity:1; }
      }
      @keyframes clipFadeOut {
        from { opacity: 1; }
        to   { opacity: 0; }
      }

      .mq-track  { display:flex; width:max-content; animation: mq  30s linear infinite; }
      .mq-trackR { display:flex; width:max-content; animation: mqR 26s linear infinite; }
      .mq-track:hover, .mq-trackR:hover { animation-play-state: paused; }

      .photo-card { position:relative; overflow:hidden; display:block; }
      .photo-card img {
        display:block; width:100%; height:100%; object-fit:cover;
        filter:grayscale(35%) brightness(0.82);
        transition: transform .7s cubic-bezier(.25,.46,.45,.94), filter .45s;
      }
      .photo-card:hover img { transform:scale(1.055); filter:grayscale(0%) brightness(0.78); }
      .photo-card .ov {
        position:absolute; bottom:0; left:0; right:0;
        padding:48px 24px 24px;
        background:linear-gradient(to top,rgba(0,0,0,.78) 0%,transparent 100%);
      }
      .photo-card .bar {
        height:2px; background:${GOLD}; width:22px; margin-top:10px;
        transition:width .32s;
      }
      .photo-card:hover .bar { width:50px; }

      .reveal {
        opacity:0; transform:translateY(32px);
        transition:opacity .75s ease, transform .75s ease;
      }
      .reveal.vis { opacity:1; transform:none; }

      a.pill {
        display:inline-flex; align-items:center; gap:10px;
        border:1.5px solid ${GOLD}; color:${BLACK};
        padding:14px 36px; text-decoration:none; border-radius:100px;
        font-size:11px; letter-spacing:2.5px; font-weight:600; text-transform:uppercase;
        font-family:${SANS}; background:${GOLD};
        transition:background .2s, color .2s, transform .15s;
      }
      a.pill:hover { background:transparent; color:${GOLD}; transform:translateY(-1px); }

      a.pill-outline {
        display:inline-flex; align-items:center; gap:10px;
        border:1.5px solid rgba(255,255,255,.3); color:rgba(255,255,255,.75);
        padding:14px 36px; text-decoration:none; border-radius:100px;
        font-size:11px; letter-spacing:2.5px; font-weight:600; text-transform:uppercase;
        font-family:${SANS}; background:transparent;
        transition:border-color .2s, color .2s;
      }
      a.pill-outline:hover { border-color:${GOLD}; color:${GOLD}; }

      a.pill-dark {
        display:inline-flex; align-items:center; gap:10px;
        border:1.5px solid rgba(0,0,0,.2); color:rgba(0,0,0,.6);
        padding:14px 36px; text-decoration:none; border-radius:100px;
        font-size:11px; letter-spacing:2.5px; font-weight:600; text-transform:uppercase;
        font-family:${SANS}; background:transparent;
        transition:border-color .2s, color .2s;
      }
      a.pill-dark:hover { border-color:${GOLD}; color:${GOLD}; }

      .nav-btn {
        background:none; border:none; cursor:pointer; padding:0;
        font-size:11px; letter-spacing:2px; text-transform:uppercase; font-weight:500;
        font-family:${SANS}; color:rgba(0,0,0,.5);
        transition:color .2s;
      }
      .nav-btn:hover { color:${BLACK}; }

      /* ── Responsive layout ───────────────────────────────────────────────── */
      .lp-nav-links { display:flex; gap:32px; align-items:center; }
      .lp-grid-3col { display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:6px; }
      .lp-split     { display:grid; grid-template-columns:55% 45%; }
      .lp-split-r   { display:grid; grid-template-columns:45% 55%; }
      .lp-grid-4col { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; }
      .lp-how-grid  { display:grid; grid-template-columns:repeat(4,1fr); gap:2px; }
      .lp-feat-grid { display:grid; grid-template-columns:1fr 1fr; gap:0 80px; }
      .lp-foot-grid { display:grid; grid-template-columns:200px 1fr 1fr 1fr; gap:48px; margin-bottom:56px; }

      @media(max-width:768px){
        .lp-nav { padding:0 20px !important; }
        .lp-nav-links { display:none; }

        .lp-section-pad   { padding:48px 20px !important; }
        .lp-section-pad-t { padding:48px 20px 0 !important; }

        .lp-grid-3col { grid-template-columns:1fr !important; }
        .lp-grid-3col > a:first-child { grid-row:auto !important; aspect-ratio:16/9 !important; }

        .lp-split   { grid-template-columns:1fr !important; }
        .lp-split-r { grid-template-columns:1fr !important; }
        .lp-split .photo-card,
        .lp-split-r .photo-card { min-height:260px !important; }
        .lp-split-r .photo-card { order:-1; }
        .lp-split > div   { padding:40px 24px !important; }
        .lp-split-r > div { padding:40px 24px !important; }

        .lp-grid-4col { grid-template-columns:repeat(2,1fr) !important; }

        .lp-how-grid { grid-template-columns:1fr 1fr !important; }
        .lp-how-grid > div {
          border-right:none !important;
          border-bottom:1px solid rgba(255,255,255,.05);
          padding:28px 20px !important;
        }

        .lp-feat-grid { grid-template-columns:1fr !important; gap:0 !important; }

        .lp-foot-grid { grid-template-columns:1fr 1fr !important; gap:24px !important; }

        .lp-hero-sub { flex-direction:column !important; align-items:flex-start !important; }
        .lp-hero-sub-right { display:none; }
      }
    `;
    document.head.appendChild(el);
    return () => { document.head.removeChild(el); };
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

// ── Scroll reveal ─────────────────────────────────────────────────────────────
function useReveal() {
  useEffect(() => {
    const timer = setTimeout(() => {
      const obs = new IntersectionObserver(
        (e) => e.forEach((x) => { if (x.isIntersecting) x.target.classList.add("vis"); }),
        { threshold: 0.1 }
      );
      document.querySelectorAll(".reveal").forEach((el) => obs.observe(el));
      return () => obs.disconnect();
    }, 150);
    return () => clearTimeout(timer);
  }, []);
}

function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

// ── Marquee (single track) ────────────────────────────────────────────────────
function MqTrack({ items, size, color, reverse, italic }: {
  items: string[]; size: number; color: string; reverse?: boolean; italic?: boolean;
}) {
  const text = items.join("   ·   ");
  const chunk = (
    <span style={{
      fontSize: size, fontWeight: 800, fontFamily: SERIF,
      fontStyle: italic ? "italic" : "normal",
      color, whiteSpace: "nowrap", paddingRight: 60,
      letterSpacing: 1, textTransform: "uppercase", lineHeight: 1.2,
      userSelect: "none",
    }}>
      {text}
    </span>
  );
  return (
    <div className={reverse ? "mq-trackR" : "mq-track"}>
      {chunk}{chunk}{chunk}{chunk}
    </div>
  );
}

// ── Label ─────────────────────────────────────────────────────────────────────
function Lbl({ children, light }: { children: React.ReactNode; light?: boolean }) {
  return (
    <div style={{
      fontSize: 10, letterSpacing: 5, textTransform: "uppercase",
      color: light ? "rgba(255,255,255,.32)" : "rgba(0,0,0,.32)",
      fontFamily: SANS, marginBottom: 18,
    }}>
      — {children}
    </div>
  );
}

// ── Footer link ───────────────────────────────────────────────────────────────
function FLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 13 }}>
      <a href={href} target="_blank" rel="noopener noreferrer"
        style={{ fontSize: 13, color: "rgba(255,255,255,.38)", textDecoration: "none", fontFamily: SANS, transition: "color .2s" }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = GOLD; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,.38)"; }}>
        {children}
      </a>
    </div>
  );
}

// ── Clip-text cycling photos ──────────────────────────────────────────────────
function ClipText() {
  const [cur, setCur] = useState(0);
  const [prev, setPrev] = useState<number | null>(null);

  useEffect(() => {
    const id = setInterval(() => {
      setCur((i) => {
        const next = (i + 1) % CLIP_PHOTOS.length;
        setPrev(i);
        return next;
      });
    }, 3600);
    return () => clearInterval(id);
  }, []);

  const base: React.CSSProperties = {
    fontFamily: SERIF, fontWeight: 900,
    fontSize: "clamp(80px, 17vw, 240px)",
    lineHeight: 0.84, textTransform: "uppercase",
    letterSpacing: "-0.02em", margin: 0,
    padding: "60px 5vw 68px",
    backgroundSize: "cover", backgroundPosition: "center 30%",
    WebkitBackgroundClip: "text", backgroundClip: "text",
    WebkitTextFillColor: "transparent", color: "transparent",
    userSelect: "none", position: "absolute", inset: 0,
  };
  const TEXT = (<>Model<br />Pro<br /><em style={{ fontStyle: "italic", fontWeight: 400 }}>Agency</em></>);

  return (
    <section style={{ background: WHITE, position: "relative", overflow: "hidden" }}>
      <div style={{ position: "relative" }}>
        <h1 style={{ ...base, position: "relative", visibility: "hidden" }}>{TEXT}</h1>
        {/* cur — bottom layer, always visible */}
        <h2 aria-hidden style={{ ...base, backgroundImage: `url(${CLIP_PHOTOS[cur]})` }}>{TEXT}</h2>
        {/* prev — top layer, fades out revealing cur beneath */}
        {prev !== null && (
          <h2 aria-hidden
            style={{ ...base, backgroundImage: `url(${CLIP_PHOTOS[prev]})`, animation: "clipFadeOut 0.85s ease forwards" }}
            onAnimationEnd={() => setPrev(null)}
          >{TEXT}</h2>
        )}
        {/* Dots */}
        <div style={{ position: "absolute", bottom: 24, left: "5vw", display: "flex", gap: 6 }}>
          {CLIP_PHOTOS.map((_, i) => (
            <div key={i} onClick={() => setCur(i)} style={{
              width: i === cur ? 22 : 6, height: 6, borderRadius: 3,
              background: i === cur ? GOLD : "rgba(0,0,0,.15)",
              transition: "all .3s", cursor: "pointer",
            }} />
          ))}
        </div>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
export function LandingPage() {
  useGlobalStyles();
  useReveal();
  const scrollY = useScrollY();

  return (
    <div style={{ background: WHITE, fontFamily: SANS, color: BLACK, overflowX: "hidden" }}>

      {/* ══ NAV — minimal, always white ══════════════════════════════════════ */}
      <nav className="lp-nav" style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 200,
        height: 64,
        background: scrollY > 60 ? "rgba(255,255,255,.97)" : WHITE,
        borderBottom: "1px solid rgba(0,0,0,.07)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 48px",
        transition: "box-shadow .3s",
        boxShadow: scrollY > 60 ? "0 2px 20px rgba(0,0,0,.06)" : "none",
      }}>
        <div onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 18, letterSpacing: 1 }}>MP</span>
          <span style={{ fontSize: 10, letterSpacing: 3, color: GOLD, fontWeight: 600, textTransform: "uppercase" }}>Agency</span>
        </div>
        <div className="lp-nav-links">
          {[{ l: "Кастинги", id: "castings" }, { l: "Категории", id: "categories" }, { l: "Как работает", id: "how" }].map(({ l, id }) => (
            <button key={id} className="nav-btn" onClick={() => scrollTo(id)}>{l}</button>
          ))}
          <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill" style={{ padding: "10px 24px" }}>
            <TgIcon /> Открыть бота
          </a>
        </div>
      </nav>

      {/* ══ CLIP-TEXT — фото сквозь буквы, самый первый блок ══════════════ */}
      <div style={{ paddingTop: 64 }}>
        <ClipText />
      </div>

      {/* ══ DIAGONAL MARQUEES — перекрещивающиеся как aroundbrand ═════════════ */}
      <div style={{ position: "relative", height: 220, margin: "0", overflow: "hidden" }}>
        {/* Strip 1 — GOLD, tilted -3° */}
        <div style={{
          position: "absolute", left: "-5%", right: "-5%", top: 18,
          transform: "rotate(-2.8deg)", background: GOLD,
          padding: "16px 0", overflow: "hidden", zIndex: 2,
        }}>
          <MqTrack items={["Кастинги", "Актёры и Модели", "Event", "Хелперы", "Реклама"]} size={28} color={BLACK} />
        </div>
        {/* Strip 2 — BLACK, tilted +3° */}
        <div style={{
          position: "absolute", left: "-5%", right: "-5%", top: 100,
          transform: "rotate(2.8deg)", background: BLACK,
          padding: "16px 0", overflow: "hidden", zIndex: 1,
        }}>
          <MqTrack items={["Telegram", "Mini App", "Model Pro", "Agency", "Casting"]} size={28} color={WHITE} reverse italic />
        </div>
      </div>

      {/* ══ EDITORIAL PHOTO GRID ════════════════════════════════════════════ */}
      <section id="castings" className="lp-section-pad-t" style={{ padding: "80px 48px 0" }}>
        <div className="reveal" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 36 }}>
          <div>
            <Lbl>Последние публикации</Lbl>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 4vw, 52px)", lineHeight: 1 }}>
              Кастинги<br /><em style={{ fontWeight: 400, color: "rgba(0,0,0,.4)", fontSize: "0.75em" }}>сегодня</em>
            </h2>
          </div>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 3, fontFamily: SANS }}>
            Смотреть все →
          </a>
        </div>

        <div className="reveal lp-grid-3col">
          <a href={APP_URL} target="_blank" rel="noopener noreferrer"
            className="photo-card" style={{ gridRow: "1 / 3", aspectRatio: "3/4", textDecoration: "none" }}>
            <img src={P.girl1} alt="Актрисы" />
            <div className="ov">
              <div style={{ fontFamily: SERIF, fontSize: 20, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>Актрисы и модели</div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,.5)", letterSpacing: 1, marginTop: 4 }}>Кино · Реклама · Съёмки</div>
              <div className="bar" />
            </div>
          </a>
          {[
            { src: P.shoot2, t: "Реклама",  s: "Москва" },
            { src: P.event1, t: "Event",    s: "Хостес · Промо" },
            { src: P.man1,   t: "Мужское",  s: "Fashion" },
            { src: P.shoot1, t: "Съёмки",   s: "Студия" },
          ].map(({ src, t, s }) => (
            <a key={t} href={APP_URL} target="_blank" rel="noopener noreferrer"
              className="photo-card" style={{ textDecoration: "none", aspectRatio: "4/3" }}>
              <img src={src} alt={t} />
              <div className="ov">
                <div style={{ fontFamily: SERIF, fontSize: 15, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>{t}</div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,.45)", letterSpacing: 1, marginTop: 2 }}>{s}</div>
                <div className="bar" />
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* ══ SPLIT: СТАТЬ УЧАСТНИКОМ ══════════════════════════════════════════ */}
      <section className="lp-split" style={{ marginTop: 6 }}>
        <a href={APP_URL} target="_blank" rel="noopener noreferrer"
          className="photo-card" style={{ minHeight: 580, textDecoration: "none" }}>
          <img src={P.studio} alt="Студия" style={{ height: "100%" }} />
        </a>
        <div style={{ background: CREAM, padding: "72px 64px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div className="reveal">
            <Lbl>Telegram Mini App</Lbl>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 3vw, 46px)", lineHeight: 1.05, textTransform: "uppercase", marginBottom: 24 }}>
              Стать<br />участником
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.85, color: "#555", marginBottom: 32, maxWidth: 360, fontFamily: SANS }}>
              Заполни анкету в Mini App — укажи категорию, параметры и город.
              Бот начнёт присылать только подходящие кастинги из 200+ каналов.
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill">
              <TgIcon /> Заполнить анкету
            </a>
            <div style={{ marginTop: 36, display: "flex", flexDirection: "column", gap: 14 }}>
              {["Актёры и модели", "Event-персонал", "Хелперы и разнорабочие", "Административный персонал"].map((item) => (
                <div key={item} style={{ display: "flex", alignItems: "center", gap: 12, fontFamily: SANS }}>
                  <div style={{ width: 18, height: 1, background: GOLD, flexShrink: 0 }} />
                  <span style={{ fontSize: 13, color: "#444" }}>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══ SECOND DIAGONAL MARQUEE STRIP ════════════════════════════════════ */}
      <div style={{ position: "relative", height: 100, overflow: "hidden" }}>
        <div style={{
          position: "absolute", left: "-5%", right: "-5%", top: 16,
          transform: "rotate(-1.5deg)", background: "#1a1208",
          padding: "14px 0", overflow: "hidden",
        }}>
          <MqTrack items={["Стать участником", "Получать кастинги", "Подать анкету", "Model Pro Agency"]} size={22} color={GOLD} italic />
        </div>
      </div>

      {/* ══ SPLIT reverse: умный агрегатор ═══════════════════════════════════ */}
      <section className="lp-split-r">
        <div style={{ background: WHITE, padding: "72px 64px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div className="reveal">
            <Lbl>Технологии</Lbl>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 3vw, 46px)", lineHeight: 1.05, textTransform: "uppercase", marginBottom: 24 }}>
              Умный<br />агрегатор
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.85, color: "#555", marginBottom: 32, maxWidth: 360, fontFamily: SANS }}>
              ИИ анализирует каждое объявление, сравнивает с твоей анкетой и присылает уведомление раньше всех — только то, что подходит.
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill-dark">
              Попробовать →
            </a>
          </div>
        </div>
        <a href={APP_URL} target="_blank" rel="noopener noreferrer"
          className="photo-card" style={{ minHeight: 500, textDecoration: "none" }}>
          <img src={P.girl2} alt="Модель" style={{ height: "100%" }} />
        </a>
      </section>

      {/* ══ CATEGORIES ═══════════════════════════════════════════════════════ */}
      <section id="categories" className="lp-section-pad-t" style={{ padding: "80px 48px 0" }}>
        <div className="reveal" style={{ textAlign: "center", marginBottom: 48 }}>
          <Lbl>Для кого</Lbl>
          <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 4vw, 52px)", lineHeight: 1 }}>Категории</h2>
        </div>
        <div className="reveal lp-grid-4col">
          {[
            { src: P.girl1,  t: "Актрисы и модели",  s: "Кино · Реклама · Съёмки" },
            { src: P.man2,   t: "Актёры и модели",   s: "Мужское направление" },
            { src: P.event2, t: "Event-персонал",    s: "Хостес · Промо · Event" },
            { src: P.girl2,  t: "Разнорабочие",      s: "Хелперы · Клининг" },
          ].map(({ src, t, s }) => (
            <a key={t} href={APP_URL} target="_blank" rel="noopener noreferrer"
              className="photo-card" style={{ textDecoration: "none", aspectRatio: "2/3" }}>
              <img src={src} alt={t} />
              <div className="ov">
                <div style={{ fontFamily: SERIF, fontSize: 17, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>{t}</div>
                <div style={{ fontSize: 10, color: "rgba(255,255,255,.45)", letterSpacing: 1, marginTop: 4 }}>{s}</div>
                <div className="bar" />
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* ══ HOW IT WORKS — dark ══════════════════════════════════════════════ */}
      <section id="how" className="lp-section-pad" style={{ background: "#111", padding: "88px 48px", marginTop: 0 }}>
        <div style={{ maxWidth: 1140, margin: "0 auto" }}>
          <div className="reveal" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 64, flexWrap: "wrap", gap: 24 }}>
            <div>
              <Lbl light>Инструкция</Lbl>
              <h2 style={{
                fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(32px, 4.5vw, 60px)",
                textTransform: "uppercase", color: WHITE, lineHeight: 1,
              }}>
                Как это<br /><em style={{ fontWeight: 400, background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>работает</em>
              </h2>
            </div>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill">
              <TgIcon /> Начать сейчас
            </a>
          </div>
          <div className="reveal lp-how-grid">
            {[
              { n: "01", t: "Открой бота",      d: "Найди @ModelProAgency_bot в Telegram и запусти командой /start." },
              { n: "02", t: "Заполни анкету",   d: "В Mini App укажи категорию, параметры, город. Занимает 2 минуты." },
              { n: "03", t: "Получай кастинги", d: "Бот мониторит 200+ каналов и присылает только подходящие предложения." },
              { n: "04", t: "Отправь отклик",   d: "Кнопка «Сгенерировать» готовит текст по твоей анкете — копируй и отправляй." },
            ].map(({ n, t, d }, i, arr) => (
              <div key={n} style={{
                padding: "40px 32px",
                background: "rgba(255,255,255,.025)",
                borderRight: i < arr.length - 1 ? "1px solid rgba(255,255,255,.05)" : "none",
              }}>
                <div style={{
                  fontFamily: SERIF, fontSize: 52, fontWeight: 900, lineHeight: 1, marginBottom: 24,
                  background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
                }}>{n}</div>
                <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", fontWeight: 700, color: WHITE, marginBottom: 14, fontFamily: SANS }}>{t}</div>
                <div style={{ fontSize: 13, lineHeight: 1.8, color: "rgba(255,255,255,.4)", fontFamily: SANS }}>{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FEATURES — numbered, dark ════════════════════════════════════════ */}
      <section className="lp-section-pad" style={{ background: "#0d0d0d", padding: "80px 48px" }}>
        <div style={{ maxWidth: 1140, margin: "0 auto" }}>
          <div className="reveal" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 60, flexWrap: "wrap", gap: 24 }}>
            <div>
              <Lbl light>Возможности</Lbl>
              <h2 style={{
                fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 4vw, 52px)",
                textTransform: "uppercase", lineHeight: 1,
                background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
              }}>
                Что внутри<br />бота
              </h2>
            </div>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 2, fontFamily: SANS }}>
              Попробовать →
            </a>
          </div>
          <div className="reveal lp-feat-grid">
            {[
              { n: "01", t: "Умная фильтрация",      d: "ИИ анализирует кастинг и сравнивает с твоими параметрами — рост, возраст, тип внешности, город." },
              { n: "02", t: "Избранное",              d: "Сохраняй лучшие предложения одним нажатием, чтобы вернуться позже." },
              { n: "03", t: "Чёрный список",          d: "Добавляй слова-исключения — бот перестанет присылать нежелательное." },
              { n: "04", t: "Готовый отклик",         d: "Одна кнопка — и персональный текст отклика сформирован по данным анкеты." },
              { n: "05", t: "Дайджест",               d: "Не хочешь уведомления сразу? /review покажет все новинки одним списком." },
              { n: "06", t: "Уведомления 24/7",       d: "Кастинг появился в канале — ты узнаёшь первым. Без задержек." },
            ].map(({ n, t, d }) => (
              <div key={n} style={{ borderTop: "1px solid rgba(255,255,255,.07)", padding: "36px 0", display: "flex", gap: 28 }}>
                <div style={{
                  fontFamily: SERIF, fontSize: 40, fontWeight: 900, lineHeight: 1, flexShrink: 0,
                  background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
                  opacity: 0.7,
                }}>{n}</div>
                <div>
                  <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", fontWeight: 700, color: WHITE, marginBottom: 12, fontFamily: SANS }}>{t}</div>
                  <div style={{ fontSize: 13, lineHeight: 1.8, color: "rgba(255,255,255,.38)", fontFamily: SANS }}>{d}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ CTA PHOTO BAND ═══════════════════════════════════════════════════ */}
      <div style={{ position: "relative", overflow: "hidden", height: 420, background: BLACK }}>
        <img src={P.event1} alt="" style={{
          position: "absolute", inset: 0, width: "100%", height: "100%",
          objectFit: "cover", filter: "brightness(0.25) grayscale(20%)",
          transform: `translateY(${(scrollY - 3500) * 0.1}px)`,
        }} />
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center",
        }}>
          <h2 style={{
            fontFamily: SERIF, fontWeight: 900,
            fontSize: "clamp(40px, 8vw, 110px)",
            textTransform: "uppercase", color: WHITE, lineHeight: 1, letterSpacing: 4,
          }}>
            Твой кастинг ждёт
          </h2>
          <div style={{ width: 60, height: 2, background: GOLD, margin: "28px auto" }} />
          <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill-outline">
            <TgIcon /> Открыть в Telegram
          </a>
        </div>
      </div>

      {/* ══ FOOTER ═══════════════════════════════════════════════════════════ */}
      <footer className="lp-section-pad" style={{ background: "#0a0a0a", color: WHITE, padding: "72px 48px 32px" }}>
        <div className="lp-foot-grid">
          <div>
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 20, letterSpacing: 1, color: WHITE }}>MP</div>
              <div style={{ fontSize: 9, letterSpacing: 3, color: GOLD, textTransform: "uppercase" }}>Agency</div>
            </div>
            <div style={{ fontSize: 11, letterSpacing: 1, color: "rgba(255,255,255,.25)", lineHeight: 2, fontFamily: SANS }}>
              Model Promo Agency<br />Telegram Mini App
            </div>
          </div>
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24, fontFamily: SANS }}>Категории</div>
            {["Актёры и модели", "Event-персонал", "Разнорабочие", "Администрирование"].map((l) => (
              <FLink key={l} href={APP_URL}>{l}</FLink>
            ))}
          </div>
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24, fontFamily: SANS }}>Telegram</div>
            <FLink href={BOT_URL}>Открыть бота</FLink>
            <FLink href={APP_URL}>Mini App</FLink>
            <FLink href={BOT_URL}>@{BOT_USERNAME}</FLink>
          </div>
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24, fontFamily: SANS }}>Начать</div>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,.3)", lineHeight: 1.8, marginBottom: 24, fontFamily: SANS }}>
              Запусти бота и заполни анкету — кастинги придут сами.
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill" style={{ padding: "12px 24px" }}>
              <TgIcon /> Открыть
            </a>
          </div>
        </div>
        <div style={{ height: 1, background: "rgba(255,255,255,.06)", marginBottom: 24 }} />
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,.16)", fontFamily: SANS }}>
            © {new Date().getFullYear()} Model Promo Agency. Все права защищены. · ИП Рябов Семён Кириллович
          </div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,.16)", fontFamily: SANS }}>16+</div>
        </div>
      </footer>
    </div>
  );
}

function TgIcon({ size = 15 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" style={{ flexShrink: 0 }}>
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.248l-2.018 9.51c-.145.658-.537.818-1.084.508l-3-2.21-1.447 1.394c-.16.16-.295.295-.605.295l.213-3.053 5.56-5.023c.242-.213-.054-.333-.373-.12l-6.871 4.326-2.962-.924c-.643-.204-.657-.643.136-.953l11.57-4.461c.537-.194 1.006.131.881.711z" />
    </svg>
  );
}
