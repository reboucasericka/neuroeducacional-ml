"""Testes do Perfil Cognitivo (rastreabilidade, seeds, isolamento)."""

from __future__ import annotations

import re
from datetime import date
from uuid import uuid4

from app import create_app
from src.platform.extensions import db
from src.platform.models import (
    Assessment,
    AssessmentInstrument,
    AssessmentResult,
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    Instrument,
    InstrumentSkillMapping,
    Patient,
    Professional,
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
        follow_redirects=False,
    )


def test_cognitive_seeds():
    app = create_app()
    with app.app_context():
        domains = CognitiveDomain.query.filter_by(is_active=True).all()
        assert len(domains) == 6
        skills = CognitiveSkill.query.filter_by(is_active=True).count()
        assert skills >= 30
        mappings = InstrumentSkillMapping.query.filter_by(is_active=True).count()
        assert mappings >= 3


def test_profile_empty_patient_ok():
    app = create_app()
    client = app.test_client()
    _login(client)
    with app.app_context():
        patient = Patient.query.filter_by(internal_code="P-0312").first()
        assert patient
        pid = patient.id
    r = client.get(f"/panel/patients/{pid}/cognitive-profile")
    assert r.status_code == 200
    assert b"Perfil Cognitivo" in r.data or b"perfil" in r.data.lower()


def test_associate_result_to_profile():
    app = create_app()
    client = app.test_client()
    _login(client)
    with app.app_context():
        patient = Patient.query.filter_by(internal_code="P-0248").first()
        stroop = Instrument.query.filter_by(slug="stroop").first()
        domain = CognitiveDomain.query.filter_by(slug="atencao-funcoes-executivas").first()
        skill = CognitiveSkill.query.filter_by(
            domain_id=domain.id, slug="controle-inibitorio"
        ).first()
        assert patient and stroop and domain and skill
        assessment = Assessment(
            patient_id=patient.id,
            professional_id=patient.professional_id,
            assessment_date=date.today(),
            reason="Teste perfil cognitivo",
            status="draft",
        )
        db.session.add(assessment)
        db.session.flush()
        ai = AssessmentInstrument(
            assessment_id=assessment.id,
            instrument_id=stroop.id,
            instrument_name=stroop.name,
            instrument_short_name=stroop.short_name,
            status="pending",
        )
        db.session.add(ai)
        db.session.flush()
        result = AssessmentResult(
            assessment_instrument_id=ai.id,
            metric_name="interferencia",
            raw_value="12",
            unit="erros",
            sort_order=0,
        )
        db.session.add(result)
        db.session.commit()
        pid, aid, rid, did, sid, ai_id = (
            patient.id,
            assessment.id,
            result.id,
            domain.id,
            skill.id,
            ai.id,
        )

    edit = client.get(f"/panel/patients/{pid}/assessments/{aid}/edit")
    assert edit.status_code == 200
    form = {
        "csrf_token": _csrf(edit.data),
        "action": "draft",
        "reason": "Teste perfil cognitivo",
        "assessment_date": date.today().isoformat(),
        f"ai_{ai_id}_status": "completed",
        f"metric_{rid}_metric_name": "interferencia",
        f"metric_{rid}_raw_value": "12",
        f"metric_{rid}_unit": "erros",
        f"metric_{rid}_link_profile": "on",
        f"metric_{rid}_domain_id": str(did),
        f"metric_{rid}_skill_id": str(sid),
    }
    r = client.post(
        f"/panel/patients/{pid}/assessments/{aid}/edit",
        data=form,
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)

    with app.app_context():
        ind = CognitiveIndicator.query.filter_by(assessment_result_id=rid).first()
        assert ind is not None
        assert ind.domain_id == did
        assert ind.skill_id == sid
        assert ind.source_type == "assessment_result"

    profile = client.get(f"/panel/patients/{pid}/cognitive-profile")
    assert profile.status_code == 200

    domain_page = client.get(
        f"/panel/patients/{pid}/cognitive-profile/domains/{did}"
    )
    assert domain_page.status_code == 200


def test_demo_patient_and_timeline():
    app = create_app()
    client = app.test_client()
    _login(client)
    with app.app_context():
        demo = Patient.query.filter_by(internal_code="DEMO-001").first()
        assert demo is not None
        pid = demo.id
        assert CognitiveIndicator.query.filter_by(patient_id=pid).count() >= 1
    r = client.get(f"/panel/patients/{pid}/cognitive-profile")
    assert r.status_code == 200
    assert b"DEMONSTRA" in r.data or b"Timeline" in r.data or b"timeline" in r.data.lower()


def test_isolation_cognitive_profile():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        other = Professional.query.filter_by(email="cog.other@neurolearn.local").first()
        if other is None:
            other = Professional(
                name="Outro Cog",
                email="cog.other@neurolearn.local",
                professional_type="clinical_neuropsychopedagogue",
            )
            other.set_password("Other@12345")
            db.session.add(other)
            db.session.commit()
        patient = Patient.query.filter_by(internal_code="DEMO-001").first()
        pid = patient.id

    _login(client)
    dash = client.get("/panel/")
    client.post("/logout", data={"csrf_token": _csrf(dash.data)})
    page = client.get("/login")
    client.post(
        "/login",
        data={
            "csrf_token": _csrf(page.data),
            "email": "cog.other@neurolearn.local",
            "password": "Other@12345",
        },
    )
    assert client.get(f"/panel/patients/{pid}/cognitive-profile").status_code == 404


def test_csrf_manual_indicator():
    app = create_app()
    client = app.test_client()
    _login(client)
    with app.app_context():
        patient = Patient.query.filter_by(internal_code="P-0248").first()
        domain = CognitiveDomain.query.first()
        pid, did = patient.id, domain.id
    page = client.get(f"/panel/patients/{pid}/cognitive-indicators/new")
    bad = client.post(
        f"/panel/patients/{pid}/cognitive-indicators/new",
        data={"domain_id": did, "label": "teste"},
        follow_redirects=False,
    )
    assert bad.status_code == 400
    good = client.post(
        f"/panel/patients/{pid}/cognitive-indicators/new",
        data={
            "csrf_token": _csrf(page.data),
            "domain_id": did,
            "label": f"manual-{uuid4().hex[:6]}",
            "source_type": "manual_entry",
        },
        follow_redirects=False,
    )
    assert good.status_code in (302, 303)


def test_landing_and_anamneses_still_ok():
    app = create_app()
    client = app.test_client()
    assert client.get("/").status_code == 200
    _login(client)
    assert client.get("/panel/anamneses").status_code == 200
    assert client.get("/panel/assessments").status_code == 200
