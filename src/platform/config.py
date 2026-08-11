"""
Configuração leve da plataforma profissional.

Valores de produção devem vir de variáveis de ambiente.
Nunca imprimir SECRET_KEY em logs.
"""

from __future__ import annotations

import os
from pathlib import Path


# DEVELOPMENT ONLY — nunca usar em produção.
_DEV_SECRET_FALLBACK = "dev-only-change-me-neurolearn"


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv(path: Path) -> None:
    """Carrega .env simples sem dependência extra (não sobrescreve env existente)."""
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_flask_env() -> str:
    """development | testing | production."""
    raw = (os.environ.get("FLASK_ENV") or os.environ.get("NEUROLEARN_ENV") or "").strip().lower()
    if raw in {"development", "dev"}:
        return "development"
    if raw in {"testing", "test"}:
        return "testing"
    if raw in {"production", "prod"}:
        return "production"
    # Inferência: se FLASK_DEBUG=0 e SECRET_KEY definida, não forçar production.
    return "development"


def resolve_secret_key(*, env: str) -> str:
    explicit = os.environ.get("SECRET_KEY") or os.environ.get("NEUROLEARN_SECRET_KEY")
    if env == "production":
        if not explicit or explicit in {_DEV_SECRET_FALLBACK, "change-me-dev-only"}:
            raise RuntimeError(
                "Produção exige SECRET_KEY (ou NEUROLEARN_SECRET_KEY) forte. "
                "Não use o fallback de desenvolvimento."
            )
        return explicit
    return explicit or _DEV_SECRET_FALLBACK


def resolve_database_uri(default_sqlite: Path) -> str:
    return (
        os.environ.get("NEUROLEARN_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or f"sqlite:///{default_sqlite.as_posix()}"
    )


def apply_config(app, base_dir: Path, *, testing: bool = False) -> None:
    """Aplica configuração Flask a partir do ambiente."""
    _load_dotenv(base_dir / ".env")

    env = "testing" if testing or app.config.get("TESTING") else resolve_flask_env()

    db_path = base_dir / "data" / "processed" / "neurolearn_platform.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Produção HTTPS: definir SESSION_COOKIE_SECURE=1 (ou true).
    cookie_secure_default = env == "production"
    cookie_secure = _truthy(
        os.environ.get("SESSION_COOKIE_SECURE"), default=cookie_secure_default
    )

    # Seed demo: nunca por omissão em produção.
    seed_default = env != "production"
    seed_demo = _truthy(os.environ.get("NEUROLEARN_SEED_DEMO"), default=seed_default)
    if env == "production":
        seed_demo = _truthy(os.environ.get("NEUROLEARN_SEED_DEMO"), default=False)

    debug_default = env == "development"
    debug = _truthy(os.environ.get("FLASK_DEBUG"), default=debug_default)
    if env == "production":
        debug = False

    app.config.update(
        SECRET_KEY=resolve_secret_key(env=env),
        SQLALCHEMY_DATABASE_URI=resolve_database_uri(db_path),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,
        NEUROLEARN_ENV=env,
        NEUROLEARN_SEED_DEMO=seed_demo,
        NEUROLEARN_DEBUG=debug,
    )


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
}
