# Спецификация: категории, per-category анкеты, autocomplete и settings

**Дата:** 2026-05-07
**Автор:** Claude Opus 4.7
**Статус:** черновик, ожидает ревью пользователя

## Проблема

Текущий Mini App — единая 6-шаговая анкета `ActorProfile` под актёров/моделей.
Бизнес расширяется на 3 новых направления (Event, Разнорабочие,
Администрирование), у каждого свои поля и подкатегории. Юзеру
непонятно, для какого направления он регистрируется, а полей под
другие направления вообще нет.

## Цель

Дать юзеру при первом открытии Mini App опросник «какие направления
интересуют» (multi-select из 4), для каждого выбранного направления —
свою независимую форму со своими полями и подкатегориями. Между
одноимёнными полями разных категорий — autocomplete-подсказки. Через
settings можно вкл/выкл категорию или изменить уже заполненную анкету.

## Не цель

- Матчинг и LLM-extract под новые категории — отдельным спеком.
  В этом спеке матчер продолжает работать только для категории
  `creative` (через адаптер на новую таблицу `creative_profile`).
- Перенос старых `ActorProfile` данных в `creative_profile` —
  не делаем. Старые юзеры проходят анкету заново.
- Админ-CRUD категорий — категории фиксированы в коде как enum.

## Принятые решения

1. **Подход к формам**: независимые формы per category +
   autocomplete-подсказки между одноимёнными полями.
2. **Старые юзеры**: после деплоя считаем `actor_profile.completed_at`
   irrelevant. На уровне API `GET /api/me.subscriptions` для них пуст,
   и они увидят опрос категорий как новые. Старая `actor_profile`
   таблица остаётся в БД read-only для аудита.
3. **Storage**: 4 отдельные таблицы (`creative_profile`,
   `event_profile`, `general_profile`, `admin_profile`). У каждой
   FK user_id UNIQUE, свой `completed_at`.
4. **Subscription**: отдельная таблица `user_category_subscription`
   (multi-row), вкл/выкл флагом без удаления данных профиля.
5. **Категории как enum в коде**: `creative`, `event`, `general`,
   `admin`. 4 значения. Изменение списка = миграция + код.

## Категории и подкатегории (work_types)

| Категория | Подкатегории |
|-----------|--------------|
| creative (Творческие) | актёры, модели — детализация через существующие справочники `project_types`/`role_types`, отдельное поле `work_types` не вводим |
| event (Event-персонал) | `work_types[]` ∈ {hostess, promo_model, animator} |
| general (Разнорабочие) | `work_types[]` ∈ {helper, cleaning, loader} |
| admin (Администрирование) | `work_types[]` ∈ {registration_operator, supervisor} |

## Поля по категориям

### creative_profile (Творческие позиции)

Полный набор полей текущего `actor_profile`:
- ФИО, пол, город, готовность к разъездам, актуальный возраст,
  играемый возраст
- Типы проектов, типы ролей, минимальная ставка, флаги
  (negotiable/non-commercial/agency)
- Рост, размер одежды, размер обуви, этнотип, телосложение,
  цвет волос, длина волос
- Опыт, образование, налоговый статус
- Цвет глаз, особые приметы, навыки (спорт/танец/вокал/инструменты)
- Портфолио, видео, проф. ссылка, телефон, VK, **telegram**, email

### event_profile (Event-персонал)

- ФИО, пол, город, готовность к разъездам, актуальный возраст
- Минимальная ставка, флаги (negotiable, non-commercial)
- Рост, размер одежды, размер обуви, этнотип, телосложение,
  цвет волос, длина волос
- `work_types[]` — `{hostess, promo_model, animator}`
- `has_experience BOOL`, налоговый статус
- Фото портфолио, видео портфолио, телефон, VK, telegram, email

### general_profile (Разнорабочие)

- ФИО, пол, город, готовность к разъездам, актуальный возраст
- Минимальная ставка
- Рост (опц.), `physical_fitness` enum `{light, medium, heavy}` (опц.)
- `has_experience BOOL`, `work_types[]` — `{helper, cleaning, loader}`
- Налоговый статус, телефон, VK, telegram, email

### admin_profile (Администрирование)

- ФИО, пол, город, готовность к разъездам, актуальный возраст
- Минимальная ставка
- Образование, `has_experience BOOL`, `work_types[]` —
  `{registration_operator, supervisor}`
- Налоговый статус, телефон, VK, telegram, email

## Канонические поля для autocomplete

Имя поля одинаковое в нескольких таблицах → autocomplete подтягивает
значения из других таблиц юзера:

- Все категории: `full_name`, `gender`, `city`, `ready_for_travel`,
  `actual_age`, `min_rate`, `tax_status`, `phone`, `vk_url`,
  `telegram_user`, `email`
- creative + event: `height_cm`, `clothing_size`, `shoe_size`,
  `ethnicity`, `body_type`, `hair_color`, `hair_length`,
  `portfolio_url`, `video_url`
- general + admin + event: `has_experience`
- general + admin: `work_types` (значения разные, но поле тоже
  multi-select — UX можно не подсказывать, либо подсказывать но фронт
  фильтрует допустимые в текущей категории)

## Схема БД

### Миграция 0012: user_category_subscription

```sql
CREATE TABLE user_category_subscription (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category VARCHAR(16) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_category CHECK (category IN ('creative','event','general','admin')),
  CONSTRAINT uq_user_category UNIQUE (user_id, category)
);
CREATE INDEX ix_user_category_subscription_user_id ON user_category_subscription (user_id);
```

### Миграция 0013: per-category profile tables

4 таблицы — `creative_profile`, `event_profile`, `general_profile`,
`admin_profile`. У каждой:
- `id BIGSERIAL PK`
- `user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE`
- `completed_at TIMESTAMPTZ NULL` — анкета этой категории завершена
- `created_at`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- Колонки полей по списку выше. Все nullable пока `completed_at IS NULL`,
  валидация completeness — на уровне Pydantic при `complete`.

`creative_profile` копирует структуру колонок старой `actor_profile` +
добавляет `telegram_user VARCHAR(64)`.

Старая `actor_profile` не модифицируется и не удаляется.

## API

Файл `api/main.py`:

| Эндпоинт | Метод | Назначение |
|---|---|---|
| `/api/me` | GET | расширяется: `{user, is_admin, subscriptions: [{category, enabled, profile_completed}]}` |
| `/api/subscriptions` | POST | `{categories: [...]}` → создаёт строки, идемпотентно. Возвращает актуальный список. |
| `/api/subscriptions/{category}` | PATCH | `{enabled: bool}` |
| `/api/profile/{category}` | GET | возвращает профиль категории или пусто |
| `/api/profile/{category}` | PUT | upsert (draft-save, без проверки completeness) |
| `/api/profile/{category}/complete` | POST | валидирует Pydantic, ставит `completed_at=now()`, шлёт нотификацию |
| `/api/profile/suggestions` | GET | `{<canonical_field>: [<value>, ...]}` для всех профилей юзера |

`api/schemas.py` — 4 Pydantic модели (Creative/Event/General/Admin
ProfileSchema) + `SubscriptionSchema` + `SuggestionsSchema`.

`db/repository.py` функции:
`get_subscriptions(user_id)`, `set_subscriptions(user_id, categories)`,
`toggle_subscription(user_id, category, enabled)`,
`get_profile(user_id, category)`, `upsert_profile(user_id, category, data)`,
`complete_profile(user_id, category)`, `get_suggestions(user_id)`.

## Frontend (webapp/src/)

### State machine

```
survey → menu → form(category) → menu
                              ↘ menu → settings → menu
                              ↘ menu → addCategory(survey-mini) → menu
```

Состояние в `App.tsx` — string union `'survey' | 'menu' | 'form:creative' |
'form:event' | 'form:general' | 'form:admin' | 'settings' | 'add'`.

### Новые компоненты

- `src/components/CategorySurveyScreen.tsx` — multi-select из 4 категорий
  с описаниями, кнопка «Продолжить» → `POST /api/subscriptions`.
- `src/components/CategoryMenuScreen.tsx` — главное меню после опроса.
  Список подписанных категорий со статусом «✅/⚠️», кнопки
  «+ Добавить категорию» и «⚙️ Настройки».
- `src/components/SettingsScreen.tsx` — все 4 категории с тогглами
  enabled/disabled и «изменить анкету».
- `src/forms/CreativeForm.tsx`, `EventForm.tsx`, `GeneralForm.tsx`,
  `AdminForm.tsx` — multi-step wizards под свой набор полей.
- `src/fields/` — shared field components с встроенным
  autocomplete: `<TextFieldWithAutocomplete field="city" ... />`,
  `<NumberFieldWithAutocomplete field="actual_age" ... />`, и т. д.
- `src/api.ts` — обёртки под все новые эндпоинты.

### Autocomplete UX

При монтировании `CategoryMenuScreen` фронт вызывает
`GET /api/profile/suggestions`, кэширует ответ в React state
(или `React Context`), пробрасывает в формы. Поле при focus показывает
dropdown со значениями, что юзер уже вводил в одноимённых полях
других своих профилей. Клик — подставляется, либо ввод своего.

### GREETING (bot/handlers.py)

Обновляется текст:
- «Event-персонал: хостес, промо-модели, **аниматоры**»
- «Администрирование: операторы регистрации, **супервайзеры**»

## Cutover старого матчинга

`db/matching.py` сейчас читает `actor_profile`. Меняем на
`creative_profile` (поля идентичны, только новая таблица). Только юзеры
с `subscriptions.creative.enabled=TRUE AND creative_profile.completed_at IS NOT NULL`
получают нотификации. Юзеры с другими категориями notif-флоу не получают —
матчинг под них отдельным спеком.

## Тесты

`tests/test_schemas_per_category.py` (новый):
- Pydantic-валидация 4 моделей: required fields на complete-этапе,
  валидные/невалидные enum значения, multi-select work_types.

`tests/test_suggestions.py` (новый):
- Чистая функция `_collect_suggestions(profiles_dict)` —
  принимает dict профилей юзера, возвращает `{field: [values]}`,
  dedupe, сортировка по `updated_at DESC`.

Существующие `test_matching.py` адаптируются под `creative_profile`.

## Риски и митигации

| Риск | Митигация |
|---|---|
| Размер фичи большой → много кода за один PR | Разбивается на 6 этапов в плане; каждый — отдельный коммит/PR при необходимости. |
| Дубли полей в 4 формах → копипаст | Shared field-компоненты в `src/fields/`. Один источник правды для каждого канонического поля. |
| Юзеры со старым `actor_profile.completed_at` после деплоя обнаружат, что им снова показывают опрос | Принимаем (явно решено). После деплоя бот может разово отправить им сообщение «обновили анкету, пройди заново» — рассмотреть в этапе 6. |
| `physical_fitness` enum не утверждён бизнесом | Делаем 3 значения light/medium/heavy с lable «до 5 кг / 5–20 / 20+». Пересмотр после первой обратной связи. |
| Матчер после cutover работает только под `creative` — Event/General/Admin юзеры не получают нотификаций | Принимаем явно. Покрывается следующим спеком. |
| `work_types` в creative — у нас этих значений сейчас нет (там `project_types/role_types`) | В creative оставляем `project_types`/`role_types` как было, поле `work_types` только в event/general/admin. |

## Этапы реализации (для writing-plans)

1. **Миграции и модели**: 0012 + 0013 + SQLAlchemy-модели
   (`UserCategorySubscription`, `CreativeProfile`, `EventProfile`,
   `GeneralProfile`, `AdminProfile`).
2. **Repository + Pydantic**: функции в `db/repository.py`,
   схемы в `api/schemas.py`.
3. **API эндпоинты**: `/api/me` расширение, `/api/subscriptions*`,
   `/api/profile/{category}*`, `/api/profile/suggestions`.
4. **Фронт — base navigation**: state machine, CategorySurveyScreen,
   CategoryMenuScreen.
5. **Фронт — формы**: CreativeForm (рефакторинг существующего Step1-6),
   EventForm, GeneralForm, AdminForm. Shared field components.
6. **Фронт — settings + autocomplete**: SettingsScreen,
   `<*WithAutocomplete>` компоненты, `GET /api/profile/suggestions`
   интеграция.
7. **Cutover + cleanup**: GREETING обновление,
   `db/matching.py` переключение на `creative_profile`,
   удаление мёртвого кода, что читал из `actor_profile`.

## Альтернативы (отклонено)

- **Storage A** (одна расширенная `actor_profile` со всеми колонками):
  не поддерживает «у меня в Творческих один телефон, в Event другой».
- **Storage C** (JSONB `category_data`): теряем DB-валидацию,
  autocomplete сложнее, типизирование уезжает в код. Профит
  «без миграции под новую категорию» неактуален — категории редко
  меняются.
- **Категории как CRUD-сущность**: over-engineering, не нужно.
  Категории фиксированы 4-мя enum-значениями.
- **Subscription через bool-колонки на User** (`is_creative`,
  `is_event`, ...): не масштабируется, нет аудита `enabled` toggle,
  нет created_at per category.
