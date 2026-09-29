"""
check_db.py
-----------
Run this BEFORE starting the app to confirm your database settings work:

    python scripts/check_db.py

It reads .streamlit/secrets.toml (or MYSQL_* environment variables), tries
to connect, creates the table if needed, and prints what it found. The
error messages printed here are for you only — the web app itself never
shows connection details to visitors.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import database  # noqa: E402


def load_local_secrets():
    """Reads the [mysql] section of .streamlit/secrets.toml, if it exists."""
    path = os.path.join(ROOT, ".streamlit", "secrets.toml")
    if not os.path.exists(path):
        return None
    try:
        import tomllib  # Python 3.11+

        with open(path, "rb") as f:
            data = tomllib.load(f)
    except ImportError:
        import toml  # installed together with Streamlit

        data = toml.load(path)
    return data.get("mysql")


def main():
    config = database.load_config(load_local_secrets())
    if config is None:
        print("No database configured.")
        print("Create .streamlit/secrets.toml from .streamlit/secrets.toml.example first.")
        return 1

    print(f"Connecting to {config['host']}:{config['port']} (database '{config['database']}') ...")
    ok, message = database.check_connection(config)
    print(f"Connection : {message}")
    if not ok:
        return 1

    print("Table      :", "ready" if database.init_schema(config) else "FAILED to create")
    print("Stats      :", database.get_global_stats(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())