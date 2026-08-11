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


def resolve_secret_key() -> str:
    return (
        os.environ.get("SECRET_KEY")
        or os.environ.get("NEUROLEARN_SECRET_KEY")
        or _DEV_SECRET_FALLBACK
    )


def resolve_database_uri(default_sqlite: Path) -> str:
    return (
        os.environ.get("NEUROLEARN_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or f"sqlite:///{default_sqlite.as_posix()}"
    )


def apply_config(app, base_dir: Path) -> None:
    """Aplica configuração Flask a partir do ambiente."""
    _load_dotenv(base_dir / ".env")

    db_path = base_dir / "data" / "processed" / "neurolearn_platform.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Produção HTTPS: definir SESSION_COOKIE_SECURE=1 (ou true).
    cookie_secure = _truthy(os.environ.get("SESSION_COOKIE_SECURE"), default=False)

    app.config.update(
        SECRET_KEY=resolve_secret_key(),
        SQLALCHEMY_DATABASE_URI=resolve_database_uri(db_path),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=cookie_secure,
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=None,
        NEUROLEARN_SEED_DEMO=_truthy(
            os.environ.get("NEUROLEARN_SEED_DEMO"), default=True
        ),
        NEUROLEARN_DEBUG=_truthy(os.environ.get("FLASK_DEBUG"), default=True),
    )


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "SAMEORIGIN",
}
