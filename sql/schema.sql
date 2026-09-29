-- ============================================================
-- SkillSync — MySQL setup (run once, as an admin user)
-- ============================================================

-- 1) Database
CREATE DATABASE IF NOT EXISTS defaultdb CHARACTER SET utf8mb4;

-- 2) A dedicated, low-privilege user for the app (least privilege:
--    the app only needs to create its table, read, insert and delete).
--    Change the password before running!
CREATE USER IF NOT EXISTS 'skillsync_user'@'localhost' IDENTIFIED BY 'change-this-password';
GRANT SELECT, INSERT, DELETE, CREATE ON defaultdb.* TO 'skillsync_user'@'localhost';
FLUSH PRIVILEGES;

-- 3) The table. The app also runs this automatically (CREATE TABLE IF NOT
--    EXISTS), so this step is optional — it is here for reference.
USE defaultdb;

CREATE TABLE IF NOT EXISTS comparisons (
    id              BIGINT        AUTO_INCREMENT PRIMARY KEY,
    session_id      CHAR(36)      NOT NULL,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resume_hash     CHAR(64)      NOT NULL,
    jd_snippet      VARCHAR(255)  NOT NULL,
    overall_score   DECIMAL(5,1)  NOT NULL,
    semantic_score  DECIMAL(5,1)  NOT NULL,
    skill_score     DECIMAL(5,1)  NOT NULL,
    semantic_weight DECIMAL(3,2)  NOT NULL,
    skill_weight    DECIMAL(3,2)  NOT NULL,
    matched_skills  TEXT          NOT NULL,
    missing_skills  TEXT          NOT NULL,
    extra_skills    TEXT          NOT NULL,
    INDEX idx_session_created (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================
-- Handy queries to check your data (and to talk about in interviews)
-- ============================================================

-- Latest 10 comparisons
SELECT id, created_at, LEFT(jd_snippet, 40) AS job, overall_score, semantic_score, skill_score
FROM comparisons ORDER BY id DESC LIMIT 10;

-- Average score and volume per day
SELECT DATE(created_at) AS day, COUNT(*) AS runs, ROUND(AVG(overall_score), 1) AS avg_score
FROM comparisons GROUP BY DATE(created_at) ORDER BY day DESC;

-- Score distribution buckets
SELECT CASE WHEN overall_score < 40 THEN 'weak (<40)'
            WHEN overall_score < 70 THEN 'moderate (40-70)'
            ELSE 'strong (70+)' END AS bucket,
       COUNT(*) AS runs
FROM comparisons GROUP BY bucket;