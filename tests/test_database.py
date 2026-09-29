import json
import os
import sys
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import database

CONFIG = {
    "host": "db.example.com", "port": 3306, "user": "u", "password": "p",
    "database": "skillsync", "use_ssl": False, "ssl_ca_pem": None,
}

RESULT = {
    "overall_score": 72.5, "semantic_score": 80.1, "skill_score": 60.0,
    "matched_skills": ["python", "sql"], "missing_skills": ["docker"],
    "extra_skills": ["excel"],
}


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params))
        self.rowcount = self.connection.rowcount

    def fetchall(self):
        return self.connection.rows

    def fetchone(self):
        return self.connection.rows[0] if self.connection.rows else None


class FakeConnection:
    def __init__(self, rows=None, rowcount=0):
        self.rows = rows or []
        self.rowcount = rowcount
        self.executed = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


def fresh():
    """Forget which schemas were created, so each test starts clean."""
    database._schema_ready.clear()


# ------------------------------------------------------------- config
def test_load_config_returns_none_when_not_configured():
    with patch.dict(os.environ, {}, clear=True):
        assert database.load_config(None) is None
        assert database.load_config({"host": "x"}) is None  # incomplete


def test_load_config_from_mapping_applies_defaults():
    with patch.dict(os.environ, {}, clear=True):
        config = database.load_config(
            {"host": "h", "user": "u", "password": "p", "database": "d"}
        )
    assert config["port"] == 3306
    assert config["use_ssl"] is False
    assert config["ssl_ca_pem"] is None


def test_load_config_parses_ssl_and_port():
    with patch.dict(os.environ, {}, clear=True):
        config = database.load_config(
            {"host": "h", "port": "4000", "user": "u", "password": "p",
             "database": "d", "use_ssl": "true"}
        )
    assert config["port"] == 4000
    assert config["use_ssl"] is True


def test_load_config_falls_back_to_environment():
    env = {"MYSQL_HOST": "envhost", "MYSQL_USER": "envuser",
           "MYSQL_PASSWORD": "envpass", "MYSQL_DATABASE": "envdb"}
    with patch.dict(os.environ, env, clear=True):
        config = database.load_config(None)
    assert config["host"] == "envhost"
    assert config["database"] == "envdb"


# ------------------------------------------------------------ helpers
def test_hash_is_stable_and_hides_the_text():
    digest = database.hash_text("my private resume text")
    assert digest == database.hash_text("my private resume text")
    assert digest != database.hash_text("another resume")
    assert "private" not in digest and len(digest) == 64


def test_snippet_normalises_whitespace_and_truncates():
    text = "Data   Scientist\n\nwanted " + "x" * 500
    snippet = database.make_snippet(text, max_chars=50)
    assert snippet.startswith("Data Scientist wanted")
    assert len(snippet) == 50


def test_build_row_never_contains_resume_text():
    row = database.build_row("sess", "SECRET RESUME BODY", "A job ad", RESULT, 0.6, 0.4)
    assert "SECRET RESUME BODY" not in json.dumps(row)
    assert row["resume_hash"] == database.hash_text("SECRET RESUME BODY")
    assert json.loads(row["matched_skills"]) == ["python", "sql"]


# --------------------------------------------------------- operations
def test_save_comparison_creates_table_then_inserts():
    fresh()
    fake = FakeConnection()
    with patch.object(database, "get_connection", return_value=fake):
        saved = database.save_comparison(CONFIG, "sess-1", "resume", "job ad", RESULT, 0.6, 0.4)
    assert saved is True
    statements = [sql for sql, _ in fake.executed]
    assert any("CREATE TABLE IF NOT EXISTS" in s for s in statements)
    insert_sql, insert_params = fake.executed[-1]
    assert "INSERT INTO comparisons" in insert_sql
    assert insert_params["session_id"] == "sess-1"
    assert insert_params["overall_score"] == 72.5
    assert fake.closed is True


def test_save_comparison_uses_placeholders_not_string_formatting():
    fresh()
    fake = FakeConnection()
    evil_jd = "'; DROP TABLE comparisons; --"
    with patch.object(database, "get_connection", return_value=fake):
        database.save_comparison(CONFIG, "s", "resume", evil_jd, RESULT, 0.6, 0.4)
    insert_sql, params = fake.executed[-1]
    assert "DROP TABLE" not in insert_sql      # never spliced into the SQL
    assert "DROP TABLE" in params["jd_snippet"]  # sent safely as data


def test_save_comparison_fails_soft_when_database_is_down():
    fresh()
    with patch.object(database, "get_connection", side_effect=RuntimeError("db down")):
        assert database.save_comparison(CONFIG, "s", "r", "j", RESULT, 0.6, 0.4) is False


def test_history_converts_rows_for_display():
    fresh()
    rows = [{
        "id": 1, "created_at": datetime(2026, 9, 28, 10, 30), "jd_snippet": "Data Scientist",
        "overall_score": Decimal("72.5"), "semantic_score": Decimal("80.1"),
        "skill_score": Decimal("60.0"),
        "matched_skills": json.dumps(["python", "sql"]),
        "missing_skills": json.dumps(["docker"]),
    }]
    fake = FakeConnection(rows=rows)
    with patch.object(database, "get_connection", return_value=fake):
        history = database.get_session_history(CONFIG, "sess-1", limit=5)
    assert history[0]["Overall %"] == 72.5
    assert history[0]["Matched"] == 2 and history[0]["Missing"] == 1
    _, params = fake.executed[-1]
    assert params == ("sess-1", 5)


def test_history_is_empty_list_on_error():
    fresh()
    with patch.object(database, "get_connection", side_effect=RuntimeError("boom")):
        assert database.get_session_history(CONFIG, "s") == []


def test_global_stats_shape():
    fresh()
    rows = [{"total_comparisons": 4, "avg_overall_score": Decimal("61.25"), "unique_resumes": 3}]
    with patch.object(database, "get_connection", return_value=FakeConnection(rows=rows)):
        stats = database.get_global_stats(CONFIG)
    assert stats == {"total_comparisons": 4, "avg_overall_score": 61.2, "unique_resumes": 3}


def test_top_missing_skills_counts_across_rows():
    fresh()
    rows = [
        {"missing_skills": json.dumps(["docker", "aws"])},
        {"missing_skills": json.dumps(["docker"])},
        {"missing_skills": json.dumps(["docker", "spark"])},
        {"missing_skills": "not valid json"},
    ]
    with patch.object(database, "get_connection", return_value=FakeConnection(rows=rows)):
        top = database.get_top_missing_skills(CONFIG, top_n=2)
    assert top[0] == ("docker", 3)
    assert len(top) == 2


def test_delete_session_history_returns_deleted_count():
    fresh()
    fake = FakeConnection(rowcount=3)
    with patch.object(database, "get_connection", return_value=fake):
        assert database.delete_session_history(CONFIG, "sess-1") == 3
    sql, params = fake.executed[-1]
    assert sql.startswith("DELETE FROM comparisons") and params == ("sess-1",)


def test_check_connection_reports_failure_without_raising():
    with patch.object(database, "get_connection", side_effect=RuntimeError("nope")):
        ok, message = database.check_connection(CONFIG)
    assert ok is False and "nope" in message


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        test()
    print(f"All {len(tests)} database tests passed!")