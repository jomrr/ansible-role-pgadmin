"""Verify effective system settings using the installed pgAdmin configuration."""

import configparser
import importlib
import os
import sys
from http.cookies import SimpleCookie
from pathlib import Path
from types import ModuleType


def verify_database(config: ModuleType, backend: str) -> None:
    """Write and read data through the configured settings database connection."""
    sqlalchemy = importlib.import_module("sqlalchemy")
    uri = config.CONFIG_DATABASE_URI
    if backend == "sqlite":
        if uri:
            raise AssertionError("SQLite must use an empty CONFIG_DATABASE_URI")
        uri = sqlalchemy.engine.URL.create("sqlite", database=config.SQLITE_PATH)
    engine = sqlalchemy.create_engine(uri)
    try:
        if engine.dialect.name != backend:
            raise AssertionError("The effective settings database backend is incorrect")
        with engine.begin() as connection:
            connection.execute(sqlalchemy.text(
                "CREATE TABLE molecule_backend_probe (value VARCHAR(32))"
            ))
            connection.execute(sqlalchemy.text(
                "INSERT INTO molecule_backend_probe (value) VALUES (:value)"
            ), {"value": "pgadmin backend test"})
            value = connection.execute(sqlalchemy.text(
                "SELECT value FROM molecule_backend_probe"
            )).scalar_one()
            if value != "pgadmin backend test":
                raise AssertionError("The settings database did not retain the value")
            connection.execute(sqlalchemy.text("DROP TABLE molecule_backend_probe"))
    finally:
        engine.dispose()


def verify_repository(source: str, os_family: str) -> None:
    """Preserve DNF substitution for release and architecture during upgrades."""
    if source == "official" and os_family == "RedHat":
        repository = configparser.ConfigParser(interpolation=None)
        repository.read("/etc/yum.repos.d/pgadmin4.repo")
        baseurl = repository["pgAdmin4"]["baseurl"]
        if not baseurl.endswith("-$releasever-$basearch"):
            raise AssertionError("The pgAdmin repository must retain DNF variables")


def verify_session_cookie(headers: list[str], cookie_name: str) -> None:
    """Check the session cookie actually returned to the browser."""
    cookies = SimpleCookie()
    for value in headers:
        cookies.load(value)
    cookie = cookies[cookie_name]
    if not cookie["secure"] or not cookie["httponly"]:
        raise AssertionError("Session cookies must be Secure and HttpOnly")
    if cookie["samesite"] != "Lax" or cookie["domain"] or cookie["path"] != "/":
        raise AssertionError("Session cookie scope does not match the baseline")


def verify_web_security(config: ModuleType) -> None:
    """Exercise host rejection and browser protections in the installed app."""
    os.environ["PGADMIN_SETUP_EMAIL"] = "molecule@example.com"
    os.environ["PGADMIN_SETUP_PASSWORD"] = "Molecule_security_42!"
    app = importlib.import_module("pgAdmin4").app
    client = app.test_client()
    response = client.get("/login", base_url="https://localhost")
    if response.status_code != 200:
        raise AssertionError(f"The HTTPS login page returned {response.status_code}")
    expected_headers = {
        "Strict-Transport-Security": "max-age=31536000",
        "X-Frame-Options": "SAMEORIGIN",
        "X-Content-Type-Options": "nosniff",
        "X-XSS-Protection": "0",
        "Cross-Origin-Opener-Policy": "same-origin",
    }
    for name, value in expected_headers.items():
        if response.headers.get(name) != value:
            raise AssertionError(f"Missing browser protection: {name}")
    verify_session_cookie(
        response.headers.getlist("Set-Cookie"), config.SESSION_COOKIE_NAME
    )

    for headers in ({}, {"X-Forwarded-Host": "localhost"}):
        response = client.get(
            "/login", base_url="https://untrusted.example.org", headers=headers
        )
        if response.status_code != 403:
            raise AssertionError("An untrusted Host bypassed the allowlist")

    for name in (
        "DEBUG", "SUPPORT_SSH_TUNNEL",
        "ALLOW_SAVE_TUNNEL_PASSWORD", "ENABLE_PSQL", "ENABLE_BINARY_PATH_BROWSING",
        "ENABLE_SERVER_PASS_EXEC_CMD", "AUTO_DISCOVER_SERVERS",
        "SHOW_GRAVATAR_IMAGE", "UPGRADE_CHECK_ENABLED", "LLM_ENABLED",
    ):
        if app.config[name] is not False:
            raise AssertionError(f"The security baseline did not disable {name}")
    if app.config["SECURITY_PASSWORD_LENGTH_MIN"] != 14:
        raise AssertionError("The authentication password minimum is not effective")
    if not app.config["MFA_ENABLED"] or app.config["MFA_SUPPORTED_METHODS"] != [
        "authenticator"
    ]:
        raise AssertionError("TOTP enrollment is not available")
    if app.config["FILE_LOG_LEVEL"] != 30:
        raise AssertionError("Site settings replaced unrelated security defaults")


def main() -> None:
    """Load pgAdmin's configuration and verify role-owned effective settings."""
    application_path = Path(sys.argv[1])
    if sys.argv[1] == "native":
        candidates = [Path("/usr/lib/pgadmin4")]
        candidates.extend(Path("/usr/lib").glob("python*/site-packages/pgadmin4"))
        application_path = next(path for path in candidates if path.is_dir())
    for name in ("pgAdmin4.py", "config.py"):
        if not (application_path / name).is_file():
            raise AssertionError(f"Missing pgAdmin application file: {name}")

    sys.path.insert(0, str(application_path))
    config = importlib.import_module("config")
    expected = {
        "SERVER_MODE": True,
        "ALLOW_SAVE_PASSWORD": False,
        "CONSOLE_LOG_LEVEL": 20,
        "LOGIN_BANNER": "Managed 'pgAdmin' — true, false, null\\n",
        "AUTHENTICATION_SOURCES": ["internal"],
        "DEFAULT_BINARY_PATHS": {"pg": "/usr/bin"},
        "FIXED_BINARY_PATHS": {"pg": None},
    }
    for name, value in expected.items():
        actual = getattr(config, name)
        if actual != value or type(actual) is not type(value):
            raise AssertionError(f"Unexpected effective setting: {name}")
    verify_database(config, sys.argv[2])
    verify_repository(sys.argv[3], sys.argv[4])
    verify_web_security(config)
    print("Installed pgAdmin web application loads the managed system settings.")


if __name__ == "__main__":
    main()
