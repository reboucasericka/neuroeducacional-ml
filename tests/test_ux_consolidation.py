"""Testes da consolidação UX: pesquisa, paginação, timeline, erros, CSRF."""

from __future__ import annotations

import re
from datetime import date, timedelta
from uuid import uuid4

import pytest

from app import create_app
from src.platform.extensions import db
from src.platform.models import (
    Assessment,
    Patient,
    PatientAnamnesis,
    Professional,
    ProfessionalSession,
)
from src.platform.anamnesis_seed import ensure_anamnesis_templates
from src.platform.models import AnamnesisTemplate


def _csrf(html: bytes) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html.decode())
    assert m, "csrf_token não encontrado"
    return m.group(1)


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test_ux.db"
    monkeypatch.setenv("NEUROLEARN_DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("NEUROLEARN_SEED_DEMO", "0")
    application = create_app(testing=True)
    with application.app_context():
        ensure_anamnesis_templates()
        yield application
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_pro(email: str | None = None) -> Professional:
    pro = Professional(
        name="Pro UX",
        email=email or f"ux-{uuid4().hex[:8]}@test.local",
        professional_type="clinical_neuropsychopedagogue",
        preferred_subject_term="learner",
        onboarding_completed=True,
        is_active=True,
    )
    pro.set_password("Senha@123")
    db.session.add(pro)
    db.session.commit()
    return pro


def _make_patient(pro: Professional, *, name: str, code: str, age_years: int = 10) -> Patient:
    birth = date.today().replace(year=date.today().year - age_years)
    patient = Patient(
        professional_id=pro.id,
        internal_code=code,
        name=name,
        birth_date=birth,
        sex="feminino",
        education_level="5º ano",
        status="ativo",
        is_minor=age_years < 18,
    )
    db.session.add(patient)
    db.session.commit()
    return patient


def _login(client, email: str):
    page = client.get("/login")
    return client.post(
        "/login",
        data={
            "csrf_token": _csrf(page.data),
            "email": email,
            "password": "Senha@123",
        },
        follow_redirects=False,
    )


def test_patient_search_and_filters(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email
        _make_patient(pro, name="Maria Silva", code="UX-001", age_years=9)
        _make_patient(pro, name="João Costa", code="UX-002", age_years=15)
        other = _make_pro()
        _make_patient(other, name="Maria Outra", code="UX-999", age_years=9)

    _login(client, email)
    r = client.get("/panel/patients?q=Maria")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Maria Silva" in body
    assert "Maria Outra" not in body
    assert 'aria-label="Breadcrumb"' in body

    r = client.get("/panel/patients?age=7-12")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Maria Silva" in body
    assert "João Costa" not in body

    r = client.get("/panel/patients?education=5%C2%BA%20ano")
    assert r.status_code == 200
    assert "Maria Silva" in r.data.decode() or "João Costa" in r.data.decode()

    r = client.get("/panel/patients?status=ativo&q=UX-001")
    assert r.status_code == 200
    assert "UX-001" in r.data.decode()


def test_patients_pagination_preserves_query(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email
        for i in range(25):
            _make_patient(pro, name=f"Paciente {i:02d}", code=f"PG-{i:03d}", age_years=8)

    _login(client, email)
    r = client.get("/panel/patients?q=Paciente&page=2&per_page=20")
    assert r.status_code == 200
    body = r.data.decode()
    assert "página 2" in body.lower() or "page 2" in body.lower() or "de 2" in body
    assert "per_page" in body
    assert "Paciente" in body


def test_patient_detail_header_tabs_and_timeline(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email
        patient = _make_patient(pro, name="Ana Timeline", code="TL-001")
        pid = patient.id
        db.session.add(
            Assessment(
                patient_id=pid,
                professional_id=pro.id,
                assessment_date=date.today(),
                reason="Avaliação demonstrativa",
                status="draft",
            )
        )
        db.session.add(
            ProfessionalSession(
                patient_id=pid,
                professional_id=pro.id,
                session_date=date.today(),
                session_type="assessment",
                status="planned",
                objective="Sessão demo",
            )
        )
        db.session.commit()

    _login(client, email)
    r = client.get(f"/panel/patients/{pid}")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Ana Timeline" in body
    assert "Novo registo" in body
    assert "Visão Geral" in body
    assert "Timeline" in body
    assert "overview-card" in body or "Anamnese mais recente" in body

    r = client.get(f"/panel/patients/{pid}?tab=timeline")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Timeline longitudinal" in body
    assert "Ver registo" in body
    assert "Avaliação" in body or "Sessão" in body

    r = client.get(f"/panel/patients/{pid}?tab=timeline&kind=assessment")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Avaliação" in body or "demonstrativa" in body


def test_empty_state_assessments_tab(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email
        patient = _make_patient(pro, name="Sem Avaliações", code="EMPTY-1")
        pid = patient.id

    _login(client, email)
    r = client.get(f"/panel/patients/{pid}?tab=assessments")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Nenhuma avaliação registrada" in body
    assert "Nova avaliação" in body


def test_history_redirects_to_timeline(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email
        patient = _make_patient(pro, name="Histórico", code="HIST-1")
        pid = patient.id

    _login(client, email)
    r = client.get(f"/panel/patients/{pid}?tab=history", follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "tab=timeline" in (r.headers.get("Location") or "")


def test_error_pages_403_404(app, client):
    with app.app_context():
        owner = _make_pro()
        other = _make_pro()
        patient = _make_patient(owner, name="Privado", code="PRIV-1")
        pid = patient.id
        other_email = other.email

    _login(client, other_email)
    r = client.get(f"/panel/patients/{pid}")
    assert r.status_code == 404
    assert "não foi encontrado" in r.data.decode().lower()

    r = client.get("/panel/this-route-does-not-exist-xyz")
    assert r.status_code == 404


def test_instruments_pagination_and_csrf_toggle(app, client):
    with app.app_context():
        from src.platform.instruments_seed import ensure_instrument_catalog

        pro = _make_pro()
        email = pro.email
        ensure_instrument_catalog()

    _login(client, email)
    r = client.get("/panel/instruments?per_page=20")
    assert r.status_code == 200
    assert "Catálogo" in r.data.decode() or "Instrumento" in r.data.decode()

    # Toggle sem CSRF deve falhar
    with app.app_context():
        from src.platform.models import Instrument

        inst = Instrument.query.filter_by(is_active=True).first()
        assert inst is not None
        iid = inst.id

    bad = client.post(f"/panel/instruments/{iid}/toggle", data={}, follow_redirects=False)
    assert bad.status_code == 400


def test_assessments_list_pagination(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email
        patient = _make_patient(pro, name="Lista Aval", code="AV-L1")
        for i in range(22):
            db.session.add(
                Assessment(
                    patient_id=patient.id,
                    professional_id=pro.id,
                    assessment_date=date.today() - timedelta(days=i),
                    reason=f"Aval {i}",
                    status="draft" if i % 2 == 0 else "completed",
                )
            )
        db.session.commit()

    _login(client, email)
    r = client.get("/panel/assessments?page=1&per_page=20")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Aval" in body
    r2 = client.get("/panel/assessments?page=2&per_page=20")
    assert r2.status_code == 200


def test_anamnesis_edit_has_section_nav_and_progress(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email
        patient = _make_patient(pro, name="Anamnese UX", code="AN-UX")
        template = AnamnesisTemplate.query.filter_by(
            slug="anamnese-neuroeducacional-v2"
        ).first()
        assert template is not None
        anam = PatientAnamnesis(
            patient_id=patient.id,
            template_id=template.id,
            professional_id=pro.id,
            status="draft",
        )
        db.session.add(anam)
        db.session.commit()
        pid, aid = patient.id, anam.id

    _login(client, email)
    r = client.get(f"/panel/patients/{pid}/anamneses/{aid}/edit")
    assert r.status_code == 200
    body = r.data.decode()
    assert "anamnesis-section-1" in body
    assert "Preenchimento" in body
    assert "Guardar rascunho" in body
    assert "data-anamnesis-nav" in body
    assert 'for="field_' in body


def test_terminology_learner_in_sidebar(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email

    _login(client, email)
    r = client.get("/panel/")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Aprendentes" in body
    assert "Perfil / Mappings" not in body
    assert "Configurações" in body
    assert "Sessões de hoje" in body


def test_settings_has_mappings_link(app, client):
    with app.app_context():
        pro = _make_pro()
        email = pro.email

    _login(client, email)
    r = client.get("/panel/settings")
    assert r.status_code == 200
    body = r.data.decode()
    assert "Mapeamento de instrumentos" in body
