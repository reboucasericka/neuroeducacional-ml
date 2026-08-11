"""Utilitários de segurança (redirects, etc.)."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import request


def safe_redirect_target(target: str | None, fallback: str) -> str:
    """
    Aceita apenas caminhos relativos internos (open-redirect safe).

    Rejeita URLs absolutas e esquemas externos (//evil.com, https://...).
    """
    if not target:
        return fallback
    candidate = target.strip()
    if not candidate or "\\" in candidate:
        return fallback
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not candidate.startswith("/") or candidate.startswith("//"):
        return fallback
    # Evitar redirects para o próprio endpoint de login em loop óbvio.
    if candidate.startswith("/login"):
        return fallback
    return candidate


def current_next_param() -> str | None:
    return request.args.get("next") or request.form.get("next")
