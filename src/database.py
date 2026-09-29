import hashlib
import json
import logging
import os
import ssl as ssl_lib
import tempfile
from collections import Counter

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

INSERT_SQL = """
INSERT INTO comparisons
    (session_id, resume_hash, jd_snippet, overall_score, semantic_score,
     skill_score, semantic_weight, skill_weight,
     matched_skills, missing_skills, extra_skills)
VALUES
    (%(session_id)s, %(resume_hash)s, %(jd_snippet)s, %(overall_score)s,
     %(semantic_score)s, %(skill_score)s, %(semantic_weight)s,
     %(skill_weight)s, %(matched_skills)s, %(missing_skills)s,
     %(extra_skills)s)
"""

HISTORY_SQL = """
SELECT id, created_at, jd_snippet, overall_score, semantic_score,
       skill_score, matched_skills, missing_skills
FROM comparisons
WHERE session_id = %s
ORDER BY created_at DESC, id DESC
LIMIT %s
"""

STATS_SQL = """
SELECT COUNT(*) AS total_comparisons,
       AVG(overall_score) AS avg_overall_score,
       COUNT(DISTINCT resume_hash) AS unique_resumes
FROM comparisons
"""

RECENT_MISSING_SQL = """
SELECT missing_skills FROM comparisons ORDER BY id DESC LIMIT %s
"""

DELETE_SESSION_SQL = "DELETE FROM comparisons WHERE session_id = %s"

# Remembers which databases already had their table created in this
# process, so we run CREATE TABLE IF NOT EXISTS once, not on every click.
_schema_ready = set()


# ---------------------------------------------------------------- config
def _to_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def load_config(secrets=None):
    """
    Builds a connection config dict, or returns None if the database is
    not configured (which simply turns the DB features off).

    `secrets` is an optional mapping — in the app we pass st.secrets["mysql"].
    Anything missing there is taken from environment variables instead
    (MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE,
    MYSQL_USE_SSL, MYSQL_SSL_CA_PEM).
    """
    source = {}
    if secrets:
        try:
            source = dict(secrets)
        except Exception:
            source = {}

    env_names = {
        "host": "MYSQL_HOST",
        "port": "MYSQL_PORT",
        "user": "MYSQL_USER",
        "password": "MYSQL_PASSWORD",
        "database": "MYSQL_DATABASE",
        "use_ssl": "MYSQL_USE_SSL",
        "ssl_ca_pem": "MYSQL_SSL_CA_PEM",
    }
    for key, env_name in env_names.items():
        if source.get(key) in (None, ""):
            env_value = os.environ.get(env_name)
            if env_value:
                source[key] = env_value

    if not (source.get("host") and source.get("user") and source.get("database")):
        return None

    return {
        "host": str(source["host"]),
        "port": int(source.get("port") or 3306),
        "user": str(source["user"]),
        "password": str(source.get("password") or ""),
        "database": str(source["database"]),
        "use_ssl": _to_bool(source.get("use_ssl", False)),
        "ssl_ca_pem": source.get("ssl_ca_pem") or None,
    }


def _write_ca_file(pem_text):
    """Writes a CA certificate (given as text) to a temp file, once."""
    digest = hashlib.sha256(pem_text.encode("utf-8")).hexdigest()[:16]
    path = os.path.join(tempfile.gettempdir(), f"skillsync_ca_{digest}.pem")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(pem_text)
    return path


def _build_ssl_context(config):
    """
    Cloud MySQL providers require encrypted (TLS) connections.
    - ssl_ca_pem given  -> trust that CA (e.g. Aiven's project CA).
    - use_ssl = true    -> trust the normal system CA store (e.g. TiDB Cloud).
    - neither           -> plain connection (fine for local MySQL only).
    """
    if config.get("ssl_ca_pem"):
        context = ssl_lib.create_default_context(cafile=_write_ca_file(config["ssl_ca_pem"]))
        # Provider CAs are verified, hostname matching is relaxed because
        # some managed services issue certificates per project, not per host.
        context.check_hostname = False
        return context
    if config.get("use_ssl"):
        return ssl_lib.create_default_context()
    return None


# ------------------------------------------------------------ connection
def get_connection(config):
    """Opens a short-lived connection. Short timeouts so the UI never hangs."""
    import pymysql  # lazy import, see module docstring

    kwargs = dict(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
    )
    ssl_context = _build_ssl_context(config)
    if ssl_context is not None:
        kwargs["ssl"] = ssl_context
    return pymysql.connect(**kwargs)


def check_connection(config):
    """Returns (ok, message). The message is for logs/scripts, not the UI."""
    try:
        connection = get_connection(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        finally:
            connection.close()
        return True, "Connected"
    except Exception as exc:  # noqa: BLE001 - we want to fail soft here
        logger.warning("Database check failed: %s", exc)
        return False, f"{type(exc).__name__}: {exc}"


def init_schema(config):
    """Creates the table if it doesn't exist. Returns True on success."""
    key = (config["host"], config["port"], config["database"])
    if key in _schema_ready:
        return True
    try:
        connection = get_connection(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_TABLE_SQL)
        finally:
            connection.close()
        _schema_ready.add(key)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not initialise schema: %s", exc)
        return False


# --------------------------------------------------------------- helpers
def hash_text(text):
    """SHA-256 fingerprint. Identifies a resume without storing its content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_snippet(text, max_chars=200):
    """First `max_chars` characters, with whitespace tidied, for display."""
    tidy = " ".join(text.split())
    return tidy[:max_chars]


def build_row(session_id, resume_text, jd_text, result, semantic_weight, skill_weight):
    """Turns one comparison into the dict that gets inserted. No I/O here."""
    return {
        "session_id": session_id,
        "resume_hash": hash_text(resume_text),
        "jd_snippet": make_snippet(jd_text),
        "overall_score": result["overall_score"],
        "semantic_score": result["semantic_score"],
        "skill_score": result["skill_score"],
        "semantic_weight": semantic_weight,
        "skill_weight": skill_weight,
        "matched_skills": json.dumps(result["matched_skills"]),
        "missing_skills": json.dumps(result["missing_skills"]),
        "extra_skills": json.dumps(result["extra_skills"]),
    }


def _load_skills(raw):
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except (TypeError, ValueError):
        return []


# ------------------------------------------------------------ operations
def save_comparison(config, session_id, resume_text, jd_text, result,
                    semantic_weight, skill_weight):
    """Saves one comparison. Returns True if saved, False otherwise."""
    try:
        if not init_schema(config):
            return False
        row = build_row(session_id, resume_text, jd_text, result,
                        semantic_weight, skill_weight)
        connection = get_connection(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(INSERT_SQL, row)
        finally:
            connection.close()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not save comparison: %s", exc)
        return False


def get_session_history(config, session_id, limit=10):
    """This visitor's most recent comparisons (newest first), display-ready."""
    try:
        if not init_schema(config):
            return []
        connection = get_connection(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(HISTORY_SQL, (session_id, int(limit)))
                rows = cursor.fetchall()
        finally:
            connection.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load history: %s", exc)
        return []

    history = []
    for row in rows:
        history.append({
            "When": str(row["created_at"]),
            "Job description": row["jd_snippet"],
            "Overall %": float(row["overall_score"]),
            "Semantic %": float(row["semantic_score"]),
            "Skill %": float(row["skill_score"]),
            "Matched": len(_load_skills(row["matched_skills"])),
            "Missing": len(_load_skills(row["missing_skills"])),
        })
    return history


def get_global_stats(config):
    """Anonymous totals across all visitors, or None if unavailable."""
    try:
        if not init_schema(config):
            return None
        connection = get_connection(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(STATS_SQL)
                row = cursor.fetchone()
        finally:
            connection.close()
        if not row:
            return None
        average = row["avg_overall_score"]
        return {
            "total_comparisons": int(row["total_comparisons"] or 0),
            "avg_overall_score": round(float(average), 1) if average is not None else 0.0,
            "unique_resumes": int(row["unique_resumes"] or 0),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load stats: %s", exc)
        return None


def get_top_missing_skills(config, top_n=5, sample_size=500):
    """Most common 'missing' skills across the latest comparisons."""
    try:
        if not init_schema(config):
            return []
        connection = get_connection(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(RECENT_MISSING_SQL, (int(sample_size),))
                rows = cursor.fetchall()
        finally:
            connection.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load missing-skill stats: %s", exc)
        return []

    counter = Counter()
    for row in rows:
        counter.update(_load_skills(row["missing_skills"]))
    return counter.most_common(top_n)


def delete_session_history(config, session_id):
    """Deletes this visitor's saved comparisons. Returns rows deleted, or -1."""
    try:
        if not init_schema(config):
            return -1
        connection = get_connection(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute(DELETE_SESSION_SQL, (session_id,))
                deleted = cursor.rowcount
        finally:
            connection.close()
        return int(deleted)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not delete history: %s", exc)
        return -1