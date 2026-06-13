import { useEffect, useRef, useState } from "react";

const BOT_USERNAME = "ModelProAgency_bot";
const APP_URL = `https://t.me/${BOT_USERNAME}/app`;
const BOT_URL = `https://t.me/${BOT_USERNAME}`;

const GOLD = "#c9a96e";
const BLACK = "#0a0a0a";
const WHITE = "#ffffff";
const CREAM = "#f5f3ef";

// ── Unsplash photos ──────────────────────────────────────────────────────────
const P = {
  hero:    "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=1600&q=90",
  girl1:   "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=800&q=85",
  girl2:   "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?w=800&q=85",
  girl3:   "https://images.unsplash.com/photo-1524638431109-93d95c968f03?w=800&q=85",
  man1:    "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800&q=85",
  man2:    "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=800&q=85",
  event1:  "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&q=85",
  event2:  "https://images.unsplash.com/photo-1519671282429-b44660ead0a7?w=800&q=85",
  studio:  "https://images.unsplash.com/photo-1581044777550-4cfa60707c03?w=800&q=85",
  casting: "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?w=800&q=85",
  shoot1:  "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=800&q=85",
  shoot2:  "https://images.unsplash.com/photo-1509631179647-0177331693ae?w=800&q=85",
};

// ── Scroll to anchor ─────────────────────────────────────────────────────────
function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
}

// ── Scroll position hook ─────────────────────────────────────────────────────
function useScrollY() {
  const [y, setY] = useState(0);
  useEffect(() => {
    const fn = () => setY(window.scrollY);
    window.addEventListener("scroll", fn, { passive: true });
    return () => window.removeEventListener("scroll", fn);
  }, []);
  return y;
}

// ── Gold button ──────────────────────────────────────────────────────────────
function GoldBtn({ href, children }: { href: string; children: React.ReactNode }) {
  const [hov, setHov] = useState(false);
  return (
    <a
      href={href} target="_blank" rel="noopener noreferrer"
      style={{
        display: "inline-flex", alignItems: "center", gap: 10,
        background: hov ? "#b8924f" : GOLD, color: BLACK,
        padding: "16px 40px", textDecoration: "none",
        fontSize: 11, letterSpacing: 3, fontWeight: 700, textTransform: "uppercase",
        transition: "background 0.2s", whiteSpace: "nowrap",
      }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      {children}
    </a>
  );
}

function OutlineBtn({ href, children, dark }: { href: string; children: React.ReactNode; dark?: boolean }) {
  const [hov, setHov] = useState(false);
  return (
    <a
      href={href} target="_blank" rel="noopener noreferrer"
      style={{
        display: "inline-flex", alignItems: "center", gap: 10,
        border: `1px solid ${dark ? "rgba(255,255,255,0.25)" : "rgba(0,0,0,0.3)"}`,
        color: hov ? GOLD : (dark ? "rgba(255,255,255,0.75)" : "rgba(0,0,0,0.7)"),
        borderColor: hov ? GOLD : (dark ? "rgba(255,255,255,0.25)" : "rgba(0,0,0,0.3)"),
        padding: "16px 32px", textDecoration: "none",
        fontSize: 11, letterSpacing: 3, fontWeight: 500, textTransform: "uppercase",
        transition: "color 0.2s, border-color 0.2s", whiteSpace: "nowrap",
      }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      {children}
    </a>
  );
}

// ── Divider ──────────────────────────────────────────────────────────────────
function GoldLine({ mx = 48 }: { mx?: number }) {
  return <div style={{ height: 1, background: GOLD, margin: `0 ${mx}px` }} />;
}

// ── Section label ─────────────────────────────────────────────────────────────
function Label({ children, light }: { children: React.ReactNode; light?: boolean }) {
  return (
    <div style={{
      fontSize: 10, letterSpacing: 4, textTransform: "uppercase",
      color: light ? "rgba(255,255,255,0.45)" : "rgba(0,0,0,0.4)",
      marginBottom: 20, fontFamily: "Georgia, serif",
    }}>
      {children}
    </div>
  );
}

// ── Photo + overlay card ─────────────────────────────────────────────────────
function PhotoCard({
  src, title, sub, href, aspect = "3/4", grayscale = true,
}: { src: string; title: string; sub?: string; href: string; aspect?: string; grayscale?: boolean }) {
  const [hov, setHov] = useState(false);
  return (
    <a
      href={href} target="_blank" rel="noopener noreferrer"
      style={{ display: "block", position: "relative", overflow: "hidden", textDecoration: "none" }}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
    >
      <div style={{ aspectRatio: aspect, overflow: "hidden" }}>
        <img
          src={src} alt={title}
          style={{
            width: "100%", height: "100%", objectFit: "cover", display: "block",
            filter: grayscale
              ? `grayscale(${hov ? 20 : 60}%) brightness(${hov ? 0.7 : 0.8})`
              : `brightness(${hov ? 0.75 : 0.85})`,
            transform: hov ? "scale(1.04)" : "scale(1)",
            transition: "transform 0.6s ease, filter 0.4s ease",
          }}
        />
      </div>
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        padding: "36px 24px 24px",
        background: "linear-gradient(to top, rgba(0,0,0,0.75) 0%, transparent 100%)",
      }}>
        <div style={{
          fontSize: "clamp(16px, 2vw, 22px)", fontWeight: 700,
          textTransform: "uppercase", letterSpacing: 2,
          color: WHITE, fontFamily: "Georgia, serif", marginBottom: 4,
        }}>
          {title}
        </div>
        {sub && <div style={{ fontSize: 11, letterSpacing: 1, color: "rgba(255,255,255,0.6)" }}>{sub}</div>}
        <div style={{ width: hov ? 48 : 24, height: 2, background: GOLD, marginTop: 12, transition: "width 0.3s" }} />
      </div>
    </a>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
export function LandingPage() {
  const scrollY = useScrollY();

  return (
    <div style={{ background: WHITE, color: BLACK, fontFamily: "'Segoe UI', Arial, sans-serif", minHeight: "100vh" }}>

      {/* ══ NAV ══════════════════════════════════════════════════════════════ */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        height: 68,
        background: scrollY > 60 ? "rgba(255,255,255,0.97)" : "transparent",
        borderBottom: scrollY > 60 ? "1px solid #e8e8e8" : "none",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 48px",
        transition: "background 0.4s, box-shadow 0.4s",
        boxShadow: scrollY > 60 ? "0 2px 20px rgba(0,0,0,0.07)" : "none",
      }}>
        <div
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          style={{ display: "flex", alignItems: "center", gap: 12, cursor: "pointer" }}
        >
          <div style={{
            width: 46, height: 46,
            background: scrollY > 60 ? BLACK : "rgba(255,255,255,0.1)",
            border: `1px solid ${scrollY > 60 ? "transparent" : "rgba(255,255,255,0.3)"}`,
            display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center",
            transition: "background 0.4s",
          }}>
            <span style={{ color: WHITE, fontWeight: 800, fontSize: 11, letterSpacing: 1, fontFamily: "Georgia, serif" }}>MP</span>
            <span style={{ color: GOLD, fontWeight: 400, fontSize: 8, letterSpacing: 2 }}>AGENCY</span>
          </div>
          <span style={{
            fontSize: 12, fontWeight: 600, letterSpacing: 2, textTransform: "uppercase",
            color: scrollY > 60 ? BLACK : WHITE, transition: "color 0.4s",
            fontFamily: "Georgia, serif",
          }}>Model Pro</span>
        </div>

        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          {[
            { label: "Кастинги", id: "castings" },
            { label: "Категории", id: "categories" },
            { label: "Как работает", id: "how" },
          ].map(({ label, id }) => (
            <button
              key={id}
              onClick={() => scrollTo(id)}
              style={{
                background: "none", border: "none", cursor: "pointer", padding: 0,
                fontSize: 11, letterSpacing: 2, textTransform: "uppercase",
                color: scrollY > 60 ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.7)",
                fontWeight: 500, transition: "color 0.3s",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = GOLD; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = scrollY > 60 ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.7)"; }}
            >
              {label}
            </button>
          ))}
          <a
            href={APP_URL} target="_blank" rel="noopener noreferrer"
            style={{
              background: GOLD, color: BLACK,
              padding: "10px 24px", textDecoration: "none",
              fontSize: 11, letterSpacing: 2, fontWeight: 700, textTransform: "uppercase",
              transition: "opacity 0.2s",
            }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = "0.85"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = "1"; }}
          >
            Открыть бота
          </a>
        </div>
      </nav>

      {/* ══ HERO — чёрный, логотип по центру ══════════════════════════════ */}
      <section style={{
        minHeight: "100vh",
        background: "#080808",
        position: "relative",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}>
        {/* фоновая фотография с затемнением */}
        <img
          src={P.hero}
          alt=""
          style={{
            position: "absolute", inset: 0,
            width: "100%", height: "100%",
            objectFit: "cover",
            filter: "grayscale(40%) brightness(0.22)",
            transform: `translateY(${scrollY * 0.25}px)`,
          }}
        />
        {/* боковые виньетки */}
        <div style={{
          position: "absolute", inset: 0,
          background: "radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.85) 100%)",
          pointerEvents: "none",
        }} />

        {/* центральный блок */}
        <div style={{ position: "relative", textAlign: "center" }}>
          {/* верхняя тонкая линия */}
          <div style={{ width: 1, height: 64, background: `linear-gradient(to bottom, transparent, ${GOLD})`, margin: "0 auto 32px" }} />

          {/* рамка */}
          <div style={{ position: "relative", display: "inline-block", padding: "56px 96px" }}>
            {/* угловые акценты */}
            {[
              { top: 0, left: 0, borderTop: `2px solid ${GOLD}`, borderLeft: `2px solid ${GOLD}` },
              { top: 0, right: 0, borderTop: `2px solid ${GOLD}`, borderRight: `2px solid ${GOLD}` },
              { bottom: 0, left: 0, borderBottom: `2px solid ${GOLD}`, borderLeft: `2px solid ${GOLD}` },
              { bottom: 0, right: 0, borderBottom: `2px solid ${GOLD}`, borderRight: `2px solid ${GOLD}` },
            ].map((s, i) => (
              <div key={i} style={{ position: "absolute", width: 28, height: 28, ...s }} />
            ))}
            <div style={{
              position: "absolute", inset: 0,
              border: "1px solid rgba(255,255,255,0.12)",
            }} />

            <h1 style={{
              fontSize: "clamp(56px, 9vw, 130px)",
              fontWeight: 800, lineHeight: 0.92, letterSpacing: "0.03em",
              textTransform: "uppercase",
              fontFamily: "Georgia, 'Times New Roman', serif",
              background: `linear-gradient(155deg, #ffffff 0%, #e8d5a3 35%, ${GOLD} 60%, #ffffff 100%)`,
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
              margin: 0,
            }}>
              Model Pro
            </h1>
            <div style={{
              fontSize: "clamp(13px, 2.2vw, 24px)",
              letterSpacing: "0.6em", textTransform: "uppercase",
              fontFamily: "Georgia, 'Times New Roman', serif",
              background: `linear-gradient(90deg, rgba(255,255,255,0.45) 0%, ${GOLD} 50%, rgba(255,255,255,0.45) 100%)`,
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
              marginTop: 16,
            }}>
              Agency
            </div>
          </div>

          {/* подзаголовок */}
          <p style={{
            marginTop: 44, fontSize: 13, letterSpacing: "0.22em",
            textTransform: "uppercase", color: "rgba(255,255,255,0.38)",
            fontFamily: "Georgia, serif",
          }}>
            Агрегатор кастингов · Telegram Mini App
          </p>

          {/* кнопки */}
          <div style={{ display: "flex", gap: 16, marginTop: 44, justifyContent: "center", flexWrap: "wrap" }}>
            <GoldBtn href={APP_URL}><TgIcon /> Открыть Mini App</GoldBtn>
            <OutlineBtn href={APP_URL} dark>Узнать больше</OutlineBtn>
          </div>

          {/* цифры */}
          <div style={{ display: "flex", gap: 56, marginTop: 72, justifyContent: "center" }}>
            {[["200+", "Каналов"], ["4", "Категории"], ["24/7", "Мониторинг"]].map(([n, l]) => (
              <div key={l} style={{ textAlign: "center" }}>
                <div style={{
                  fontSize: 34, fontWeight: 800, letterSpacing: -1,
                  fontFamily: "Georgia, serif",
                  background: `linear-gradient(135deg, ${WHITE}, ${GOLD})`,
                  WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
                }}>{n}</div>
                <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginTop: 8 }}>{l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* нижняя тонкая линия + scroll */}
        <div style={{
          position: "absolute", bottom: 0, left: "50%", transform: "translateX(-50%)",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 10,
          paddingBottom: 32,
        }}>
          <span style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: "rgba(255,255,255,0.22)" }}>Scroll</span>
          <div style={{ width: 1, height: 48, background: `linear-gradient(to bottom, ${GOLD}, transparent)` }} />
        </div>
      </section>

      {/* ══ TAGLINE STRIP ════════════════════════════════════════════════════ */}
      <div style={{
        background: GOLD, padding: "18px 48px",
        display: "flex", alignItems: "center", justifyContent: "center", gap: 40,
        flexWrap: "wrap",
      }}>
        {["Кастинги · Съёмки · Реклама", "Event-персонал", "Актёры и модели", "Разнорабочие"].map((t, i, arr) => (
          <span key={t} style={{ display: "flex", alignItems: "center", gap: 40 }}>
            <span style={{ fontSize: 11, letterSpacing: 3, textTransform: "uppercase", fontWeight: 600, color: BLACK }}>{t}</span>
            {i < arr.length - 1 && <span style={{ width: 4, height: 4, borderRadius: "50%", background: "rgba(0,0,0,0.3)", display: "inline-block" }} />}
          </span>
        ))}
      </div>

      {/* ══ EDITORIAL GRID — 5 фото ══════════════════════════════════════════ */}
      <section id="castings" style={{ padding: "72px 48px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 36 }}>
          <div>
            <Label>Портфолио участников</Label>
            <h2 style={{ fontSize: "clamp(28px, 3.5vw, 48px)", fontWeight: 800, fontFamily: "Georgia, serif", letterSpacing: 1, margin: 0 }}>
              Последние кастинги
            </h2>
          </div>
          <a href={APP_URL} target="_blank" rel="noopener noreferrer"
            style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 2 }}>
            Смотреть все →
          </a>
        </div>

        {/* 5-фото редакционная сетка */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gridTemplateRows: "auto auto", gap: 6 }}>
          {/* большая слева */}
          <div style={{ gridRow: "1 / 3" }}>
            <PhotoCard src={P.girl1} title="Актрисы" sub="Кино · Сериалы" href={APP_URL} aspect="2/3" />
          </div>
          {/* 4 маленьких справа */}
          <div style={{ gridColumn: "2 / 4", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            <PhotoCard src={P.shoot2} title="Реклама" sub="Москва" href={APP_URL} aspect="4/3" />
            <PhotoCard src={P.event1} title="Event" sub="Хостес · Промо" href={APP_URL} aspect="4/3" />
            <PhotoCard src={P.man1} title="Мужское" sub="Fashion" href={APP_URL} aspect="4/3" />
            <PhotoCard src={P.casting} title="Съёмки" sub="Студия" href={APP_URL} aspect="4/3" />
          </div>
        </div>
      </section>

      {/* ══ SPLIT: СТАТЬ УЧАСТНИКОМ ══════════════════════════════════════════ */}
      <section style={{ display: "grid", gridTemplateColumns: "55% 45%", marginTop: 6 }}>
        <div style={{ position: "relative", overflow: "hidden", minHeight: 580 }}>
          <img src={P.studio} alt="" style={{
            width: "100%", height: "100%", objectFit: "cover",
            filter: "grayscale(15%) brightness(0.88)",
          }} />
          {/* оверлей снизу */}
          <div style={{
            position: "absolute", inset: 0,
            background: "linear-gradient(135deg, rgba(0,0,0,0.4) 0%, transparent 60%)",
          }} />
        </div>
        <div style={{
          background: CREAM, padding: "72px 64px",
          display: "flex", flexDirection: "column", justifyContent: "center",
        }}>
          <Label>Telegram Mini App</Label>
          <h2 style={{
            fontSize: "clamp(28px, 3vw, 44px)", fontWeight: 800,
            fontFamily: "Georgia, serif", lineHeight: 1.1,
            textTransform: "uppercase", letterSpacing: 1, marginBottom: 24,
          }}>
            Стать<br />участником
          </h2>
          <p style={{ fontSize: 15, lineHeight: 1.85, color: "#555", marginBottom: 36, maxWidth: 380 }}>
            Заполни анкету в нашем Telegram Mini App за 2 минуты — укажи категорию,
            параметры и город. Бот сразу начнёт присылать только подходящие
            кастинги и вакансии.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            <GoldBtn href={APP_URL}><TgIcon /> Заполнить анкету</GoldBtn>
          </div>
          {/* мини-список */}
          <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 14 }}>
            {["Актёры и модели", "Event-персонал", "Хелперы и разнорабочие", "Административный персонал"].map((item) => (
              <div key={item} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: GOLD, flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: "#444", letterSpacing: 0.5 }}>{item}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ STATS BAR ════════════════════════════════════════════════════════ */}
      <div style={{ background: BLACK, padding: "56px 48px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 0, maxWidth: 1000, margin: "0 auto", textAlign: "center" }}>
          {[
            ["200+", "Telegram-каналов"],
            ["4", "Направления"],
            ["24/7", "Мониторинг"],
            ["2 мин", "Заполнить анкету"],
          ].map(([n, l], i, arr) => (
            <div key={l} style={{
              padding: "0 32px",
              borderRight: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.08)" : "none",
            }}>
              <div style={{
                fontSize: "clamp(32px, 4vw, 52px)", fontWeight: 800,
                fontFamily: "Georgia, serif",
                background: `linear-gradient(135deg, ${WHITE} 0%, ${GOLD} 100%)`,
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
                lineHeight: 1,
              }}>{n}</div>
              <div style={{ fontSize: 10, letterSpacing: 3, textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginTop: 14 }}>{l}</div>
            </div>
          ))}
        </div>
      </div>

      <GoldLine />

      {/* ══ SPLIT: ПРОФЕССИОНАЛЬНЫЙ ПОДХОД (reverse) ═════════════════════════ */}
      <section style={{ display: "grid", gridTemplateColumns: "45% 55%" }}>
        <div style={{
          background: WHITE, padding: "72px 64px",
          display: "flex", flexDirection: "column", justifyContent: "center",
        }}>
          <Label>Умный агрегатор</Label>
          <h2 style={{
            fontSize: "clamp(28px, 3vw, 44px)", fontWeight: 800,
            fontFamily: "Georgia, serif", lineHeight: 1.1,
            textTransform: "uppercase", letterSpacing: 1, marginBottom: 24,
          }}>
            Профессиональный<br />подход
          </h2>
          <p style={{ fontSize: 15, lineHeight: 1.85, color: "#555", marginBottom: 36, maxWidth: 380 }}>
            ИИ анализирует каждое объявление, извлекает требования и сравнивает
            с твоей анкетой в реальном времени. Ты получаешь уведомление
            раньше всех и только о том, что действительно подходит.
          </p>
          <OutlineBtn href={APP_URL}>Попробовать</OutlineBtn>
        </div>
        <div style={{ position: "relative", overflow: "hidden", minHeight: 500 }}>
          <img src={P.shoot1} alt="" style={{
            width: "100%", height: "100%", objectFit: "cover",
            filter: "grayscale(15%)",
          }} />
        </div>
      </section>

      <GoldLine />

      {/* ══ CATEGORIES ═══════════════════════════════════════════════════════ */}
      <section id="categories" style={{ padding: "72px 48px" }}>
        <div style={{ textAlign: "center", marginBottom: 52 }}>
          <Label>Для кого</Label>
          <h2 style={{ fontSize: "clamp(28px, 3.5vw, 48px)", fontWeight: 800, fontFamily: "Georgia, serif", letterSpacing: 1, margin: 0 }}>
            Категории
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
          {[
            { src: P.girl2, title: "Актрисы и модели", sub: "Кино · Реклама · Съёмки" },
            { src: P.man2,  title: "Актёры и модели", sub: "Мужское направление" },
            { src: P.event2, title: "Event-персонал", sub: "Хостес · Промо · Event" },
            { src: P.girl3, title: "Разнорабочие", sub: "Хелперы · Клининг" },
          ].map(({ src, title, sub }) => (
            <PhotoCard key={title} src={src} title={title} sub={sub} href={APP_URL} aspect="2/3" />
          ))}
        </div>
      </section>

      {/* ══ HOW IT WORKS ═════════════════════════════════════════════════════ */}
      <section id="how" style={{ background: BLACK, padding: "88px 48px" }}>
        <div style={{ maxWidth: 1100, margin: "0 auto" }}>
          <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 64, flexWrap: "wrap", gap: 20 }}>
            <div>
              <Label light>Инструкция</Label>
              <h2 style={{
                fontSize: "clamp(28px, 4vw, 52px)", fontWeight: 800,
                fontFamily: "Georgia, serif", letterSpacing: 1,
                color: WHITE, margin: 0, textTransform: "uppercase",
              }}>
                Как это<br />работает
              </h2>
            </div>
            <GoldBtn href={APP_URL}><TgIcon /> Начать сейчас</GoldBtn>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 2 }}>
            {[
              { n: "01", title: "Открой бота", desc: "Нажми кнопку ниже или найди @ModelProAgency_bot в Telegram и запусти его командой /start." },
              { n: "02", title: "Заполни анкету", desc: "В Mini App укажи категорию, параметры, город и предпочтения. Занимает ровно 2 минуты." },
              { n: "03", title: "Получай кастинги", desc: "Бот круглосуточно мониторит 200+ каналов и присылает только подходящие предложения." },
              { n: "04", title: "Отправь отклик", desc: "Кнопка «Сгенерировать отклик» готовит текст по твоей анкете — копируй и отправляй." },
            ].map(({ n, title, desc }, i, arr) => (
              <div key={n} style={{
                padding: "40px 32px",
                background: "rgba(255,255,255,0.03)",
                borderRight: i < arr.length - 1 ? "1px solid rgba(255,255,255,0.06)" : "none",
              }}>
                <div style={{
                  fontSize: 48, fontWeight: 800, fontFamily: "Georgia, serif",
                  color: GOLD, lineHeight: 1, marginBottom: 24, opacity: 0.9,
                }}>{n}</div>
                <div style={{ fontSize: 13, letterSpacing: 1, textTransform: "uppercase", fontWeight: 700, color: WHITE, marginBottom: 14 }}>{title}</div>
                <div style={{ fontSize: 13, lineHeight: 1.75, color: "rgba(255,255,255,0.45)" }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ FEATURES STRIP ═══════════════════════════════════════════════════ */}
      <section style={{ background: "#111", padding: "88px 48px" }}>
        <div style={{ maxWidth: 1140, margin: "0 auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 72, flexWrap: "wrap", gap: 20 }}>
            <div>
              <Label light>Возможности</Label>
              <h2 style={{
                fontSize: "clamp(28px, 4vw, 52px)", fontWeight: 800,
                fontFamily: "Georgia, serif", textTransform: "uppercase",
                letterSpacing: 1,
                background: `linear-gradient(135deg, ${WHITE} 0%, ${GOLD} 100%)`,
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text",
                margin: 0,
              }}>
                Что внутри бота
              </h2>
            </div>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: 11, letterSpacing: 2, textTransform: "uppercase", color: GOLD, textDecoration: "none", borderBottom: `1px solid ${GOLD}`, paddingBottom: 2 }}>
              Попробовать →
            </a>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 80px" }}>
            {[
              { n: "01", title: "Умная фильтрация", desc: "ИИ анализирует каждый кастинг и сравнивает с твоими параметрами — рост, возраст, тип внешности, город." },
              { n: "02", title: "Избранное", desc: "Сохраняй лучшие предложения одним нажатием, чтобы вернуться к ним позже или поделиться с коллегой." },
              { n: "03", title: "Чёрный список", desc: "Добавляй слова-исключения — и бот автоматически перестанет присылать нежелательные объявления." },
              { n: "04", title: "Готовый отклик", desc: "Одна кнопка — и персональный текст отклика сформирован по данным твоей анкеты. Остаётся только отправить." },
              { n: "05", title: "Дайджест", desc: "Не хочешь получать уведомления в моменте? Командой /review смотри все новинки одним списком в удобное время." },
              { n: "06", title: "Мгновенные уведомления", desc: "Кастинг появился в канале — ты узнаёшь первым. Бот работает круглосуточно без задержек." },
            ].map(({ n, title, desc }) => (
              <div key={n} style={{
                borderTop: "1px solid rgba(255,255,255,0.08)",
                padding: "40px 0",
                display: "flex",
                gap: 32,
              }}>
                <div style={{
                  fontSize: 42, fontWeight: 800, fontFamily: "Georgia, serif",
                  color: GOLD, opacity: 0.55, lineHeight: 1, flexShrink: 0,
                  letterSpacing: -1,
                }}>{n}</div>
                <div>
                  <div style={{
                    fontSize: 13, letterSpacing: 2, textTransform: "uppercase",
                    fontWeight: 700, color: WHITE, marginBottom: 14,
                  }}>{title}</div>
                  <div style={{ fontSize: 14, lineHeight: 1.8, color: "rgba(255,255,255,0.42)" }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══ WIDE PHOTO BAND ══════════════════════════════════════════════════ */}
      <div style={{ position: "relative", overflow: "hidden", height: 420 }}>
        <img src={P.event1} alt="" style={{
          width: "100%", height: "100%", objectFit: "cover",
          filter: "grayscale(30%) brightness(0.45)",
          transform: `translateY(${(scrollY - 2000) * 0.15}px)`,
        }} />
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          textAlign: "center",
        }}>
          <div style={{ width: 1, height: 48, background: `linear-gradient(to bottom, transparent, ${GOLD})`, marginBottom: 32 }} />
          <h2 style={{
            fontSize: "clamp(28px, 5vw, 64px)", fontWeight: 800,
            fontFamily: "Georgia, serif", textTransform: "uppercase",
            letterSpacing: 4, color: WHITE, marginBottom: 16,
          }}>
            Начни зарабатывать
          </h2>
          <p style={{ fontSize: 14, letterSpacing: 2, color: "rgba(255,255,255,0.5)", marginBottom: 40 }}>
            Тысячи кастингов каждый день — не пропускай своё
          </p>
          <GoldBtn href={APP_URL}><TgIcon /> Открыть в Telegram</GoldBtn>
        </div>
      </div>

      {/* ══ FOOTER ═══════════════════════════════════════════════════════════ */}
      <footer style={{ background: "#080808", color: WHITE, padding: "72px 48px 32px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 1fr 1fr", gap: 48, marginBottom: 56 }}>

          {/* Logo */}
          <div>
            <div style={{
              width: 52, height: 52,
              border: `1px solid ${GOLD}`,
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", marginBottom: 20,
            }}>
              <span style={{ color: WHITE, fontWeight: 800, fontSize: 13, letterSpacing: 1, fontFamily: "Georgia, serif" }}>MP</span>
              <span style={{ color: GOLD, fontSize: 8, letterSpacing: 3 }}>AGENCY</span>
            </div>
            <div style={{ fontSize: 11, letterSpacing: 2, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", lineHeight: 1.8 }}>
              Model Promo Agency<br />Telegram Mini App
            </div>
          </div>

          {/* Категории */}
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24 }}>Категории</div>
            {["Актёры и модели", "Event-персонал", "Разнорабочие", "Администрирование"].map((l) => (
              <div key={l} style={{ marginBottom: 12 }}>
                <a href={APP_URL} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", textDecoration: "none" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = GOLD; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.5)"; }}
                >
                  {l}
                </a>
              </div>
            ))}
          </div>

          {/* Бот */}
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24 }}>Telegram</div>
            {[
              { label: "Открыть бота", href: BOT_URL },
              { label: "Mini App", href: APP_URL },
              { label: "@" + BOT_USERNAME, href: BOT_URL },
            ].map(({ label, href }) => (
              <div key={label} style={{ marginBottom: 12 }}>
                <a href={href} target="_blank" rel="noopener noreferrer"
                  style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", textDecoration: "none" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = GOLD; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.5)"; }}
                >
                  {label}
                </a>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 24 }}>Начать</div>
            <p style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", lineHeight: 1.7, marginBottom: 24 }}>
              Запусти бота и заполни анкету — кастинги придут сами.
            </p>
            <GoldBtn href={APP_URL}><TgIcon /> Открыть</GoldBtn>
          </div>
        </div>

        <GoldLine mx={0} />
        <div style={{ paddingTop: 24, display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.22)", letterSpacing: 0.5 }}>
            © {new Date().getFullYear()} Model Promo Agency. Все права защищены. · ИП Рябов Семён Кириллович
          </div>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.22)", letterSpacing: 0.5 }}>16+</div>
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
