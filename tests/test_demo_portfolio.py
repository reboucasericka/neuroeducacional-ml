"""Testes do seed de portfólio (DEMO-001 e idempotência)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app import create_app
from src.platform.demo_seed import PORTFOLIO_MARKER, ensure_portfolio_demo
from src.platform.extensions import db
from src.platform.models import (
    Assessment,
    FeedbackReport,
    InterventionPlan,
    Patient,
    PatientAnamnesis,
    Professional,
    ProfessionalSession,
    ProgressNote,
)
from src.platform.seed import seed_demo_data


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test_demo_seed.db"
    monkeypatch.setenv("NEUROLEARN_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("NEUROLEARN_SEED_DEMO", "0")
    application = create_app(testing=True)
    application.config["WTF_CSRF_ENABLED"] = False
    with application.app_context():
        yield application
        db.session.remove()


def test_portfolio_seed_creates_demo001_journey(app):
    with app.app_context():
        # Conta demo mínima
        pro = Professional(
            name="Dra. Ana Demonstração",
            email=f"demo-{uuid4().hex[:6]}@neurolearn.local",
            professional_type="clinical_neuropsychopedagogue",
            preferred_subject_term="learner",
            onboarding_completed=True,
            is_active=True,
        )
        # ensure_portfolio_demo procura email fixo — criar a conta canónica
        existing = Professional.query.filter_by(email="demo@neurolearn.local").first()
        if existing is None:
            pro.email = "demo@neurolearn.local"
            pro.set_password("Demo@12345")
            db.session.add(pro)
            db.session.commit()

        from src.platform.anamnesis_seed import ensure_anamnesis_templates
        from src.platform.cognitive_seed import (
            ensure_cognitive_catalog,
            ensure_demo_cognitive_patient,
        )
        from src.platform.instruments_seed import ensure_instrument_catalog

        ensure_anamnesis_templates()
        ensure_instrument_catalog()
        ensure_cognitive_catalog()
        ensure_demo_cognitive_patient()
        ensure_portfolio_demo()

        patient = Patient.query.filter_by(internal_code="DEMO-001").first()
        assert patient is not None
        assert "Lara" in patient.name
        assert PORTFOLIO_MARKER in (patient.notes or "")
        assert PatientAnamnesis.query.filter_by(patient_id=patient.id).count() >= 1
        assert Assessment.query.filter_by(patient_id=patient.id).count() >= 1
        assert FeedbackReport.query.filter_by(patient_id=patient.id).count() >= 1
        assert InterventionPlan.query.filter_by(patient_id=patient.id).count() >= 1
        assert ProfessionalSession.query.filter_by(patient_id=patient.id).count() >= 3
        assert ProgressNote.query.filter_by(patient_id=patient.id).count() >= 1

        codes = {
            p.internal_code
            for p in Patient.query.filter(
                Patient.internal_code.like("DEMO-%")
            ).all()
        }
        for i in range(1, 9):
            assert f"DEMO-00{i}" in codes

        # Idempotência
        n_sessions = ProfessionalSession.query.filter_by(patient_id=patient.id).count()
        n_patients = Patient.query.filter(Patient.internal_code.like("DEMO-%")).count()
        ensure_portfolio_demo()
        assert (
            ProfessionalSession.query.filter_by(patient_id=patient.id).count()
            == n_sessions
        )
        assert (
            Patient.query.filter(Patient.internal_code.like("DEMO-%")).count()
            == n_patients
        )


def test_production_requires_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me-dev-only")
    monkeypatch.setenv("NEUROLEARN_DATABASE_URL", f"sqlite:///{(tmp_path/'p.db').as_posix()}")
    from flask import Flask
    from src.platform.config import apply_config

    app = Flask("test-prod")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        apply_config(app, tmp_path)


def test_landing_mentions_demo_cta(app):
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Explorar demonstração" in body
    assert "Data Science experimental" in body
    assert "DEMO-001" in body
