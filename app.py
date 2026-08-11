"""
NeuroLearn Analytics — aplicação Flask (landing + plataforma profissional).

O pipeline de Machine Learning sintético permanece em ``main.py`` / ``src/``
e não é misturado com dados identificáveis de pacientes.
"""

from __future__ import annotations

from pathlib import Path

from flask import Flask, flash, render_template

from src.platform.anamnesis_routes import anamnesis_bp
from src.platform.assessment_routes import assessment_bp
from src.platform.auth_routes import auth_bp
from src.platform.care_flow_routes import care_bp
from src.platform.cognitive_routes import cognitive_bp
from src.platform.config import SECURITY_HEADERS, apply_config
from src.platform.extensions import csrf, db, login_manager
from src.platform.intervention_routes import intervention_bp
from src.platform.models import Professional
from src.platform.panel_routes import panel_bp
from src.platform.schema_utils import ensure_schema
from src.platform.seed import seed_demo_data
from src.platform.terminology import (
    PRACTICE_CONTEXT_LABELS,
    PROFESSIONAL_TYPE_BLURBS,
    PROFESSIONAL_TYPE_LABELS,
    SUBJECT_LABELS,
    SUBJECT_TERMS,
    digital_use_label,
    practice_context,
    professional_type_label,
    scope_status_label,
    subject_label,
    subject_label_plural,
)


def create_app(*, testing: bool = False) -> Flask:
    app = Flask(__name__)

    base_dir = Path(__file__).resolve().parent
    apply_config(app, base_dir)

    if testing:
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = True
        app.config["NEUROLEARN_SEED_DEMO"] = False

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(Professional, int(user_id))

    @app.context_processor
    def inject_terminology():
        from flask_login import current_user

        pro = current_user if getattr(current_user, "is_authenticated", False) else None
        return {
            "subject_label": subject_label(pro),
            "subject_label_plural": subject_label_plural(pro),
            "professional_type_display": (
                professional_type_label(pro.professional_type) if pro else ""
            ),
            "practice_context_key": practice_context(pro.professional_type) if pro else "",
            "practice_context_label": (
                PRACTICE_CONTEXT_LABELS.get(practice_context(pro.professional_type), "")
                if pro
                else ""
            ),
            "professional_type_labels": PROFESSIONAL_TYPE_LABELS,
            "professional_type_blurbs": PROFESSIONAL_TYPE_BLURBS,
            "subject_term_choices": [
                (key, SUBJECT_LABELS[key][0]) for key in SUBJECT_TERMS
            ],
            "scope_status_label": scope_status_label,
            "digital_use_label": digital_use_label,
        }

    @app.before_request
    def maybe_force_onboarding():
        from flask import request
        from flask_login import current_user

        if not getattr(current_user, "is_authenticated", False):
            return None
        endpoint = request.endpoint or ""
        if endpoint in (
            "panel.onboarding",
            "auth.logout",
            "static",
        ) or endpoint.startswith("static"):
            return None
        if not getattr(current_user, "onboarding_completed", True):
            from flask import redirect, url_for

            return redirect(url_for("panel.onboarding"))
        return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(panel_bp)
    app.register_blueprint(anamnesis_bp)
    app.register_blueprint(assessment_bp)
    app.register_blueprint(cognitive_bp)
    app.register_blueprint(care_bp)
    app.register_blueprint(intervention_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.after_request
    def set_security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response

    @app.errorhandler(400)
    def handle_bad_request(error):
        # CSRFProtect emite 400; mensagem amigável sem stack trace.
        description = str(getattr(error, "description", "") or "")
        if "CSRF" in description.upper() or "csrf" in description.lower():
            flash(
                "A sessão expirou ou o formulário já não é válido. "
                "Atualize a página e tente novamente.",
                "error",
            )
            return (
                render_template(
                    "errors/csrf.html",
                    message=(
                        "A sessão expirou ou o formulário já não é válido. "
                        "Atualize a página e tente novamente."
                    ),
                ),
                400,
            )
        return (
            render_template(
                "errors/generic.html",
                message="Não foi possível processar o pedido.",
            ),
            400,
        )

    # Flask-WTF CSRFError (quando disponível)
    try:
        from flask_wtf.csrf import CSRFError

        @app.errorhandler(CSRFError)
        def handle_csrf_error(error):
            if app.debug:
                app.logger.warning("CSRF rejected: %s", getattr(error, "description", ""))
            flash(
                "A sessão expirou ou o formulário já não é válido. "
                "Atualize a página e tente novamente.",
                "error",
            )
            return (
                render_template(
                    "errors/csrf.html",
                    message=(
                        "A sessão expirou ou o formulário já não é válido. "
                        "Atualize a página e tente novamente."
                    ),
                ),
                400,
            )
    except ImportError:
        pass

    with app.app_context():
        ensure_schema()
        if app.config.get("NEUROLEARN_SEED_DEMO", True) and not testing:
            seed_demo_data()
        elif not testing:
            # Catálogos sem conta demo (produção / seed desativado).
            from src.platform.anamnesis_seed import ensure_anamnesis_templates
            from src.platform.cognitive_seed import ensure_cognitive_catalog
            from src.platform.instruments_seed import ensure_instrument_catalog

            ensure_anamnesis_templates()
            ensure_instrument_catalog()
            ensure_cognitive_catalog()

    return app


app = create_app()


if __name__ == "__main__":
    # DEVELOPMENT ONLY — em produção: debug=False e servidor WSGI + HTTPS.
    debug = bool(app.config.get("NEUROLEARN_DEBUG", True))
    app.run(debug=debug, host="127.0.0.1", port=8080)
