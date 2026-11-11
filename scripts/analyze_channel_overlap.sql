-- Насколько объявления одного канала уникальны: встречаются ли они в других каналах.
-- Запуск на проде (только чтение):
--   docker exec -i tg_parser_postgres psql -U tg_parser -d tg_parser \
--     -v ch=allcastingsgroup < scripts/analyze_channel_overlap.sql
-- :ch — username канала в нижнем регистре, без @.

\pset pager off
\echo '== Канал в таблице channels =='
SELECT id, username, tg_chat_id, active, added_at
FROM channels WHERE lower(username) = lower(:'ch');

-- Сообщения канала (кастинги) за всё время.
DROP TABLE IF EXISTS _src;
CREATE TEMP TABLE _src AS
SELECT m.*
FROM messages m
WHERE lower(m.tg_chat_username) = lower(:'ch')
   OR m.tg_chat_id = (SELECT tg_chat_id FROM channels WHERE lower(username) = lower(:'ch'));

\echo '== Объём: всего / кастингов / период =='
SELECT count(*) AS total,
       count(*) FILTER (WHERE is_casting) AS castings,
       min(received_at) AS first_seen, max(received_at) AS last_seen
FROM _src;

-- Точные дубли по text_hash (нормализованный текст): тот же пост есть в другом канале.
DROP TABLE IF EXISTS _exact;
CREATE TEMP TABLE _exact AS
SELECT s.id AS src_id,
       bool_or(o.received_at < s.received_at) AS other_was_first,
       array_agg(DISTINCT coalesce(o.tg_chat_username, o.tg_chat_id::text)) AS other_channels
FROM _src s
JOIN messages o ON o.text_hash = s.text_hash
               AND o.text_hash IS NOT NULL
               AND o.tg_chat_id <> s.tg_chat_id
WHERE s.is_casting
GROUP BY s.id;

\echo '== Кастинги канала: есть точная копия в других каналах? =='
SELECT (SELECT count(*) FROM _src WHERE is_casting) AS castings,
       count(*) AS found_elsewhere,
       count(*) FILTER (WHERE other_was_first) AS elsewhere_earlier,
       round(100.0 * count(*) / nullif((SELECT count(*) FROM _src WHERE is_casting), 0), 1) AS pct_dup
FROM _exact;

\echo '== Откуда копии (топ каналов-источников) =='
SELECT ch, count(*) AS n
FROM _exact, unnest(other_channels) AS ch
GROUP BY ch ORDER BY n DESC LIMIT 15;

\echo '== Сколько уведомлений юзерам ушло именно из этого канала (последние 30 дней) =='
SELECT count(*) AS notifications, count(DISTINCT n.user_id) AS users
FROM notifications n JOIN _src s ON s.id = n.message_id
WHERE n.sent_at > now() - interval '30 days';

-- Нечёткие дубли (перефразированные посты). Нужен pg_trgm:
--   CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- если ещё нет и есть права
\echo '== Нечёткие совпадения (pg_trgm, similarity > 0.6) среди уникальных по hash =='
SELECT count(DISTINCT s.id) AS fuzzy_found_elsewhere
FROM _src s
JOIN messages o ON o.tg_chat_id <> s.tg_chat_id
               AND o.is_casting
               AND o.received_at BETWEEN s.received_at - interval '7 days'
                                     AND s.received_at + interval '7 days'
               AND similarity(o.text, s.text) > 0.6
WHERE s.is_casting
  AND s.id NOT IN (SELECT src_id FROM _exact);

\echo '== 10 примеров уникальных постов канала (нигде больше нет) =='
SELECT s.id, s.received_at::date, s.category, left(regexp_replace(s.text, '\s+', ' ', 'g'), 160) AS text
FROM _src s
WHERE s.is_casting AND s.id NOT IN (SELECT src_id FROM _exact)
ORDER BY s.received_at DESC LIMIT 10;
