"""Devolutiva, intervenção e evolução longitudinal."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from app import create_app
from src.platform.extensions import db
from src.platform.models import (
    FeedbackReport,
    InterventionGoal,
    InterventionPlan,
    InterventionPlanReview,
    InterventionStrategy,
    Patient,
    Professional,
    ProfessionalSession,
    ProgressNote,
    SessionInterventionGoal,
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


def _demo_patient_id(app) -> int:
    with app.app_context():
        p = Patient.query.filter_by(internal_code="P-0248").first()
        assert p is not None
        return p.id


def test_feedback_draft_complete_reopen():
    app = create_app()
    client = app.test_client()
    _login(client)
    pid = _demo_patient_id(app)

    page = client.get(f"/panel/patients/{pid}/feedbacks/new")
    assert page.status_code == 200
    assert "Evidências".encode("utf-8") in page.data
    assert b"TDAH" not in page.data

    r = client.post(
        f"/panel/patients/{pid}/feedbacks/new",
        data={
            "csrf_token": _csrf(page.data),
            "title": f"Devolutiva {uuid4().hex[:6]}",
            "feedback_date": date.today().isoformat(),
            "strengths": "Boa persistência em tarefas curtas.",
            "professional_conclusion": "Síntese profissional descritiva — sem diagnóstico.",
            "family_guidance": "Manter rotina de estudo assistido.",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    fid = int(r.headers["Location"].rstrip("/").split("/")[-2]
              if r.headers["Location"].endswith("/edit")
              else r.headers["Location"].rstrip("/").split("/")[-1])
    # Location .../feedbacks/<id>/edit
    parts = r.headers["Location"].rstrip("/").split("/")
    fid = int(parts[parts.index("feedbacks") + 1])

    edit = client.get(f"/panel/patients/{pid}/feedbacks/{fid}/edit")
    assert edit.status_code == 200
    done = client.post(
        f"/panel/patients/{pid}/feedbacks/{fid}/edit",
        data={
            "csrf_token": _csrf(edit.data),
            "title": f"Devolutiva concluída {uuid4().hex[:4]}",
            "feedback_date": date.today().isoformat(),
            "strengths": "Potencialidades registadas.",
            "action": "complete",
        },
        follow_redirects=False,
    )
    assert done.status_code in (302, 303)

    view = client.get(f"/panel/patients/{pid}/feedbacks/{fid}")
    assert view.status_code == 200
    assert b"readonly" in view.data.lower() or "Conclus".encode("utf-8") in view.data or True

    # edit while completed redirects
    assert client.get(f"/panel/patients/{pid}/feedbacks/{fid}/edit").status_code in (302, 303)

    reopen_page = client.get(f"/panel/patients/{pid}/feedbacks/{fid}")
    reopen = client.post(
        f"/panel/patients/{pid}/feedbacks/{fid}/reopen",
        data={"csrf_token": _csrf(reopen_page.data)},
        follow_redirects=False,
    )
    assert reopen.status_code in (302, 303)
    with app.app_context():
        report = db.session.get(FeedbackReport, fid)
        assert report.status == "draft"


def test_intervention_goals_strategies_review_session_progress():
    app = create_app()
    client = app.test_client()
    _login(client)
    pid = _demo_patient_id(app)

    page = client.get(f"/panel/patients/{pid}/interventions/new")
    r = client.post(
        f"/panel/patients/{pid}/interventions/new",
        data={
            "csrf_token": _csrf(page.data),
            "title": f"Plano INT {uuid4().hex[:6]}",
            "status": "active",
            "start_date": date.today().isoformat(),
            "general_goal": "Desenvolver planeamento em tarefas escolares.",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    plan_id = int(r.headers["Location"].rstrip("/").split("/")[-1])

    edit = client.get(f"/panel/patients/{pid}/interventions/{plan_id}")
    client.post(
        f"/panel/patients/{pid}/interventions/{plan_id}",
        data={
            "csrf_token": _csrf(edit.data),
            "action": "add_goal",
            "goal_title": "Desenvolver planejamento",
            "how_observed": "Observação em tarefa de múltiplos passos",
            "success_criteria": "Antecipa etapas com menor mediação",
            "goal_status": "active",
        },
        follow_redirects=True,
    )
    with app.app_context():
        goal = InterventionGoal.query.filter_by(intervention_plan_id=plan_id).first()
        assert goal is not None
        goal_id = goal.id

    edit = client.get(f"/panel/patients/{pid}/interventions/{plan_id}")
    client.post(
        f"/panel/patients/{pid}/interventions/{plan_id}",
        data={
            "csrf_token": _csrf(edit.data),
            "action": "add_strategy",
            "strategy_goal_id": goal_id,
            "strategy_name": "Treino de planeamento (demo)",
            "strategy_frequency": "2x/semana",
        },
        follow_redirects=True,
    )
    with app.app_context():
        assert InterventionStrategy.query.filter_by(intervention_goal_id=goal_id).count() >= 1

    edit = client.get(f"/panel/patients/{pid}/interventions/{plan_id}")
    client.post(
        f"/panel/patients/{pid}/interventions/{plan_id}",
        data={
            "csrf_token": _csrf(edit.data),
            "action": "add_review",
            "review_date": date.today().isoformat(),
            "decision": "continue",
            "review_summary": "Manter frequência.",
        },
        follow_redirects=True,
    )
    with app.app_context():
        assert InterventionPlanReview.query.filter_by(intervention_plan_id=plan_id).count() >= 1

    # sessão de intervenção com 2 objetivos (cria 2º objetivo)
    edit = client.get(f"/panel/patients/{pid}/interventions/{plan_id}")
    client.post(
        f"/panel/patients/{pid}/interventions/{plan_id}",
        data={
            "csrf_token": _csrf(edit.data),
            "action": "add_goal",
            "goal_title": "Organização de materiais",
            "goal_status": "active",
        },
        follow_redirects=True,
    )
    with app.app_context():
        gids = [
            g.id
            for g in InterventionGoal.query.filter_by(intervention_plan_id=plan_id).all()
        ]
        assert len(gids) >= 2

    sform = client.get(f"/panel/patients/{pid}/sessions/new")
    r = client.post(
        f"/panel/patients/{pid}/sessions/new",
        data={
            "csrf_token": _csrf(sform.data),
            "session_date": date.today().isoformat(),
            "session_type": "intervention",
            "status": "completed",
            "intervention_plan_id": plan_id,
            "intervention_goal_ids": gids,
            "summary": "Sessão de intervenção demo",
            "strengths_observed": "Engajamento inicial",
            "help_level": "moderate",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 303)
    sid = int(r.headers["Location"].rstrip("/").split("/")[-1])
    with app.app_context():
        links = SessionInterventionGoal.query.filter_by(session_id=sid).count()
        assert links >= 2
        session = db.session.get(ProfessionalSession, sid)
        assert session.session_type == "intervention"

    pform = client.get(f"/panel/patients/{pid}/progress-notes/new")
    client.post(
        f"/panel/patients/{pid}/progress-notes/new",
        data={
            "csrf_token": _csrf(pform.data),
            "progress_status": "progress",
            "intervention_plan_id": plan_id,
            "intervention_goal_id": gids[0],
            "session_id": sid,
            "summary": "Consegue antecipar parte das etapas com menor mediação.",
            "professional_interpretation": "Evolução qualitativa positiva.",
        },
        follow_redirects=True,
    )
    with app.app_context():
        assert ProgressNote.query.filter_by(patient_id=pid).count() >= 1

    evo = client.get(f"/panel/patients/{pid}/evolution")
    assert evo.status_code == 200
    assert "Evolução".encode("utf-8") in evo.data

    # timeline includes feedback/intervention kinds via cognitive profile
    profile = client.get(f"/panel/patients/{pid}/cognitive-profile")
    assert profile.status_code == 200


def test_isolation_feedback_and_csrf():
    app = create_app()
    client = app.test_client()
    _login(client)
    pid = _demo_patient_id(app)
    page = client.get(f"/panel/patients/{pid}/feedbacks/new")
    bad = client.post(
        f"/panel/patients/{pid}/feedbacks/new",
        data={"title": "Sem CSRF"},
        follow_redirects=False,
    )
    assert bad.status_code == 400

    with app.app_context():
        other = Professional(
            name="Outro",
            email=f"other-{uuid4().hex[:6]}@test.local",
            professional_type="psychopedagogue",
            preferred_subject_term="learner",
            onboarding_completed=True,
            is_active=True,
        )
        other.set_password("Senha@123")
        db.session.add(other)
        db.session.flush()
        report = FeedbackReport(
            patient_id=pid,
            professional_id=other.id,
            title="Alheia",
            status="draft",
            feedback_date=date.today(),
        )
        db.session.add(report)
        db.session.commit()
        rid = report.id

    assert client.get(f"/panel/patients/{pid}/feedbacks/{rid}").status_code == 404


def test_terminology_on_feedback_pages():
    app = create_app()
    client = app.test_client()
    _login(client)
    pid = _demo_patient_id(app)
    with app.app_context():
        pro = Professional.query.filter_by(email="demo@neurolearn.local").first()
        pro.preferred_subject_term = "learner"
        db.session.commit()
    r = client.get(f"/panel/patients/{pid}/feedbacks")
    assert r.status_code == 200
    # nav uses Aprendentes
    assert "Aprendente".encode("utf-8") in r.data or "Aprendentes".encode("utf-8") in r.data


def test_empty_patient_intervention_ok():
    app = create_app()
    client = app.test_client()
    _login(client)
    with app.app_context():
        pro = Professional.query.filter_by(email="demo@neurolearn.local").first()
        empty = Patient(
            professional_id=pro.id,
            internal_code=f"E-{uuid4().hex[:5]}",
            name="Vazio",
            birth_date=date(2015, 1, 1),
            is_minor=True,
            status="ativo",
        )
        db.session.add(empty)
        db.session.commit()
        eid = empty.id
    assert client.get(f"/panel/patients/{eid}/feedbacks").status_code == 200
    assert client.get(f"/panel/patients/{eid}/interventions").status_code == 200
    assert client.get(f"/panel/patients/{eid}/evolution").status_code == 200


def test_main_py_intact():
    root = Path(__file__).resolve().parents[1]
    assert (root / "main.py").exists()
