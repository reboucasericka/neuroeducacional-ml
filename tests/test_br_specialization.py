"""Especialização BR: tipos profissionais, terminologia e escopo de instrumentos."""

from __future__ import annotations

from pathlib import Path
from datetime import date
from uuid import uuid4

import pytest

from app import create_app
from src.platform.extensions import db
from src.platform.instruments_seed import (
    ensure_instrument_catalog,
    ensure_instrument_professional_scopes,
)
from src.platform.models import (
    Assessment,
    Instrument,
    InstrumentProfessionalScope,
    Patient,
    Professional,
)
from src.platform.terminology import (
    PROFESSIONAL_TYPES,
    normalize_professional_type,
    practice_context,
    professional_type_label,
    resolve_subject_term,
    subject_label,
    subject_label_plural,
)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test_br_specialization.db"
    monkeypatch.setenv("NEUROLEARN_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("NEUROLEARN_SEED_DEMO", "0")
    application = create_app(testing=True)
    application.config["WTF_CSRF_ENABLED"] = False
    with application.app_context():
        yield application
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_pro(**kwargs) -> Professional:
    email = kwargs.pop("email", f"pro-{uuid4().hex[:8]}@test.local")
    defaults = dict(
        name="Pro Teste",
        email=email,
        professional_type="clinical_neuropsychopedagogue",
        preferred_subject_term="patient",
        onboarding_completed=True,
        is_active=True,
    )
    defaults.update(kwargs)
    defaults["email"] = email
    pro = Professional(**defaults)
    pro.set_password("Senha@123")
    db.session.add(pro)
    db.session.commit()
    return pro


def _login(client, email: str, password: str = "Senha@123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def test_professional_type_persists_and_labels(app, client):
    with app.app_context():
        pro = _make_pro(
            professional_type="psychopedagogue",
            preferred_subject_term="learner",
        )
        email = pro.email

    assert _login(client, email).status_code in (302, 303)

    r = client.get("/panel/profile")
    assert r.status_code == 200
    assert "Psicopedagogia".encode("utf-8") in r.data
    assert "Registro / identificação profissional".encode("utf-8") in r.data

    client.post(
        "/panel/profile",
        data={
            "name": "Pro Teste",
            "email": email,
            "professional_type": "institutional_neuropsychopedagogue",
            "preferred_subject_term": "learner",
            "registration_number": "REG-1",
            "education": "Neuropsicopedagogia",
            "specialization": "Institucional",
            "workplace": "Escola Demo",
            "phone": "11999990000",
            "city": "Campinas",
            "state": "SP",
            "bio": "Bio demo",
        },
        follow_redirects=True,
    )
    with app.app_context():
        pro = Professional.query.filter_by(email=email).first()
        assert pro.professional_type == "institutional_neuropsychopedagogue"
        assert pro.city == "Campinas"
        assert set(PROFESSIONAL_TYPES) == {
            "clinical_neuropsychopedagogue",
            "institutional_neuropsychopedagogue",
            "psychopedagogue",
        }
        assert professional_type_label(pro.professional_type) == (
            "Neuropsicopedagogia Institucional"
        )
        assert practice_context(pro.professional_type) == "institutional"


def test_subject_terminology_patient_learner_evaluatee(app):
    with app.app_context():
        clinical = Professional(
            name="A",
            email=f"a-{uuid4().hex[:6]}@t.local",
            professional_type="clinical_neuropsychopedagogue",
            preferred_subject_term="patient",
            onboarding_completed=True,
            password_hash="x",
        )
        institutional = Professional(
            name="B",
            email=f"b-{uuid4().hex[:6]}@t.local",
            professional_type="institutional_neuropsychopedagogue",
            preferred_subject_term=None,
            onboarding_completed=True,
            password_hash="x",
        )
        evaluatee = Professional(
            name="C",
            email=f"c-{uuid4().hex[:6]}@t.local",
            professional_type="psychopedagogue",
            preferred_subject_term="evaluatee",
            onboarding_completed=True,
            password_hash="x",
        )
        assert subject_label(clinical) == "Paciente"
        assert subject_label_plural(clinical) == "Pacientes"
        assert resolve_subject_term(institutional) == "learner"
        assert subject_label(institutional) == "Aprendente"
        assert subject_label(evaluatee) == "Avaliando"
        assert subject_label_plural(evaluatee) == "Avaliandos"


def test_ui_uses_learner_label(app, client):
    with app.app_context():
        pro = _make_pro(
            professional_type="psychopedagogue",
            preferred_subject_term="learner",
        )
        email = pro.email
    _login(client, email)
    r = client.get("/panel/patients")
    assert r.status_code == 200
    assert "Aprendentes".encode("utf-8") in r.data


def test_instrument_scope_default_verify(app):
    with app.app_context():
        ensure_instrument_catalog()
        ensure_instrument_professional_scopes()
        scopes = InstrumentProfessionalScope.query.all()
        assert scopes
        assert all(s.status == "verify" for s in scopes)
        inst = Instrument.query.first()
        assert inst.digital_use_status == "verify"


def test_restricting_scope_does_not_delete_assessments(app):
    with app.app_context():
        pro = _make_pro()
        patient = Patient(
            professional_id=pro.id,
            internal_code="T-1",
            name="Sujeito",
            birth_date=date(2012, 5, 1),
            is_minor=False,
            status="ativo",
        )
        inst = Instrument(
            name="Demo Inst",
            slug="demo-inst-scope",
            category="Outros",
            license_status="unknown",
            copyright_status="unknown",
            digital_use_status="verify",
            is_active=True,
        )
        db.session.add_all([patient, inst])
        db.session.flush()
        scope = InstrumentProfessionalScope(
            instrument_id=inst.id,
            professional_type="clinical_neuropsychopedagogue",
            status="allowed",
        )
        assessment = Assessment(
            patient_id=patient.id,
            professional_id=pro.id,
            reason="Avaliação demo",
            status="completed",
        )
        db.session.add_all([scope, assessment])
        db.session.commit()
        aid = assessment.id
        scope.status = "restricted"
        db.session.commit()
        assert db.session.get(Assessment, aid) is not None


def test_legacy_type_normalizes():
    assert normalize_professional_type("psicologo") == "clinical_neuropsychopedagogue"
    assert normalize_professional_type(None) == "clinical_neuropsychopedagogue"


def test_landing_200_and_positioning(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Neuropsicopedagogia".encode("utf-8") in r.data
    assert "Feito para a sua prática".encode("utf-8") in r.data
    assert b"profissionais de sa" not in r.data.lower()


def test_main_py_intact():
    root = Path(__file__).resolve().parents[1]
    main_path = root / "main.py"
    assert main_path.exists()
    content = main_path.read_text(encoding="utf-8")
    assert "if __name__" in content


def test_onboarding_sets_type(app, client):
    with app.app_context():
        pro = _make_pro(
            onboarding_completed=False,
            professional_type="clinical_neuropsychopedagogue",
        )
        email = pro.email
    login = _login(client, email)
    assert login.status_code in (302, 303)
    assert "/panel/onboarding" in (login.headers.get("Location") or "")
    r = client.post(
        "/panel/onboarding",
        data={"professional_type": "psychopedagogue"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    with app.app_context():
        pro = Professional.query.filter_by(email=email).first()
        assert pro.professional_type == "psychopedagogue"
        assert pro.onboarding_completed is True
        assert pro.preferred_subject_term == "learner"
