const GOLD  = "#c9a96e";
const WHITE = "#ffffff";
const SERIF = "'Playfair Display', 'Cormorant Garamond', Georgia, serif";
const SANS  = "'Inter', 'Segoe UI', Arial, sans-serif";

const BOT_USERNAME = "ModelProAgency_bot";
const BOT_URL   = `https://t.me/${BOT_USERNAME}`;
const SITE_URL  = "https://modelpro.agency";
const EMAIL     = "semen.ryab0v@yandex.ru";
const INN       = "502018424008";
const OGRNIP    = "325508100609056";
const OWNER     = "Индивидуальный предприниматель Рябов Семён Кириллович";
const DATE      = "17 июня 2026 года";

/* ── Shared layout ─────────────────────────────────────────────────────── */

function LegalLayout({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ minHeight: "100vh", background: "#fafaf8", fontFamily: SANS, color: "#1a1a1a" }}>
      {/* header */}
      <header style={{
        background: "#0a0a0a",
        borderBottom: `1px solid rgba(201,169,110,.18)`,
        padding: "18px 48px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 12,
      }}>
        <a href="/" style={{ textDecoration: "none", display: "flex", flexDirection: "column", gap: 2 }}>
          <span style={{ fontFamily: SERIF, fontWeight: 700, fontSize: 18, letterSpacing: 1, color: WHITE }}>MP</span>
          <span style={{ fontSize: 8, letterSpacing: 3, color: GOLD, textTransform: "uppercase" }}>Agency</span>
        </a>
        <nav style={{ display: "flex", gap: 28, alignItems: "center" }}>
          {[
            { label: "Оферта",   href: "/offer"    },
            { label: "Конфиденциальность", href: "/privacy" },
            { label: "Контакты", href: "/contacts" },
          ].map(({ label, href }) => (
            <a key={href} href={href} style={{
              fontSize: 12, letterSpacing: 1, textTransform: "uppercase",
              color: window.location.pathname === href ? GOLD : "rgba(255,255,255,.45)",
              textDecoration: "none",
              transition: "color .2s",
            }}>{label}</a>
          ))}
        </nav>
      </header>

      {/* hero */}
      <div style={{ background: "#0a0a0a", padding: "56px 48px 48px", borderBottom: `1px solid rgba(201,169,110,.1)` }}>
        <div style={{ maxWidth: 800, margin: "0 auto" }}>
          <p style={{ fontSize: 11, letterSpacing: 4, textTransform: "uppercase", color: GOLD, marginBottom: 16, fontFamily: SANS }}>
            Model Promo Agency
          </p>
          <h1 style={{ fontFamily: SERIF, fontWeight: 700, fontSize: "clamp(28px,4vw,42px)", color: WHITE, margin: 0, lineHeight: 1.2 }}>
            {title}
          </h1>
        </div>
      </div>

      {/* content */}
      <main style={{ maxWidth: 800, margin: "0 auto", padding: "56px 48px 80px" }}>
        {children}
      </main>

      {/* footer */}
      <footer style={{
        background: "#0a0a0a",
        borderTop: `1px solid rgba(255,255,255,.06)`,
        padding: "32px 48px",
        display: "flex",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 12,
        alignItems: "center",
      }}>
        <div style={{ fontSize: 11, color: "rgba(255,255,255,.2)", fontFamily: SANS }}>
          © {new Date().getFullYear()} Model Promo Agency · {OWNER}
        </div>
        <div style={{ display: "flex", gap: 20 }}>
          {[
            { label: "Оферта",   href: "/offer"    },
            { label: "Конфиденциальность", href: "/privacy" },
            { label: "Контакты", href: "/contacts" },
          ].map(({ label, href }) => (
            <a key={href} href={href} style={{
              fontSize: 11, color: "rgba(255,255,255,.25)", textDecoration: "none", fontFamily: SANS,
            }}>{label}</a>
          ))}
        </div>
      </footer>

      <style>{`
        @media (max-width: 600px) {
          header, main, footer { padding-left: 20px !important; padding-right: 20px !important; }
        }
        .legal h2 { font-family: ${SERIF}; font-size: 18px; font-weight: 700; margin: 40px 0 12px; color: #111; }
        .legal h3 { font-size: 14px; font-weight: 600; margin: 24px 0 8px; color: #333; }
        .legal p  { font-size: 15px; line-height: 1.8; color: #444; margin: 0 0 14px; }
        .legal ul { padding-left: 20px; margin: 0 0 14px; }
        .legal li { font-size: 15px; line-height: 1.8; color: #444; margin-bottom: 4px; }
        .legal a  { color: ${GOLD}; text-decoration: none; }
        .legal .meta {
          font-size: 13px; color: #888; background: #f0ede8;
          border-left: 3px solid ${GOLD}; padding: 12px 16px;
          border-radius: 0 4px 4px 0; margin-bottom: 36px; line-height: 1.7;
        }
        .legal .section-num {
          display: inline-block; width: 28px; height: 28px;
          background: ${GOLD}; color: #fff; border-radius: 50%;
          text-align: center; line-height: 28px; font-size: 13px;
          font-weight: 700; margin-right: 10px; flex-shrink: 0;
        }
        .legal .section-title {
          display: flex; align-items: center; margin: 40px 0 12px;
        }
        .legal .section-title h2 { margin: 0; }
      `}</style>
    </div>
  );
}

/* ── Offer ─────────────────────────────────────────────────────────────── */

export function OfferPage() {
  return (
    <LegalLayout title="Публичная оферта">
      <div className="legal">
        <div className="meta">
          <strong>{OWNER}</strong><br />
          ИНН: {INN} · ОГРНИП: {OGRNIP}<br />
          Сайт: <a href={SITE_URL}>{SITE_URL}</a> · Редакция от {DATE}
        </div>

        <div className="section-title"><span className="section-num">1</span><h2>Термины и определения</h2></div>
        <p><strong>Акцепт</strong> — полное безоговорочное принятие условий настоящей оферты путём оплаты подписки или начала использования платного функционала Сервиса.</p>
        <p><strong>Договор</strong> — договор о предоставлении доступа к Сервису, заключённый между Администрацией и Пользователем на условиях настоящей оферты.</p>
        <p><strong>Пользователь</strong> — дееспособное физическое лицо старше 18 лет, совершившее Акцепт.</p>
        <p><strong>Сервис</strong> — агрегатор кастингов и вакансий «Model Promo Agency», доступный через Telegram-бота <a href={BOT_URL}>@{BOT_USERNAME}</a> и мини-приложение по адресу <a href={SITE_URL + "/app"}>{SITE_URL}/app</a>.</p>
        <p><strong>Администрация</strong> — {OWNER}, владелец и оператор Сервиса.</p>

        <div className="section-title"><span className="section-num">2</span><h2>Предмет соглашения</h2></div>
        <p>Администрация предоставляет Пользователю доступ к платному функционалу Сервиса: просмотр актуальных кастингов и вакансий для актёров, моделей и event-персонала, агрегированных из 200+ Telegram-каналов; возможность откликаться на проекты; получение уведомлений о новых предложениях в режиме реального времени.</p>
        <p>Авторизация в Сервисе осуществляется исключительно через Telegram. Доступ к мини-приложению возможен только через официального Telegram-бота <a href={BOT_URL}>@{BOT_USERNAME}</a>.</p>

        <div className="section-title"><span className="section-num">3</span><h2>Порядок принятия оферты</h2></div>
        <p>Акцептом настоящей оферты является совершение оплаты подписки через платёжную форму внутри мини-приложения. Совершая Акцепт, Пользователь подтверждает:</p>
        <ul>
          <li>полное и безоговорочное согласие с условиями настоящей оферты;</li>
          <li>свою полную дееспособность и достижение возраста 18 лет;</li>
          <li>ознакомление с Политикой конфиденциальности.</li>
        </ul>

        <div className="section-title"><span className="section-num">4</span><h2>Стоимость и порядок оплаты</h2></div>
        <p>Стоимость подписки определяется выбранным тарифным планом, актуальный перечень которых отображается в мини-приложении в разделе «Подписка». Оплата производится единовременно за выбранный период.</p>
        <p>Приём платежей осуществляется через платёжный сервис ЮKassa (<a href="https://yookassa.ru" target="_blank" rel="noopener noreferrer">yookassa.ru</a>). Оплата доступна только авторизованным Пользователям внутри мини-приложения.</p>
        <p>Подписка активируется автоматически после подтверждения платежа. Возврат денежных средств за неиспользованный остаток периода подписки не производится, за исключением случаев, предусмотренных действующим законодательством РФ.</p>

        <div className="section-title"><span className="section-num">5</span><h2>Срок действия договора</h2></div>
        <p>Договор вступает в силу с момента Акцепта и действует в течение оплаченного периода подписки. Пользователь вправе в любой момент прекратить использование Сервиса — доступ сохраняется до окончания оплаченного периода.</p>
        <p>Администрация вправе расторгнуть Договор в одностороннем порядке с уведомлением Пользователя за 10 (десять) календарных дней, если иное не предусмотрено обстоятельствами, требующими незамедлительного прекращения доступа.</p>

        <div className="section-title"><span className="section-num">6</span><h2>Права и обязанности сторон</h2></div>
        <h3>Администрация вправе:</h3>
        <ul>
          <li>приостановить или прекратить доступ Пользователя к Сервису при нарушении условий настоящего Договора;</li>
          <li>вносить изменения в функционал Сервиса без предварительного уведомления;</li>
          <li>изменять тарифные планы — изменения не распространяются на действующие оплаченные периоды.</li>
        </ul>
        <h3>Пользователь обязуется:</h3>
        <ul>
          <li>не передавать доступ к аккаунту третьим лицам;</li>
          <li>использовать Сервис исключительно в законных целях;</li>
          <li>не осуществлять массовый сбор (парсинг) данных из Сервиса.</li>
        </ul>

        <div className="section-title"><span className="section-num">7</span><h2>Ответственность сторон</h2></div>
        <p>Администрация не несёт ответственности за временную недоступность Сервиса, вызванную техническими сбоями, плановыми работами или обстоятельствами непреодолимой силы. Администрация не гарантирует трудоустройство и не является работодателем или кадровым агентством — Сервис предоставляет исключительно информационный доступ к кастинговым объявлениям.</p>
        <p>По всем вопросам, связанным с исполнением Договора, обращайтесь на: <a href={`mailto:${EMAIL}`}>{EMAIL}</a>.</p>
      </div>
    </LegalLayout>
  );
}

/* ── Privacy ───────────────────────────────────────────────────────────── */

export function PrivacyPage() {
  return (
    <LegalLayout title="Политика конфиденциальности">
      <div className="legal">
        <div className="meta">
          <strong>{OWNER}</strong><br />
          ИНН: {INN} · ОГРНИП: {OGRNIP}<br />
          Сайт: <a href={SITE_URL}>{SITE_URL}</a> · Редакция от {DATE}
        </div>

        <p>Настоящая Политика конфиденциальности определяет порядок обработки персональных данных пользователей Сервиса «Model Promo Agency» в соответствии с Федеральным законом № 152-ФЗ «О персональных данных».</p>

        <div className="section-title"><span className="section-num">1</span><h2>Оператор персональных данных</h2></div>
        <p>{OWNER}, ИНН: {INN}, ОГРНИП: {OGRNIP}.</p>
        <p>Контактный адрес: <a href={`mailto:${EMAIL}`}>{EMAIL}</a></p>

        <div className="section-title"><span className="section-num">2</span><h2>Собираемые данные</h2></div>
        <p>При использовании Сервиса Администрация обрабатывает следующие данные, передаваемые платформой Telegram:</p>
        <ul>
          <li><strong>Telegram ID</strong> — уникальный числовой идентификатор аккаунта;</li>
          <li><strong>Имя</strong> — имя (и при наличии фамилия), указанные в профиле Telegram;</li>
          <li><strong>Username</strong> — публичный псевдоним (@username), если установлен;</li>
          <li><strong>Данные анкеты</strong> — город, категория занятости, параметры внешности, указанные самим Пользователем при регистрации в боте.</li>
        </ul>
        <p>Администрация не собирает платёжные данные: обработка платежей осуществляется оператором ЮKassa, который несёт самостоятельную ответственность за защиту платёжной информации.</p>

        <div className="section-title"><span className="section-num">3</span><h2>Цели обработки данных</h2></div>
        <ul>
          <li>идентификация Пользователя и предоставление доступа к Сервису;</li>
          <li>персонализация подборки кастингов по параметрам анкеты;</li>
          <li>отправка уведомлений о новых вакансиях через Telegram-бота;</li>
          <li>обработка обращений в службу поддержки;</li>
          <li>исполнение обязательств по Договору оферты.</li>
        </ul>

        <div className="section-title"><span className="section-num">4</span><h2>Хранение и защита данных</h2></div>
        <p>Данные хранятся на серверах, расположенных на территории Российской Федерации. Администрация применяет технические и организационные меры для защиты данных от несанкционированного доступа, в том числе шифрование передачи данных по протоколу HTTPS.</p>
        <p>Данные хранятся в течение срока действия Договора и в течение 3 лет после его прекращения, если иное не предусмотрено законодательством.</p>

        <div className="section-title"><span className="section-num">5</span><h2>Передача данных третьим лицам</h2></div>
        <p>Администрация не передаёт персональные данные Пользователей третьим лицам, за исключением:</p>
        <ul>
          <li>случаев, предусмотренных законодательством РФ;</li>
          <li>платёжного оператора ЮKassa — исключительно в объёме, необходимом для обработки транзакций.</li>
        </ul>

        <div className="section-title"><span className="section-num">6</span><h2>Права пользователя</h2></div>
        <p>Пользователь вправе в любой момент:</p>
        <ul>
          <li>запросить информацию об обрабатываемых данных;</li>
          <li>потребовать уточнения, блокирования или удаления своих данных;</li>
          <li>отозвать согласие на обработку данных — в этом случае доступ к Сервису будет прекращён.</li>
        </ul>
        <p>Для реализации прав направьте запрос на: <a href={`mailto:${EMAIL}`}>{EMAIL}</a>. Обращения рассматриваются в срок не более 30 дней.</p>

        <div className="section-title"><span className="section-num">7</span><h2>Изменения политики</h2></div>
        <p>Администрация вправе вносить изменения в настоящую Политику. Актуальная редакция всегда доступна по адресу <a href={SITE_URL + "/privacy"}>{SITE_URL}/privacy</a>. Продолжение использования Сервиса после публикации изменений означает согласие с новой редакцией.</p>
      </div>
    </LegalLayout>
  );
}

/* ── Contacts ──────────────────────────────────────────────────────────── */

export function ContactsPage() {
  return (
    <LegalLayout title="Контакты">
      <div className="legal">
        <div className="meta">
          Если у вас возникли вопросы по работе Сервиса, оплате или удалению данных — напишите нам. Мы отвечаем в течение 1 рабочего дня.
        </div>

        <div className="section-title"><span className="section-num">1</span><h2>Владелец сервиса</h2></div>
        <p>{OWNER}</p>
        <ul>
          <li><strong>ИНН:</strong> {INN}</li>
          <li><strong>ОГРНИП:</strong> {OGRNIP}</li>
        </ul>

        <div className="section-title"><span className="section-num">2</span><h2>Способы связи</h2></div>
        <p><strong>Email:</strong> <a href={`mailto:${EMAIL}`}>{EMAIL}</a><br />
        Для вопросов по оплате, удалению аккаунта, жалоб и юридических обращений.</p>
        <p><strong>Telegram-бот:</strong> <a href={BOT_URL}>@{BOT_USERNAME}</a><br />
        Для вопросов по работе Сервиса и технической поддержки.</p>

        <div className="section-title"><span className="section-num">3</span><h2>Реквизиты</h2></div>
        <ul>
          <li><strong>Полное наименование:</strong> {OWNER}</li>
          <li><strong>ИНН:</strong> {INN}</li>
          <li><strong>ОГРНИП:</strong> {OGRNIP}</li>
          <li><strong>Сайт:</strong> <a href={SITE_URL}>{SITE_URL}</a></li>
          <li><strong>Email:</strong> <a href={`mailto:${EMAIL}`}>{EMAIL}</a></li>
        </ul>

        <div className="section-title"><span className="section-num">4</span><h2>Документы</h2></div>
        <ul>
          <li><a href="/offer">Публичная оферта</a></li>
          <li><a href="/privacy">Политика конфиденциальности</a></li>
        </ul>
      </div>
    </LegalLayout>
  );
}
