import { useEffect, useState } from "react";
import { useLang } from "./i18n";

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
  h1:     "/photos/h1.jpg",
  h2:     "/photos/h2.jpg",
  h3:     "/photos/h3.jpg",
  girl1:  "/photos/girl1.jpg",
  girl2:  "/photos/girl2.jpg",
  man1:   "/photos/man1.jpg",
  man2:   "/photos/man2.jpg",
  event1: "/photos/event1.jpg",
  event2: "/photos/event2.jpg",
  studio: "/photos/studio.jpg",
  shoot1: "/photos/shoot1.jpg",
  shoot2: "/photos/shoot2.jpg",
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
      @keyframes menuSlideIn {
        from { opacity: 0; transform: translateY(-12px); }
        to   { opacity: 1; transform: translateY(0); }
      }

      .lp-hamburger {
        display:none; flex-direction:column; justify-content:center; gap:5px;
        background:none; border:none; cursor:pointer; padding:8px;
        position:relative; z-index:310;
      }
      .lp-hamburger span {
        display:block; width:22px; height:1.5px; border-radius:2px;
        transition:transform .3s ease, opacity .3s ease, background .3s ease;
      }
      .lp-hamburger.closed span { background:#111; }
      .lp-hamburger.open   span { background:#fff; }
      .lp-hamburger.open span:nth-child(1) { transform:translateY(6.5px) rotate(45deg); }
      .lp-hamburger.open span:nth-child(2) { opacity:0; transform:scaleX(0); }
      .lp-hamburger.open span:nth-child(3) { transform:translateY(-6.5px) rotate(-45deg); }

      .mob-menu-link {
        background:none; border:none; cursor:pointer; width:100%; text-align:center;
        font-family:${SERIF}; font-weight:900; text-transform:uppercase;
        font-size:clamp(34px,10vw,52px); letter-spacing:0.02em;
        color:#fff; padding:22px 0;
        border-bottom:1px solid rgba(255,255,255,.07);
        transition:color .2s;
      }
      .mob-menu-link:hover { color:${GOLD}; }

      .mq-track  { display:flex; width:max-content; animation: mq  30s linear infinite; }
      .mq-trackR { display:flex; width:max-content; animation: mqR 26s linear infinite; }

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
        .lp-hamburger { display:flex; }

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
  const { t } = useLang();
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

      {/* CTA strip */}
      <div style={{
        padding: "24px 5vw",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        borderTop: "1px solid rgba(0,0,0,.07)",
        flexWrap: "wrap", gap: 16,
      }}>
        <p style={{ fontSize: 13, color: "rgba(0,0,0,.38)", fontFamily: SANS, letterSpacing: 0.3, margin: 0 }}>
          {t("Агрегатор кастингов из 200+ Telegram-каналов — для моделей, актёров и event-персонала", "An aggregator of castings from 200+ Telegram channels — for models, actors and event staff")}
        </p>
        <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill" style={{ padding: "12px 28px", flexShrink: 0 }}>
          <TgIcon /> {t("Открыть бота", "Open the bot")}
        </a>
      </div>
    </section>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
export function LandingPage() {
  const { t, lang, setLang } = useLang();
  useGlobalStyles();
  useReveal();
  const scrollY = useScrollY();
  const [menuOpen, setMenuOpen] = useState(false);
  const [vpnToast, setVpnToast] = useState(false);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [menuOpen]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      const a = (e.target as Element).closest("a");
      if (a?.href?.includes("t.me")) {
        setVpnToast(true);
        setTimeout(() => setVpnToast(false), 5000);
      }
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, []);

  return (
    <div style={{ background: WHITE, fontFamily: SANS, color: BLACK, overflowX: "hidden" }}>

      {vpnToast && (
        <div style={{
          position: "fixed", bottom: 28, left: "50%", transform: "translateX(-50%)",
          zIndex: 9999, background: "#1a1208", color: WHITE,
          padding: "13px 22px", borderRadius: 14, fontSize: 14, fontFamily: SANS,
          boxShadow: "0 6px 32px rgba(0,0,0,.45)", display: "flex",
          alignItems: "center", gap: 10, whiteSpace: "nowrap",
          maxWidth: "calc(100vw - 48px)", animation: "fadeUp .25s ease",
        }}>
          <span style={{ fontSize: 18 }}>🔒</span>
          <span>{t("Если Telegram не открылся — включите VPN", "If Telegram didn't open — turn on a VPN")}</span>
        </div>
      )}

      {/* ══ NAV — minimal, always white ══════════════════════════════════════ */}
      <nav className="lp-nav" style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 300,
        height: 64,
        background: menuOpen ? BLACK : (scrollY > 60 ? "rgba(255,255,255,.97)" : WHITE),
        borderBottom: menuOpen ? "none" : "1px solid rgba(0,0,0,.07)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 48px",
        transition: "background .3s, box-shadow .3s",
        boxShadow: (!menuOpen && scrollY > 60) ? "0 2px 20px rgba(0,0,0,.06)" : "none",
      }}>
        <div onClick={() => { window.scrollTo({ top: 0, behavior: "smooth" }); setMenuOpen(false); }}
          style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 18, letterSpacing: 1, color: menuOpen ? WHITE : BLACK }}>MP</span>
          <span style={{ fontSize: 10, letterSpacing: 3, color: GOLD, fontWeight: 600, textTransform: "uppercase" }}>Agency</span>
        </div>
        <div className="lp-nav-links">
          {[{ l: t("Кастинги", "Castings"), id: "castings" }, { l: t("Категории", "Categories"), id: "categories" }, { l: t("Как работает", "How it works"), id: "how" }].map(({ l, id }) => (
            <button key={id} className="nav-btn" onClick={() => scrollTo(id)}>{l}</button>
          ))}
          <button onClick={() => setLang(lang === "ru" ? "en" : "ru")} className="nav-btn" style={{ fontWeight: 600 }}>
            {lang === "ru" ? "EN" : "RU"}
          </button>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill" style={{ padding: "10px 24px" }}>
            <TgIcon /> {t("Открыть бота", "Open the bot")}
          </a>
        </div>
        <button
          className={`lp-hamburger ${menuOpen ? "open" : "closed"}`}
          onClick={() => setMenuOpen(o => !o)}
          aria-label={menuOpen ? t("Закрыть меню", "Close menu") : t("Открыть меню", "Open menu")}
          aria-expanded={menuOpen}
        >
          <span /><span /><span />
        </button>
      </nav>

      {/* ══ MOBILE MENU OVERLAY ═══════════════════════════════════════════════ */}
      {menuOpen && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 250,
          background: BLACK,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          animation: "menuSlideIn 0.32s ease forwards",
          paddingTop: 64,
        }}>
          <div style={{ width: "100%", maxWidth: 420, padding: "0 32px" }}>
            {[
              { l: t("Кастинги", "Castings"),         id: "castings" },
              { l: t("Категории", "Categories"),      id: "categories" },
              { l: t("Как работает", "How it works"), id: "how" },
            ].map(({ l, id }) => (
              <button key={id} className="mob-menu-link" onClick={() => { scrollTo(id); setMenuOpen(false); }}>
                {l}
              </button>
            ))}
            <div style={{ marginTop: 32, display: "flex", justifyContent: "center" }}>
              <button
                onClick={() => setLang(lang === "ru" ? "en" : "ru")}
                style={{
                  background: "none", border: "1px solid rgba(255,255,255,.3)", borderRadius: 100,
                  color: WHITE, padding: "8px 20px", fontSize: 12, letterSpacing: 2,
                  textTransform: "uppercase", fontWeight: 600, fontFamily: SANS, cursor: "pointer",
                }}
              >
                {lang === "ru" ? "EN" : "RU"}
              </button>
            </div>
            <div style={{ marginTop: 24, display: "flex", justifyContent: "center" }}>
              <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill"
                onClick={() => setMenuOpen(false)}>
                <TgIcon /> {t("Открыть бота", "Open the bot")}
              </a>
            </div>
          </div>
        </div>
      )}

      {/* ══ CLIP-TEXT — фото сквозь буквы, самый первый блок ══════════════ */}
      <div style={{ paddingTop: 64 }}>
        <ClipText />
      </div>

      {/* ══ DIAGONAL MARQUEES — перекрещивающиеся как aroundbrand ═════════════ */}
      <div style={{ position: "relative", height: 220, margin: "0", overflow: "hidden" }}>
        {/* Strip 1 — GOLD, tilted -3° */}
        <div style={{
          position: "absolute", left: "-5%", right: "-5%", top: 46,
          transform: "rotate(-2.8deg)", background: GOLD,
          padding: "16px 0", overflow: "hidden", zIndex: 2,
        }}>
          <MqTrack items={[t("Кастинги", "Castings"), t("Актёры и Модели", "Actors & Models"), "Event", t("Хелперы", "Helpers"), t("Реклама", "Ads")]} size={28} color={BLACK} />
        </div>
        {/* Strip 2 — BLACK, tilted +3° */}
        <div style={{
          position: "absolute", left: "-5%", right: "-5%", top: 120,
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
            <Lbl>{t("Последние публикации", "Latest listings")}</Lbl>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 4vw, 52px)", lineHeight: 1 }}>
              {t("Кастинги", "Castings")}<br /><em style={{ fontWeight: 400, color: "rgba(0,0,0,.4)", fontSize: "0.75em" }}>{t("сегодня", "today")}</em>
            </h2>
          </div>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 3, fontFamily: SANS }}>
            {t("Смотреть все →", "See all →")}
          </a>
        </div>

        <div className="reveal lp-grid-3col">
          <a href={APP_URL} target="_blank" rel="noopener noreferrer"
            className="photo-card" style={{ gridRow: "1 / 3", aspectRatio: "3/4", textDecoration: "none" }}>
            <img src={P.girl1} alt={t("Актрисы", "Actresses")} />
            <div className="ov">
              <div style={{ fontFamily: SERIF, fontSize: 20, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>{t("Актрисы и модели", "Actresses & models")}</div>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,.5)", letterSpacing: 1, marginTop: 4 }}>{t("Кино · Реклама · Съёмки", "Film · Ads · Photoshoots")}</div>
              <div className="bar" />
            </div>
          </a>
          {[
            { src: P.shoot2, t: t("Реклама", "Ads"),   s: t("Москва", "Moscow") },
            { src: P.event1, t: "Event",               s: t("Хостес · Промо", "Hostess · Promo") },
            { src: P.man1,   t: t("Мужское", "Menswear"), s: "Fashion" },
            { src: P.shoot1, t: t("Съёмки", "Shoots"), s: t("Студия", "Studio") },
          ].map(({ src, t: label, s }) => (
            <a key={label} href={APP_URL} target="_blank" rel="noopener noreferrer"
              className="photo-card" style={{ textDecoration: "none", aspectRatio: "4/3" }}>
              <img src={src} alt={label} />
              <div className="ov">
                <div style={{ fontFamily: SERIF, fontSize: 15, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
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
          <img src={P.studio} alt={t("Студия", "Studio")} style={{ height: "100%" }} />
        </a>
        <div style={{ background: CREAM, padding: "72px 64px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div className="reveal">
            <Lbl>Telegram Mini App</Lbl>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 3vw, 46px)", lineHeight: 1.05, textTransform: "uppercase", marginBottom: 24 }}>
              {t("Стать", "Become")}<br />{t("участником", "a member")}
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.85, color: "#555", marginBottom: 32, maxWidth: 360, fontFamily: SANS }}>
              {t(
                "Заполни анкету в Mini App — укажи категорию, параметры и город. Бот начнёт присылать только подходящие кастинги из 200+ каналов.",
                "Fill out your profile in the Mini App — pick a category, parameters and city. The bot will start sending only castings that match, from 200+ channels."
              )}
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill">
              <TgIcon /> {t("Заполнить анкету", "Fill out profile")}
            </a>
            <div style={{ marginTop: 36, display: "flex", flexDirection: "column", gap: 14 }}>
              {[
                t("Актёры и модели", "Actors & models"),
                t("Event-персонал", "Event staff"),
                t("Хелперы и разнорабочие", "Helpers & laborers"),
                t("Административный персонал", "Administrative staff"),
              ].map((item) => (
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
          <MqTrack items={[t("Стать участником", "Become a member"), t("Получать кастинги", "Get castings"), t("Подать анкету", "Submit profile"), "Model Pro Agency"]} size={22} color={GOLD} italic />
        </div>
      </div>

      {/* ══ SPLIT reverse: умный агрегатор ═══════════════════════════════════ */}
      <section className="lp-split-r">
        <div style={{ background: WHITE, padding: "72px 64px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div className="reveal">
            <Lbl>{t("Технологии", "Technology")}</Lbl>
            <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 3vw, 46px)", lineHeight: 1.05, textTransform: "uppercase", marginBottom: 24 }}>
              {t("Умный", "Smart")}<br />{t("агрегатор", "aggregator")}
            </h2>
            <p style={{ fontSize: 15, lineHeight: 1.85, color: "#555", marginBottom: 32, maxWidth: 360, fontFamily: SANS }}>
              {t(
                "ИИ анализирует каждое объявление, сравнивает с твоей анкетой и присылает уведомление раньше всех — только то, что подходит.",
                "AI analyzes every listing, compares it against your profile, and notifies you before anyone else — only what actually fits."
              )}
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill-dark">
              {t("Попробовать →", "Try it →")}
            </a>
          </div>
        </div>
        <a href={APP_URL} target="_blank" rel="noopener noreferrer"
          className="photo-card" style={{ minHeight: 500, textDecoration: "none" }}>
          <img src={P.girl2} alt={t("Модель", "Model")} style={{ height: "100%" }} />
        </a>
      </section>

      {/* ══ CATEGORIES ═══════════════════════════════════════════════════════ */}
      <section id="categories" className="lp-section-pad-t" style={{ padding: "80px 48px 0" }}>
        <div className="reveal" style={{ textAlign: "center", marginBottom: 48 }}>
          <Lbl>{t("Для кого", "Who it's for")}</Lbl>
          <h2 style={{ fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 4vw, 52px)", lineHeight: 1 }}>{t("Категории", "Categories")}</h2>
        </div>
        <div className="reveal lp-grid-4col">
          {[
            { src: P.girl1,  t: t("Актрисы и модели", "Actresses & models"), s: t("Кино · Реклама · Съёмки", "Film · Ads · Photoshoots") },
            { src: P.man2,   t: t("Актёры и модели", "Actors & models"),     s: t("Мужское направление", "Menswear direction") },
            { src: P.event2, t: t("Event-персонал", "Event staff"),         s: t("Хостес · Промо · Event", "Hostess · Promo · Events") },
            { src: P.girl2,  t: t("Разнорабочие", "General labor"),         s: t("Хелперы · Клининг", "Helpers · Cleaning") },
          ].map(({ src, t: label, s }) => (
            <a key={label} href={APP_URL} target="_blank" rel="noopener noreferrer"
              className="photo-card" style={{ textDecoration: "none", aspectRatio: "2/3" }}>
              <img src={src} alt={label} />
              <div className="ov">
                <div style={{ fontFamily: SERIF, fontSize: 17, fontWeight: 700, color: WHITE, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
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
              <Lbl light>{t("Инструкция", "Instructions")}</Lbl>
              <h2 style={{
                fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(32px, 4.5vw, 60px)",
                textTransform: "uppercase", color: WHITE, lineHeight: 1,
              }}>
                {t("Как это", "How it")}<br /><em style={{ fontWeight: 400, background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>{t("работает", "works")}</em>
              </h2>
            </div>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill">
              <TgIcon /> {t("Начать сейчас", "Start now")}
            </a>
          </div>
          <div className="reveal lp-how-grid">
            {[
              { n: "01", t: t("Открой бота", "Open the bot"),      d: t("Найди @ModelProAgency_bot в Telegram и запусти командой /start.", "Find @ModelProAgency_bot on Telegram and launch it with the /start command.") },
              { n: "02", t: t("Заполни анкету", "Fill out profile"), d: t("В Mini App укажи категорию, параметры, город. Занимает 2 минуты.", "In the Mini App, specify your category, parameters and city. Takes 2 minutes.") },
              { n: "03", t: t("Получай кастинги", "Get castings"),  d: t("Бот мониторит 200+ каналов и присылает только подходящие предложения.", "The bot monitors 200+ channels and sends only offers that match you.") },
              { n: "04", t: t("Отправь отклик", "Send a reply"),    d: t("Кнопка «Сгенерировать» готовит текст по твоей анкете — копируй и отправляй.", "The “Generate” button drafts a reply from your profile — copy it and send.") },
            ].map(({ n, t: label, d }, i, arr) => (
              <div key={n} style={{
                padding: "40px 32px",
                background: "rgba(255,255,255,.025)",
                borderRight: i < arr.length - 1 ? "1px solid rgba(255,255,255,.05)" : "none",
              }}>
                <div style={{
                  fontFamily: SERIF, fontSize: 52, fontWeight: 900, lineHeight: 1, marginBottom: 24,
                  background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
                }}>{n}</div>
                <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", fontWeight: 700, color: WHITE, marginBottom: 14, fontFamily: SANS }}>{label}</div>
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
              <Lbl light>{t("Возможности", "Features")}</Lbl>
              <h2 style={{
                fontFamily: SERIF, fontWeight: 900, fontSize: "clamp(28px, 4vw, 52px)",
                textTransform: "uppercase", lineHeight: 1,
                background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
              }}>
                {t("Что внутри", "What's inside")}<br />{t("бота", "the bot")}
              </h2>
            </div>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 2, fontFamily: SANS }}>
              {t("Попробовать →", "Try it →")}
            </a>
          </div>
          <div className="reveal lp-feat-grid">
            {[
              { n: "01", t: t("Умная фильтрация", "Smart filtering"), d: t("ИИ анализирует кастинг и сравнивает с твоими параметрами — рост, возраст, тип внешности, город.", "AI analyzes each casting and compares it against your parameters — height, age, look, city.") },
              { n: "02", t: t("Избранное", "Favorites"),               d: t("Сохраняй лучшие предложения одним нажатием, чтобы вернуться позже.", "Save the best offers with one tap, so you can come back to them later.") },
              { n: "03", t: t("Чёрный список", "Blocklist"),           d: t("Добавляй слова-исключения — бот перестанет присылать нежелательное.", "Add exclusion words — the bot will stop sending anything you don't want.") },
              { n: "04", t: t("Готовый отклик", "Ready-made reply"),   d: t("Одна кнопка — и персональный текст отклика сформирован по данным анкеты.", "One button generates a personal reply text drawn from your profile data.") },
              { n: "05", t: t("Дайджест", "Digest"),                   d: t("Не хочешь уведомления сразу? /review покажет все новинки одним списком.", "Don't want instant notifications? /review shows all the new listings in one list.") },
              { n: "06", t: t("Уведомления 24/7", "24/7 alerts"),      d: t("Кастинг появился в канале — ты узнаёшь первым. Без задержек.", "A casting appears in a channel — you find out first. No delays.") },
            ].map(({ n, t: label, d }) => (
              <div key={n} style={{ borderTop: "1px solid rgba(255,255,255,.07)", padding: "36px 0", display: "flex", gap: 28 }}>
                <div style={{
                  fontFamily: SERIF, fontSize: 40, fontWeight: 900, lineHeight: 1, flexShrink: 0,
                  background: GRAD_TEXT, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
                  opacity: 0.7,
                }}>{n}</div>
                <div>
                  <div style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", fontWeight: 700, color: WHITE, marginBottom: 12, fontFamily: SANS }}>{label}</div>
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
            {t("Твой кастинг ждёт", "Your casting awaits")}
          </h2>
          <div style={{ width: 60, height: 2, background: GOLD, margin: "28px auto" }} />
          <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill-outline">
            <TgIcon /> {t("Открыть в Telegram", "Open in Telegram")}
          </a>
        </div>
      </div>

      {/* ══ SEO TEXT ═════════════════════════════════════════════════════════ */}
      <div style={{ background: "#0a0a0a", padding: "0 48px 48px" }}>
        <div style={{ borderTop: "1px solid rgba(255,255,255,.05)", paddingTop: 36, maxWidth: 1140, margin: "0 auto" }}>
          <p style={{ fontSize: 12, lineHeight: 2, color: "rgba(255,255,255,.18)", fontFamily: SANS, maxWidth: 860 }}>
            {t(
              `Model Pro Agency — агрегатор кастингов для моделей, актёров и event-персонала в Москве и по всей России.
            Сервис автоматически мониторит объявления из 200+ Telegram-каналов: кастинги для моделей,
            кастинги для актёров без опыта, вакансии хостес и промо-моделей, работа на мероприятиях,
            выставках и презентациях. Кастинги 2026 — актуальная база обновляется ежедневно.
            Подходит тем, кто ищет работу моделью, хочет попасть на официальный кастинг, найти вакансии
            event-персонала или промо-акции. Умная фильтрация подбирает только релевантные предложения
            по вашим параметрам — росту, возрасту, типу внешности и городу.`,
              `Model Pro Agency is a casting aggregator for models, actors and event staff in Moscow and across Russia.
            The service automatically monitors listings from 200+ Telegram channels: castings for models,
            castings for actors with no experience, hostess and promo-model vacancies, work at events,
            exhibitions and presentations. Castings 2026 — an up-to-date database updated daily.
            Ideal for anyone looking for modeling work, aiming for an official casting, or seeking
            event-staff vacancies or promo campaigns. Smart filtering surfaces only the offers relevant
            to your parameters — height, age, look and city.`
            )}
          </p>
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
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24, fontFamily: SANS }}>{t("Категории", "Categories")}</div>
            {[t("Актёры и модели", "Actors & models"), t("Event-персонал", "Event staff"), t("Разнорабочие", "General labor"), t("Администрирование", "Administration")].map((l) => (
              <FLink key={l} href={APP_URL}>{l}</FLink>
            ))}
          </div>
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24, fontFamily: SANS }}>Telegram</div>
            <FLink href={BOT_URL}>{t("Открыть бота", "Open the bot")}</FLink>
            <FLink href={APP_URL}>Mini App</FLink>
            <FLink href={BOT_URL}>@{BOT_USERNAME}</FLink>
          </div>
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24, fontFamily: SANS }}>{t("Начать", "Get started")}</div>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,.3)", lineHeight: 1.8, marginBottom: 24, fontFamily: SANS }}>
              {t("Запусти бота и заполни анкету — кастинги придут сами.", "Launch the bot and fill out your profile — castings will come to you.")}
            </p>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="pill" style={{ padding: "12px 24px" }}>
              <TgIcon /> {t("Открыть", "Open")}
            </a>
          </div>
        </div>
        <div style={{ height: 1, background: "rgba(255,255,255,.06)", marginBottom: 24 }} />
        <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, alignItems: "center" }}>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,.16)", fontFamily: SANS }}>
            © {new Date().getFullYear()} Model Promo Agency. {t("Все права защищены", "All rights reserved")}. · {t("ИП Рябов Семён Кириллович", "Individual Entrepreneur Semyon Kirillovich Ryabov")}
          </div>
          <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
            {[
              { label: t("Оферта", "Offer"),                     href: "/offer"    },
              { label: t("Конфиденциальность", "Privacy"),       href: "/privacy"  },
              { label: t("Контакты", "Contacts"),                href: "/contacts" },
            ].map(({ label, href }) => (
              <a key={href} href={href} style={{ fontSize: 11, color: "rgba(255,255,255,.25)", textDecoration: "none", fontFamily: SANS }}>
                {label}
              </a>
            ))}
            <span style={{ fontSize: 11, color: "rgba(255,255,255,.16)", fontFamily: SANS }}>16+</span>
          </div>
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
