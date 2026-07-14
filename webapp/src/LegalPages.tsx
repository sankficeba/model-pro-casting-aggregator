import { useLang } from "./i18n";

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
  const { t, lang, setLang } = useLang();

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
            { label: t("Оферта", "Offer"),   href: "/offer"    },
            { label: t("Конфиденциальность", "Privacy"), href: "/privacy" },
            { label: t("Контакты", "Contacts"), href: "/contacts" },
          ].map(({ label, href }) => (
            <a key={href} href={href} style={{
              fontSize: 12, letterSpacing: 1, textTransform: "uppercase",
              color: window.location.pathname === href ? GOLD : "rgba(255,255,255,.45)",
              textDecoration: "none",
              transition: "color .2s",
            }}>{label}</a>
          ))}
          <button
            onClick={() => setLang(lang === "ru" ? "en" : "ru")}
            style={{
              fontSize: 12, letterSpacing: 1, textTransform: "uppercase",
              color: "rgba(255,255,255,.45)", background: "none", border: "none",
              cursor: "pointer", fontFamily: SANS, padding: 0,
            }}
          >
            {lang === "ru" ? "EN" : "RU"}
          </button>
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
          © {new Date().getFullYear()} Model Promo Agency · {t(OWNER, "Individual Entrepreneur Semyon Kirillovich Ryabov")}
        </div>
        <div style={{ display: "flex", gap: 20 }}>
          {[
            { label: t("Оферта", "Offer"),   href: "/offer"    },
            { label: t("Конфиденциальность", "Privacy"), href: "/privacy" },
            { label: t("Контакты", "Contacts"), href: "/contacts" },
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
  const { t } = useLang();

  return (
    <LegalLayout title={t("Публичная оферта", "Public Offer")}>
      <div className="legal">
        <div className="meta">
          <strong>{t(OWNER, "Individual Entrepreneur Semyon Kirillovich Ryabov")}</strong><br />
          {t("ИНН", "Tax ID (INN)")}: {INN} · {t("ОГРНИП", "OGRNIP")}: {OGRNIP}<br />
          {t("Сайт", "Website")}: <a href={SITE_URL}>{SITE_URL}</a> · {t("Редакция от", "Revision dated")} {t(DATE, "June 17, 2026")}
        </div>

        <div className="section-title"><span className="section-num">1</span><h2>{t("Термины и определения", "Definitions")}</h2></div>
        <p><strong>{t("Акцепт", "Acceptance")}</strong> — {t(
          "полное безоговорочное принятие условий настоящей оферты путём оплаты подписки или начала использования платного функционала Сервиса.",
          "the complete and unconditional acceptance of the terms of this offer by paying for a subscription or by beginning to use the Service's paid functionality.",
        )}</p>
        <p><strong>{t("Договор", "Agreement")}</strong> — {t(
          "договор о предоставлении доступа к Сервису, заключённый между Администрацией и Пользователем на условиях настоящей оферты.",
          "the agreement for the provision of access to the Service, concluded between the Administration and the User on the terms of this offer.",
        )}</p>
        <p><strong>{t("Пользователь", "User")}</strong> — {t(
          "дееспособное физическое лицо старше 18 лет, совершившее Акцепт.",
          "a legally capable individual over the age of 18 who has performed the Acceptance.",
        )}</p>
        <p><strong>{t("Сервис", "Service")}</strong> — {t("агрегатор кастингов и вакансий «Model Promo Agency», доступный через Telegram-бота", "the “Model Promo Agency” casting and job aggregator, accessible via the Telegram bot")} <a href={BOT_URL}>@{BOT_USERNAME}</a> {t("и мини-приложение по адресу", "and the mini-app at")} <a href={SITE_URL + "/app"}>{SITE_URL}/app</a>.</p>
        <p><strong>{t("Администрация", "Administration")}</strong> — {t(OWNER, "Individual Entrepreneur Semyon Kirillovich Ryabov")}, {t("владелец и оператор Сервиса.", "the owner and operator of the Service.")}</p>

        <div className="section-title"><span className="section-num">2</span><h2>{t("Предмет соглашения", "Subject of the Agreement")}</h2></div>
        <p>{t(
          "Администрация предоставляет Пользователю доступ к платному функционалу Сервиса: просмотр актуальных кастингов и вакансий для актёров, моделей и event-персонала, агрегированных из 200+ Telegram-каналов; возможность откликаться на проекты; получение уведомлений о новых предложениях в режиме реального времени.",
          "The Administration provides the User with access to the Service's paid functionality: viewing current castings and job openings for actors, models, and event staff, aggregated from 200+ Telegram channels; the ability to respond to projects; and receiving real-time notifications of new offers.",
        )}</p>
        <p>{t("Авторизация в Сервисе осуществляется исключительно через Telegram. Доступ к мини-приложению возможен только через официального Telegram-бота", "Authorization in the Service is carried out exclusively via Telegram. Access to the mini-app is only possible through the official Telegram bot")} <a href={BOT_URL}>@{BOT_USERNAME}</a>.</p>

        <div className="section-title"><span className="section-num">3</span><h2>{t("Порядок принятия оферты", "Procedure for Accepting the Offer")}</h2></div>
        <p>{t(
          "Акцептом настоящей оферты является совершение оплаты подписки через платёжную форму внутри мини-приложения. Совершая Акцепт, Пользователь подтверждает:",
          "Acceptance of this offer is constituted by paying for a subscription through the payment form inside the mini-app. By performing the Acceptance, the User confirms:",
        )}</p>
        <ul>
          <li>{t("полное и безоговорочное согласие с условиями настоящей оферты;", "full and unconditional agreement with the terms of this offer;")}</li>
          <li>{t("свою полную дееспособность и достижение возраста 18 лет;", "that they have full legal capacity and have reached the age of 18;")}</li>
          <li>{t("ознакомление с Политикой конфиденциальности.", "that they have read and reviewed the Privacy Policy.")}</li>
        </ul>

        <div className="section-title"><span className="section-num">4</span><h2>{t("Стоимость и порядок оплаты", "Cost and Payment Procedure")}</h2></div>
        <p>{t(
          "Стоимость подписки определяется выбранным тарифным планом, актуальный перечень которых отображается в мини-приложении в разделе «Подписка». Оплата производится единовременно за выбранный период.",
          "The subscription cost is determined by the selected pricing plan; the current list of plans is displayed in the mini-app in the “Subscription” section. Payment is made as a one-time charge for the selected period.",
        )}</p>
        <p>{t("Приём платежей осуществляется через платёжный сервис ЮKassa (", "Payments are processed through the YooKassa payment service (")}<a href="https://yookassa.ru" target="_blank" rel="noopener noreferrer">yookassa.ru</a>{t("). Оплата доступна только авторизованным Пользователям внутри мини-приложения.", "). Payment is available only to authorized Users inside the mini-app.")}</p>
        <p>{t(
          "Подписка активируется автоматически после подтверждения платежа. Возврат денежных средств за неиспользованный остаток периода подписки не производится, за исключением случаев, предусмотренных действующим законодательством РФ.",
          "The subscription is activated automatically upon payment confirmation. No refund is issued for the unused portion of the subscription period, except in cases provided for by the applicable legislation of the Russian Federation.",
        )}</p>

        <div className="section-title"><span className="section-num">5</span><h2>{t("Срок действия договора", "Term of the Agreement")}</h2></div>
        <p>{t(
          "Договор вступает в силу с момента Акцепта и действует в течение оплаченного периода подписки. Пользователь вправе в любой момент прекратить использование Сервиса — доступ сохраняется до окончания оплаченного периода.",
          "The Agreement takes effect from the moment of Acceptance and remains in force for the duration of the paid subscription period. The User may discontinue use of the Service at any time — access remains available until the end of the paid period.",
        )}</p>
        <p>{t(
          "Администрация вправе расторгнуть Договор в одностороннем порядке с уведомлением Пользователя за 10 (десять) календарных дней, если иное не предусмотрено обстоятельствами, требующими незамедлительного прекращения доступа.",
          "The Administration has the right to terminate the Agreement unilaterally by notifying the User 10 (ten) calendar days in advance, unless circumstances requiring the immediate termination of access dictate otherwise.",
        )}</p>

        <div className="section-title"><span className="section-num">6</span><h2>{t("Права и обязанности сторон", "Rights and Obligations of the Parties")}</h2></div>
        <h3>{t("Администрация вправе:", "The Administration has the right to:")}</h3>
        <ul>
          <li>{t("приостановить или прекратить доступ Пользователя к Сервису при нарушении условий настоящего Договора;", "suspend or terminate the User's access to the Service in the event of a violation of the terms of this Agreement;")}</li>
          <li>{t("вносить изменения в функционал Сервиса без предварительного уведомления;", "make changes to the Service's functionality without prior notice;")}</li>
          <li>{t("изменять тарифные планы — изменения не распространяются на действующие оплаченные периоды.", "change pricing plans — such changes do not apply to already-paid, active subscription periods.")}</li>
        </ul>
        <h3>{t("Пользователь обязуется:", "The User undertakes to:")}</h3>
        <ul>
          <li>{t("не передавать доступ к аккаунту третьим лицам;", "not transfer access to their account to third parties;")}</li>
          <li>{t("использовать Сервис исключительно в законных целях;", "use the Service exclusively for lawful purposes;")}</li>
          <li>{t("не осуществлять массовый сбор (парсинг) данных из Сервиса.", "not carry out mass collection (scraping) of data from the Service.")}</li>
        </ul>

        <div className="section-title"><span className="section-num">7</span><h2>{t("Ответственность сторон", "Liability of the Parties")}</h2></div>
        <p>{t(
          "Администрация не несёт ответственности за временную недоступность Сервиса, вызванную техническими сбоями, плановыми работами или обстоятельствами непреодолимой силы. Администрация не гарантирует трудоустройство и не является работодателем или кадровым агентством — Сервис предоставляет исключительно информационный доступ к кастинговым объявлениям.",
          "The Administration is not liable for temporary unavailability of the Service caused by technical failures, scheduled maintenance, or force majeure circumstances. The Administration does not guarantee employment and is not an employer or a recruitment agency — the Service provides solely informational access to casting listings.",
        )}</p>
        <p>{t("По всем вопросам, связанным с исполнением Договора, обращайтесь на:", "For all matters related to the performance of the Agreement, please contact:")} <a href={`mailto:${EMAIL}`}>{EMAIL}</a>.</p>
      </div>
    </LegalLayout>
  );
}

/* ── Privacy ───────────────────────────────────────────────────────────── */

export function PrivacyPage() {
  const { t } = useLang();

  return (
    <LegalLayout title={t("Политика конфиденциальности", "Privacy Policy")}>
      <div className="legal">
        <div className="meta">
          <strong>{t(OWNER, "Individual Entrepreneur Semyon Kirillovich Ryabov")}</strong><br />
          {t("ИНН", "Tax ID (INN)")}: {INN} · {t("ОГРНИП", "OGRNIP")}: {OGRNIP}<br />
          {t("Сайт", "Website")}: <a href={SITE_URL}>{SITE_URL}</a> · {t("Редакция от", "Revision dated")} {t(DATE, "June 17, 2026")}
        </div>

        <p>{t(
          "Настоящая Политика конфиденциальности определяет порядок обработки персональных данных пользователей Сервиса «Model Promo Agency» в соответствии с Федеральным законом № 152-ФЗ «О персональных данных».",
          "This Privacy Policy defines the procedure for processing the personal data of users of the “Model Promo Agency” Service in accordance with Federal Law No. 152-FZ “On Personal Data.”",
        )}</p>

        <div className="section-title"><span className="section-num">1</span><h2>{t("Оператор персональных данных", "Personal Data Controller")}</h2></div>
        <p>{t(OWNER, "Individual Entrepreneur Semyon Kirillovich Ryabov")}, {t("ИНН", "Tax ID (INN)")}: {INN}, {t("ОГРНИП", "OGRNIP")}: {OGRNIP}.</p>
        <p>{t("Контактный адрес", "Contact address")}: <a href={`mailto:${EMAIL}`}>{EMAIL}</a></p>

        <div className="section-title"><span className="section-num">2</span><h2>{t("Собираемые данные", "Data Collected")}</h2></div>
        <p>{t("При использовании Сервиса Администрация обрабатывает следующие данные, передаваемые платформой Telegram:", "When using the Service, the Administration processes the following data transmitted by the Telegram platform:")}</p>
        <ul>
          <li><strong>{t("Telegram ID", "Telegram ID")}</strong> — {t("уникальный числовой идентификатор аккаунта;", "the unique numeric identifier of the account;")}</li>
          <li><strong>{t("Имя", "Name")}</strong> — {t("имя (и при наличии фамилия), указанные в профиле Telegram;", "the first name (and last name, if provided) specified in the Telegram profile;")}</li>
          <li><strong>{t("Username", "Username")}</strong> — {t("публичный псевдоним (@username), если установлен;", "the public handle (@username), if set;")}</li>
          <li><strong>{t("Данные анкеты", "Profile data")}</strong> — {t("город, категория занятости, параметры внешности, указанные самим Пользователем при регистрации в боте.", "city, occupation category, and physical characteristics provided by the User during registration in the bot.")}</li>
        </ul>
        <p>{t(
          "Администрация не собирает платёжные данные: обработка платежей осуществляется оператором ЮKassa, который несёт самостоятельную ответственность за защиту платёжной информации.",
          "The Administration does not collect payment data: payment processing is carried out by the YooKassa operator, which bears independent responsibility for protecting payment information.",
        )}</p>

        <div className="section-title"><span className="section-num">3</span><h2>{t("Цели обработки данных", "Purposes of Data Processing")}</h2></div>
        <ul>
          <li>{t("идентификация Пользователя и предоставление доступа к Сервису;", "identifying the User and providing access to the Service;")}</li>
          <li>{t("персонализация подборки кастингов по параметрам анкеты;", "personalizing the selection of castings based on profile parameters;")}</li>
          <li>{t("отправка уведомлений о новых вакансиях через Telegram-бота;", "sending notifications about new job openings via the Telegram bot;")}</li>
          <li>{t("обработка обращений в службу поддержки;", "processing inquiries to support;")}</li>
          <li>{t("исполнение обязательств по Договору оферты.", "fulfilling obligations under the Offer Agreement.")}</li>
        </ul>

        <div className="section-title"><span className="section-num">4</span><h2>{t("Хранение и защита данных", "Data Storage and Protection")}</h2></div>
        <p>{t(
          "Данные хранятся на серверах, расположенных на территории Российской Федерации. Администрация применяет технические и организационные меры для защиты данных от несанкционированного доступа, в том числе шифрование передачи данных по протоколу HTTPS.",
          "Data is stored on servers located within the territory of the Russian Federation. The Administration applies technical and organizational measures to protect data from unauthorized access, including encryption of data transmission via the HTTPS protocol.",
        )}</p>
        <p>{t(
          "Данные хранятся в течение срока действия Договора и в течение 3 лет после его прекращения, если иное не предусмотрено законодательством.",
          "Data is retained for the duration of the Agreement and for 3 years after its termination, unless otherwise provided by law.",
        )}</p>

        <div className="section-title"><span className="section-num">5</span><h2>{t("Передача данных третьим лицам", "Disclosure of Data to Third Parties")}</h2></div>
        <p>{t("Администрация не передаёт персональные данные Пользователей третьим лицам, за исключением:", "The Administration does not disclose Users' personal data to third parties, except:")}</p>
        <ul>
          <li>{t("случаев, предусмотренных законодательством РФ;", "in cases provided for by the legislation of the Russian Federation;")}</li>
          <li>{t("платёжного оператора ЮKassa — исключительно в объёме, необходимом для обработки транзакций.", "the YooKassa payment operator — solely to the extent necessary to process transactions.")}</li>
        </ul>

        <div className="section-title"><span className="section-num">6</span><h2>{t("Права пользователя", "User Rights")}</h2></div>
        <p>{t("Пользователь вправе в любой момент:", "The User has the right, at any time, to:")}</p>
        <ul>
          <li>{t("запросить информацию об обрабатываемых данных;", "request information about the data being processed;")}</li>
          <li>{t("потребовать уточнения, блокирования или удаления своих данных;", "demand the correction, blocking, or deletion of their data;")}</li>
          <li>{t("отозвать согласие на обработку данных — в этом случае доступ к Сервису будет прекращён.", "withdraw consent to data processing — in which case access to the Service will be terminated.")}</li>
        </ul>
        <p>{t("Для реализации прав направьте запрос на:", "To exercise these rights, send a request to:")} <a href={`mailto:${EMAIL}`}>{EMAIL}</a>. {t("Обращения рассматриваются в срок не более 30 дней.", "Requests are reviewed within no more than 30 days.")}</p>

        <div className="section-title"><span className="section-num">7</span><h2>{t("Изменения политики", "Changes to the Policy")}</h2></div>
        <p>{t("Администрация вправе вносить изменения в настоящую Политику. Актуальная редакция всегда доступна по адресу", "The Administration has the right to make changes to this Policy. The current version is always available at")} <a href={SITE_URL + "/privacy"}>{SITE_URL}/privacy</a>. {t("Продолжение использования Сервиса после публикации изменений означает согласие с новой редакцией.", "Continued use of the Service after the publication of changes constitutes agreement with the new version.")}</p>
      </div>
    </LegalLayout>
  );
}

/* ── Contacts ──────────────────────────────────────────────────────────── */

export function ContactsPage() {
  const { t } = useLang();

  return (
    <LegalLayout title={t("Контакты", "Contacts")}>
      <div className="legal">
        <div className="meta">
          {t(
            "Если у вас возникли вопросы по работе Сервиса, оплате или удалению данных — напишите нам. Мы отвечаем в течение 1 рабочего дня.",
            "If you have questions about the Service, payments, or data deletion — write to us. We respond within 1 business day.",
          )}
        </div>

        <div className="section-title"><span className="section-num">1</span><h2>{t("Владелец сервиса", "Service Owner")}</h2></div>
        <p>{t(OWNER, "Individual Entrepreneur Semyon Kirillovich Ryabov")}</p>
        <ul>
          <li><strong>{t("ИНН", "Tax ID (INN)")}:</strong> {INN}</li>
          <li><strong>{t("ОГРНИП", "OGRNIP")}:</strong> {OGRNIP}</li>
        </ul>

        <div className="section-title"><span className="section-num">2</span><h2>{t("Способы связи", "Ways to Get in Touch")}</h2></div>
        <p><strong>{t("Email", "Email")}:</strong> <a href={`mailto:${EMAIL}`}>{EMAIL}</a><br />
        {t("Для вопросов по оплате, удалению аккаунта, жалоб и юридических обращений.", "For questions about payment, account deletion, complaints, and legal inquiries.")}</p>
        <p><strong>{t("Telegram-бот", "Telegram bot")}:</strong> <a href={BOT_URL}>@{BOT_USERNAME}</a><br />
        {t("Для вопросов по работе Сервиса и технической поддержки.", "For questions about the Service's operation and technical support.")}</p>

        <div className="section-title"><span className="section-num">3</span><h2>{t("Реквизиты", "Registration Details")}</h2></div>
        <ul>
          <li><strong>{t("Полное наименование", "Full legal name")}:</strong> {t(OWNER, "Individual Entrepreneur Semyon Kirillovich Ryabov")}</li>
          <li><strong>{t("ИНН", "Tax ID (INN)")}:</strong> {INN}</li>
          <li><strong>{t("ОГРНИП", "OGRNIP")}:</strong> {OGRNIP}</li>
          <li><strong>{t("Сайт", "Website")}:</strong> <a href={SITE_URL}>{SITE_URL}</a></li>
          <li><strong>{t("Email", "Email")}:</strong> <a href={`mailto:${EMAIL}`}>{EMAIL}</a></li>
        </ul>

        <div className="section-title"><span className="section-num">4</span><h2>{t("Документы", "Documents")}</h2></div>
        <ul>
          <li><a href="/offer">{t("Публичная оферта", "Public Offer")}</a></li>
          <li><a href="/privacy">{t("Политика конфиденциальности", "Privacy Policy")}</a></li>
        </ul>
      </div>
    </LegalLayout>
  );
}
