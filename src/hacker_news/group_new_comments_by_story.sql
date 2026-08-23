WITH RECURSIVE comment_chain AS (
    SELECT
        c.comment_id,
        c.parent_id,
        c.comment_id AS original_comment_id
    FROM comment c
    WHERE c.comment_id > $1 AND c.comment_id <= $2
    UNION ALL
    SELECT
        c.comment_id,
        c.parent_id,
        cc.original_comment_id
    FROM comment_chain cc
    JOIN comment c
    ON c.comment_id = cc.parent_id
),

comment_story AS (
    SELECT DISTINCT
        cc.original_comment_id AS comment_id,
        s.story_id
    FROM comment_chain cc
    JOIN story s
    ON s.story_id = cc.parent_id
),

orphan_comment AS (
    SELECT
        c.comment_id,
        NULL::BIGINT AS story_id
    FROM comment c
    WHERE c.comment_id > $1 AND c.comment_id <= $2
    AND NOT EXISTS (
          SELECT 1
          FROM comment_story cs
          WHERE cs.comment_id = c.comment_id
      )
)

SELECT story_id, jsonb_agg(comment_id ORDER BY comment_id) AS comment_id
FROM (
    SELECT story_id, comment_id FROM comment_story
    UNION ALL
    SELECT story_id, comment_id FROM orphan_comment
) t
GROUP BY story_id
ORDER BY story_id;