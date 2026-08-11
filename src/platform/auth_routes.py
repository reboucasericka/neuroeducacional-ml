"""Rotas de autenticação profissional."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from src.platform.models import Professional
from src.platform.security_utils import safe_redirect_target

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        professional = Professional.query.filter_by(email=email).first()

        if (
            professional
            and professional.is_active
            and professional.check_password(password)
        ):
            login_user(professional)
            if not getattr(professional, "onboarding_completed", True):
                return redirect(url_for("panel.onboarding"))
            fallback = url_for("panel.dashboard")
            next_url = safe_redirect_target(
                request.form.get("next") or request.args.get("next"),
                fallback,
            )
            return redirect(next_url)

        flash("Credenciais inválidas ou conta inativa.", "error")

    return render_template(
        "auth/login.html",
        next=safe_redirect_target(request.args.get("next"), ""),
    )


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sessão terminada.", "info")
    return redirect(url_for("auth.login"))
