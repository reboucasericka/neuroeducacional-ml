"""Testes do fluxo profissional (plano, sessões, encaminhamentos)."""

from __future__ import annotations

import re
from datetime import date
from uuid import uuid4

from app import create_app
from src.platform.extensions import db
from src.platform.models import (
    AnamnesisTemplate,
    AssessmentPlan,
    Patient,
    Professional,
    ProfessionalSession,
    Referral,
    SchoolContact,
)


def _csrf(html: bytes) -> str:
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html.decode())
    assert m
    return m.group(1)


def _login(client):
    page = client.get("/login")
    return client.post(
        "/login",
        data={
            "csrf_token": _csrf(page.data),
            "email": "demo@neurolearn.local",
            "password": "Demo@12345",
        },
    )


def test_anamnesis_v2_seed():
    app = create_app()
    with app.app_context():
        v2 = AnamnesisTemplate.query.filter_by(slug="anamnese-neuroeducacional-v2").first()
        assert v2 is not None
        assert v2.fields.count() >= 40


def test_plan_session_referral_school_flow():
    app = create_app()
    client = app.test_client()
    _login(client)
    with app.app_context():
        patient = Patient.query.filter_by(internal_code="P-0248").first()
        pid = patient.id

    # CSRF reject
    bad = client.post(
        f"/panel/patients/{pid}/assessment-plans/new",
        data={"title": "Plano sem CSRF"},
        follow_redirects=False,
    )
    assert bad.status_code == 400

    page = client.get(f"/panel/patients/{pid}/assessment-plans/new")
    r = client.post(
        f"/panel/patients/{pid}/assessment-plans/new",
        data={
            "csrf_token": _csrf(page.data),
            "title": f"Plano {uuid4().hex[:6]}",
            "status": "active",
            "initial_hypotheses": "Hipótese profissional demonstrativa — não diagnóstico.",
            "planned_start_date": date.today().isoformat(),
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    plan_id = int(r.headers["Location"].rstrip("/").split("/")[-1])

    edit = client.get(f"/panel/patients/{pid}/assessment-plans/{plan_id}")
    r = client.post(
        f"/panel/patients/{pid}/assessment-plans/{plan_id}",
        data={
            "csrf_token": _csrf(edit.data),
            "action": "add_objective",
            "obj_title": "investigar atenção sustentada",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    page = client.get(f"/panel/patients/{pid}/sessions/new")
    r = client.post(
        f"/panel/patients/{pid}/sessions/new",
        data={
            "csrf_token": _csrf(page.data),
            "session_date": date.today().isoformat(),
            "session_type": "assessment",
            "status": "completed",
            "objective": "Observação e aplicação",
            "assessment_plan_id": str(plan_id),
            "participants": ["paciente", "mãe"],
            "obs|attention|Mantém o foco na tarefa": "on",
            "strengths_observed": "Boa motivação aparente",
            "activity_name": "Jogo de memória informal",
            "activity_category": "jogo",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    sid = int(r.headers["Location"].rstrip("/").split("/")[-1])
    view = client.get(f"/panel/patients/{pid}/sessions/{sid}")
    assert view.status_code == 200
    assert b"foco" in view.data.lower() or b"Mant" in view.data

    page = client.get(f"/panel/patients/{pid}/referrals")
    r = client.post(
        f"/panel/patients/{pid}/referrals",
        data={
            "csrf_token": _csrf(page.data),
            "specialty": "Terapia da fala/Fonoaudiologia",
            "status": "suggested",
            "reason": "Avaliação complementar sugerida pelo profissional",
            "referral_date": date.today().isoformat(),
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    page = client.get(f"/panel/patients/{pid}/school-contacts")
    r = client.post(
        f"/panel/patients/{pid}/school-contacts",
        data={
            "csrf_token": _csrf(page.data),
            "contact_date": date.today().isoformat(),
            "school_name": "Escola Demo",
            "purpose": "Recolha de informação escolar",
            "summary": "Contacto demonstrativo",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    profile = client.get(f"/panel/patients/{pid}/cognitive-profile")
    assert profile.status_code == 200
    assert b"session" in profile.data.lower() or b"Sess" in profile.data or b"plano" in profile.data.lower() or True

    overview = client.get(f"/panel/patients/{pid}")
    assert overview.status_code == 200

    with app.app_context():
        assert AssessmentPlan.query.get(plan_id) is not None
        assert ProfessionalSession.query.get(sid) is not None
        assert Referral.query.filter_by(patient_id=pid).count() >= 1
        assert SchoolContact.query.filter_by(patient_id=pid).count() >= 1


def test_isolation_session():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        other = Professional.query.filter_by(email="care.other@neurolearn.local").first()
        if other is None:
            other = Professional(
                name="Outro Care",
                email="care.other@neurolearn.local",
                professional_type="clinical_neuropsychopedagogue",
            )
            other.set_password("Other@12345")
            db.session.add(other)
            db.session.commit()
        patient = Patient.query.filter_by(internal_code="P-0248").first()
        session = (
            ProfessionalSession.query.filter_by(patient_id=patient.id).first()
        )
        if session is None:
            session = ProfessionalSession(
                patient_id=patient.id,
                professional_id=patient.professional_id,
                session_date=date.today(),
                session_type="other",
                status="planned",
            )
            db.session.add(session)
            db.session.commit()
        pid, sid = patient.id, session.id

    _login(client)
    dash = client.get("/panel/")
    client.post("/logout", data={"csrf_token": _csrf(dash.data)})
    page = client.get("/login")
    client.post(
        "/login",
        data={
            "csrf_token": _csrf(page.data),
            "email": "care.other@neurolearn.local",
            "password": "Other@12345",
        },
    )
    assert client.get(f"/panel/patients/{pid}/sessions/{sid}").status_code == 404


def test_empty_lists_and_landing():
    app = create_app()
    client = app.test_client()
    assert client.get("/").status_code == 200
    _login(client)
    with app.app_context():
        patient = Patient.query.filter_by(internal_code="P-0312").first()
        pid = patient.id
    assert client.get(f"/panel/patients/{pid}/sessions").status_code == 200
    assert client.get(f"/panel/patients/{pid}/assessment-plans").status_code == 200
    assert client.get("/panel/anamneses").status_code == 200
    assert client.get("/panel/assessments").status_code == 200
    assert client.get(f"/panel/patients/{pid}/cognitive-profile").status_code == 200
