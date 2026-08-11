"""Testes mínimos de CSRF e hardening básico."""

from __future__ import annotations

import re
from datetime import date
from uuid import uuid4

from app import create_app
from src.platform.extensions import db
from src.platform.models import Instrument, Patient, Professional
from src.platform.security_utils import safe_redirect_target


def _csrf_from(html: bytes | str) -> str:
    text = html.decode() if isinstance(html, bytes) else html
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', text)
    assert match, "csrf_token em falta na página"
    return match.group(1)


def _login(client, *, with_csrf: bool = True):
    page = client.get("/login")
    data = {
        "email": "demo@neurolearn.local",
        "password": "Demo@12345",
    }
    if with_csrf:
        data["csrf_token"] = _csrf_from(page.data)
    return client.post("/login", data=data, follow_redirects=False)


def test_safe_redirect_rejects_external():
    assert safe_redirect_target("https://evil.example/phish", "/panel/") == "/panel/"
    assert safe_redirect_target("//evil.example", "/panel/") == "/panel/"
    assert safe_redirect_target("/panel/patients", "/panel/") == "/panel/patients"
    assert safe_redirect_target(None, "/panel/") == "/panel/"


def test_csrf_login_without_token_rejected():
    app = create_app()
    client = app.test_client()
    response = client.post(
        "/login",
        data={"email": "demo@neurolearn.local", "password": "Demo@12345"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert b"sess" in response.data.lower() or b"formul" in response.data.lower()


def test_csrf_login_invalid_token_rejected():
    app = create_app()
    client = app.test_client()
    client.get("/login")
    response = client.post(
        "/login",
        data={
            "email": "demo@neurolearn.local",
            "password": "Demo@12345",
            "csrf_token": "token-invalido",
        },
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_csrf_login_valid_token_allowed():
    app = create_app()
    client = app.test_client()
    response = _login(client)
    assert response.status_code in (302, 303)


def test_logout_get_not_allowed():
    app = create_app()
    client = app.test_client()
    _login(client)
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 405


def test_logout_post_with_csrf():
    app = create_app()
    client = app.test_client()
    _login(client)
    dash = client.get("/panel/")
    token = _csrf_from(dash.data)
    response = client.post(
        "/logout", data={"csrf_token": token}, follow_redirects=False
    )
    assert response.status_code in (302, 303)


def test_csrf_patient_create():
    app = create_app()
    client = app.test_client()
    _login(client)
    page = client.get("/panel/patients/new")
    token = _csrf_from(page.data)
    code = f"P-C{uuid4().hex[:8].upper()}"

    # sem token
    bad = client.post(
        "/panel/patients/new",
        data={
            "internal_code": code,
            "name": "Paciente CSRF",
            "birth_date": "2015-01-01",
            "sex": "feminino",
        },
        follow_redirects=False,
    )
    assert bad.status_code == 400

    good = client.post(
        "/panel/patients/new",
        data={
            "csrf_token": token,
            "internal_code": code,
            "name": "Paciente CSRF",
            "birth_date": "2015-01-01",
            "sex": "feminino",
        },
        follow_redirects=False,
    )
    assert good.status_code in (302, 303)


def test_csrf_instrument_and_assessment_flow():
    app = create_app()
    client = app.test_client()
    _login(client)

    page = client.get("/panel/instruments/new")
    token = _csrf_from(page.data)
    bad = client.post(
        "/panel/instruments/new",
        data={"name": "Instr CSRF", "category": "Outros", "license_status": "unknown"},
        follow_redirects=False,
    )
    assert bad.status_code == 400

    good = client.post(
        "/panel/instruments/new",
        data={
            "csrf_token": token,
            "name": "Instr CSRF Valid",
            "short_name": "ICS",
            "slug": f"instr-csrf-{uuid4().hex[:6]}",
            "category": "Outros",
            "license_status": "unknown",
        },
        follow_redirects=False,
    )
    assert good.status_code in (302, 303)

    with app.app_context():
        patient = Patient.query.filter_by(internal_code="P-0248").first()
        assert patient is not None
        instruments = Instrument.query.filter_by(is_active=True).limit(2).all()
        assert len(instruments) >= 1
        pid = patient.id
        ids = [i.id for i in instruments]

    new_page = client.get(f"/panel/patients/{pid}/assessments/new")
    token = _csrf_from(new_page.data)
    bad = client.post(
        f"/panel/patients/{pid}/assessments/new",
        data={
            "reason": "Avaliação CSRF",
            "assessment_date": date.today().isoformat(),
            "instrument_ids": ids,
        },
        follow_redirects=False,
    )
    assert bad.status_code == 400

    good = client.post(
        f"/panel/patients/{pid}/assessments/new",
        data={
            "csrf_token": token,
            "reason": "Avaliação CSRF",
            "assessment_date": date.today().isoformat(),
            "instrument_ids": ids,
        },
        follow_redirects=False,
    )
    assert good.status_code in (302, 303)


def test_csrf_anamnesis_new():
    app = create_app()
    client = app.test_client()
    _login(client)
    with app.app_context():
        patient = Patient.query.filter_by(internal_code="P-0248").first()
        pid = patient.id
    page = client.get(f"/panel/patients/{pid}/anamneses/new")
    assert page.status_code == 200
    token = _csrf_from(page.data)
    # extrair um template_id do HTML
    match = re.search(r'name="template_id"[^>]*value="(\d+)"|value="(\d+)"[^>]*name="template_id"', page.data.decode())
    # fallback: select options
    if not match:
        match = re.search(r'<option value="(\d+)"', page.data.decode())
    assert match
    tid = match.group(1) or match.group(2)

    bad = client.post(
        f"/panel/patients/{pid}/anamneses/new",
        data={"template_id": tid},
        follow_redirects=False,
    )
    assert bad.status_code == 400

    good = client.post(
        f"/panel/patients/{pid}/anamneses/new",
        data={"csrf_token": token, "template_id": tid},
        follow_redirects=False,
    )
    assert good.status_code in (302, 303)


def test_isolation_still_404():
    app = create_app()
    client = app.test_client()
    with app.app_context():
        other = Professional.query.filter_by(email="csrf.other@neurolearn.local").first()
        if other is None:
            other = Professional(
                name="Outro CSRF",
                email="csrf.other@neurolearn.local",
                professional_type="clinical_neuropsychopedagogue",
            )
            other.set_password("Other@12345")
            db.session.add(other)
            db.session.commit()
        patient = Patient.query.filter_by(internal_code="P-0248").first()
        pid = patient.id

    _login(client)
    # logout via CSRF
    dash = client.get("/panel/")
    client.post("/logout", data={"csrf_token": _csrf_from(dash.data)})

    page = client.get("/login")
    client.post(
        "/login",
        data={
            "csrf_token": _csrf_from(page.data),
            "email": "csrf.other@neurolearn.local",
            "password": "Other@12345",
        },
    )
    assert client.get(f"/panel/patients/{pid}").status_code == 404


def test_security_headers_present():
    app = create_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert "strict-origin-when-cross-origin" in (
        response.headers.get("Referrer-Policy") or ""
    )


def test_open_redirect_on_login():
    app = create_app()
    client = app.test_client()
    page = client.get("/login?next=https://evil.example/x")
    token = _csrf_from(page.data)
    response = client.post(
        "/login?next=https://evil.example/x",
        data={
            "csrf_token": token,
            "email": "demo@neurolearn.local",
            "password": "Demo@12345",
            "next": "https://evil.example/x",
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    loc = response.headers.get("Location", "")
    assert "evil.example" not in loc
    assert "/panel" in loc
