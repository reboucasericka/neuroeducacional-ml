"""Rotas do fluxo profissional: plano, sessões, encaminhamentos, escola, consentimentos."""

from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src.platform.care_flow_constants import (
    ACTIVITY_CATEGORIES,
    CONSENT_TYPES,
    DOCUMENT_TYPES,
    HELP_LEVELS,
    OBSERVATION_CHECKLIST,
    PARTICIPANT_OPTIONS,
    PLAN_STATUSES,
    REFERRAL_SPECIALTIES,
    REFERRAL_STATUSES,
    SESSION_STATUSES,
    SESSION_TYPES,
    participants_from_storage,
    participants_to_storage,
)
from src.platform.extensions import db
from src.platform.models import (
    ActivityRecord,
    Assessment,
    AssessmentInstrument,
    AssessmentPlan,
    AssessmentPlanObjective,
    CognitiveDomain,
    InterventionGoal,
    InterventionPlan,
    Patient,
    PatientConsent,
    PatientDocument,
    ProfessionalSession,
    Referral,
    SchoolContact,
    SessionInterventionGoal,
    SessionObservation,
    utcnow,
)

care_bp = Blueprint("care", __name__, url_prefix="/panel")


def _owned_patient_or_404(patient_id: int) -> Patient:
    patient = Patient.query.filter_by(
        id=patient_id, professional_id=current_user.id
    ).first()
    if patient is None:
        abort(404)
    return patient


def _owned_plan_or_404(patient_id: int, plan_id: int) -> AssessmentPlan:
    plan = AssessmentPlan.query.filter_by(
        id=plan_id, patient_id=patient_id, professional_id=current_user.id
    ).first()
    if plan is None:
        abort(404)
    return plan


def _owned_session_or_404(patient_id: int, session_id: int) -> ProfessionalSession:
    session = ProfessionalSession.query.filter_by(
        id=session_id, patient_id=patient_id, professional_id=current_user.id
    ).first()
    if session is None:
        abort(404)
    return session


def _parse_date(raw: str | None):
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


# ---------- Plano de avaliação ----------


@care_bp.route("/patients/<int:patient_id>/assessment-plans")
@login_required
def plans_list(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    plans = (
        AssessmentPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(AssessmentPlan.updated_at.desc())
        .all()
    )
    return render_template(
        "panel/plans_list.html",
        patient=patient,
        plans=plans,
        plan_statuses=dict(PLAN_STATUSES),
    )


@care_bp.route("/patients/<int:patient_id>/assessment-plans/new", methods=["GET", "POST"])
@login_required
def plans_new(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Título é obrigatório.", "error")
        else:
            plan = AssessmentPlan(
                patient_id=patient.id,
                professional_id=current_user.id,
                title=title,
                reason=(request.form.get("reason") or "").strip() or None,
                objectives=(request.form.get("objectives") or "").strip() or None,
                initial_hypotheses=(request.form.get("initial_hypotheses") or "").strip()
                or None,
                status=request.form.get("status") or "draft",
                planned_start_date=_parse_date(request.form.get("planned_start_date")),
                planned_end_date=_parse_date(request.form.get("planned_end_date")),
                estimated_sessions=request.form.get("estimated_sessions", type=int),
                notes=(request.form.get("notes") or "").strip() or None,
            )
            if plan.status not in dict(PLAN_STATUSES):
                plan.status = "draft"
            db.session.add(plan)
            db.session.commit()
            flash("Plano de avaliação criado.", "success")
            return redirect(
                url_for("care.plans_edit", patient_id=patient.id, plan_id=plan.id)
            )
    return render_template(
        "panel/plan_form.html",
        patient=patient,
        plan=None,
        form={},
        plan_statuses=PLAN_STATUSES,
        mode="new",
    )


@care_bp.route(
    "/patients/<int:patient_id>/assessment-plans/<int:plan_id>",
    methods=["GET", "POST"],
)
@login_required
def plans_edit(patient_id: int, plan_id: int):
    patient = _owned_patient_or_404(patient_id)
    plan = _owned_plan_or_404(patient_id, plan_id)
    domains = (
        CognitiveDomain.query.filter_by(is_active=True)
        .order_by(CognitiveDomain.sort_order.asc())
        .all()
    )

    if request.method == "POST":
        action = request.form.get("action") or "save"
        if action == "add_objective":
            title = (request.form.get("obj_title") or "").strip()
            if title:
                order = plan.plan_objectives.count() + 1
                db.session.add(
                    AssessmentPlanObjective(
                        assessment_plan_id=plan.id,
                        title=title,
                        description=(request.form.get("obj_description") or "").strip()
                        or None,
                        domain_id=request.form.get("obj_domain_id", type=int),
                        priority=(request.form.get("obj_priority") or "").strip() or None,
                        status="open",
                        sort_order=order,
                    )
                )
                plan.touch()
                db.session.commit()
                flash("Objetivo adicionado.", "success")
            else:
                flash("Título do objetivo é obrigatório.", "error")
            return redirect(
                url_for("care.plans_edit", patient_id=patient.id, plan_id=plan.id)
            )

        if action == "toggle_objective":
            oid = request.form.get("objective_id", type=int)
            obj = AssessmentPlanObjective.query.filter_by(
                id=oid, assessment_plan_id=plan.id
            ).first()
            if obj:
                obj.status = "done" if obj.status != "done" else "open"
                plan.touch()
                db.session.commit()
            return redirect(
                url_for("care.plans_edit", patient_id=patient.id, plan_id=plan.id)
            )

        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Título é obrigatório.", "error")
        else:
            plan.title = title
            plan.reason = (request.form.get("reason") or "").strip() or None
            plan.objectives = (request.form.get("objectives") or "").strip() or None
            plan.initial_hypotheses = (
                request.form.get("initial_hypotheses") or ""
            ).strip() or None
            status = request.form.get("status") or plan.status
            if status in dict(PLAN_STATUSES):
                plan.status = status
            if plan.status == "completed" and plan.completed_at is None:
                plan.completed_at = utcnow()
            if plan.status != "completed":
                plan.completed_at = None
            plan.planned_start_date = _parse_date(request.form.get("planned_start_date"))
            plan.planned_end_date = _parse_date(request.form.get("planned_end_date"))
            plan.estimated_sessions = request.form.get("estimated_sessions", type=int)
            plan.notes = (request.form.get("notes") or "").strip() or None
            plan.touch()
            db.session.commit()
            flash("Plano atualizado.", "success")
            return redirect(
                url_for("care.plans_edit", patient_id=patient.id, plan_id=plan.id)
            )

    objectives = (
        plan.plan_objectives.order_by(
            AssessmentPlanObjective.sort_order.asc(), AssessmentPlanObjective.id.asc()
        ).all()
    )
    return render_template(
        "panel/plan_form.html",
        patient=patient,
        plan=plan,
        objectives=objectives,
        domains=domains,
        form={},
        plan_statuses=PLAN_STATUSES,
        mode="edit",
    )


# ---------- Sessões ----------


@care_bp.route("/patients/<int:patient_id>/sessions")
@login_required
def sessions_list(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    sessions = (
        ProfessionalSession.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(ProfessionalSession.session_date.desc(), ProfessionalSession.id.desc())
        .all()
    )
    return render_template(
        "panel/sessions_list.html",
        patient=patient,
        sessions=sessions,
        session_types=dict(SESSION_TYPES),
        session_statuses=dict(SESSION_STATUSES),
    )


def _session_form_context(patient: Patient):
    plans = (
        AssessmentPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(AssessmentPlan.updated_at.desc())
        .all()
    )
    intervention_plans = (
        InterventionPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(InterventionPlan.updated_at.desc())
        .all()
    )
    intervention_goals = []
    for ip in intervention_plans:
        for g in ip.goals.filter(InterventionGoal.status != "cancelled").all():
            intervention_goals.append(g)
    assessments = (
        Assessment.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(Assessment.assessment_date.desc())
        .all()
    )
    instruments = []
    for a in assessments:
        for ai in a.instruments.order_by(AssessmentInstrument.id.asc()).all():
            instruments.append(ai)
    return plans, assessments, instruments, intervention_plans, intervention_goals


def _apply_session_fields(session: ProfessionalSession, form) -> list[str]:
    errors = []
    session_date = _parse_date(form.get("session_date"))
    if session_date is None:
        errors.append("Data da sessão inválida.")
        return errors
    session.session_date = session_date
    session.start_time = (form.get("start_time") or "").strip() or None
    session.end_time = (form.get("end_time") or "").strip() or None
    stype = form.get("session_type") or "assessment"
    session.session_type = stype if stype in dict(SESSION_TYPES) else "other"
    status = form.get("status") or "planned"
    session.status = status if status in dict(SESSION_STATUSES) else "planned"
    session.objective = (form.get("objective") or "").strip() or None
    session.summary = (form.get("summary") or "").strip() or None
    session.professional_notes = (form.get("professional_notes") or "").strip() or None
    session.next_steps = (form.get("next_steps") or "").strip() or None
    session.strengths_observed = (form.get("strengths_observed") or "").strip() or None
    session.facilitating_strategies = (
        form.get("facilitating_strategies") or ""
    ).strip() or None
    session.participants = participants_to_storage(form.getlist("participants"))
    session.assessment_plan_id = form.get("assessment_plan_id", type=int)
    session.assessment_id = form.get("assessment_id", type=int)
    session.assessment_instrument_id = form.get("assessment_instrument_id", type=int)
    session.intervention_plan_id = form.get("intervention_plan_id", type=int) or None
    session.help_level = (form.get("help_level") or "").strip() or None
    session.difficulties_observed = (form.get("difficulties_observed") or "").strip() or None
    session.response_notes = (form.get("response_notes") or "").strip() or None
    session.touch()
    return errors


def _sync_intervention_goals(session: ProfessionalSession, form) -> None:
    SessionInterventionGoal.query.filter_by(session_id=session.id).delete()
    for raw in form.getlist("intervention_goal_ids"):
        try:
            gid = int(raw)
        except (TypeError, ValueError):
            continue
        db.session.add(
            SessionInterventionGoal(session_id=session.id, intervention_goal_id=gid)
        )


def _sync_observations(session: ProfessionalSession, form) -> None:
    SessionObservation.query.filter_by(session_id=session.id).delete()
    for category, label in OBSERVATION_CHECKLIST:
        key = f"obs|{category}|{label}"
        if form.get(key) == "on":
            db.session.add(
                SessionObservation(
                    session_id=session.id,
                    category=category,
                    label=label,
                    value="observado",
                )
            )
    extra_notes = (form.get("observation_notes") or "").strip()
    if extra_notes:
        db.session.add(
            SessionObservation(
                session_id=session.id,
                category="other",
                label="Notas de observação",
                value=None,
                notes=extra_notes,
            )
        )


@care_bp.route("/patients/<int:patient_id>/sessions/new", methods=["GET", "POST"])
@login_required
def sessions_new(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    plans, assessments, instruments, intervention_plans, intervention_goals = (
        _session_form_context(patient)
    )
    if request.method == "POST":
        session = ProfessionalSession(
            patient_id=patient.id,
            professional_id=current_user.id,
        )
        errors = _apply_session_fields(session, request.form)
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            db.session.add(session)
            db.session.flush()
            _sync_observations(session, request.form)
            _sync_intervention_goals(session, request.form)
            activity_name = (request.form.get("activity_name") or "").strip()
            if activity_name:
                cat = request.form.get("activity_category") or "outro"
                db.session.add(
                    ActivityRecord(
                        session_id=session.id,
                        name=activity_name,
                        category=cat,
                        objective=(request.form.get("activity_objective") or "").strip()
                        or None,
                        description=(request.form.get("activity_description") or "").strip()
                        or None,
                        observed_response=(
                            request.form.get("activity_observed_response") or ""
                        ).strip()
                        or None,
                        notes=(request.form.get("activity_notes") or "").strip() or None,
                    )
                )
            db.session.commit()
            flash("Sessão criada.", "success")
            return redirect(
                url_for(
                    "care.sessions_view", patient_id=patient.id, session_id=session.id
                )
            )
    return render_template(
        "panel/session_form.html",
        patient=patient,
        session=None,
        mode="new",
        plans=plans,
        assessments=assessments,
        instruments=instruments,
        intervention_plans=intervention_plans,
        intervention_goals=intervention_goals,
        selected_goal_ids=set(),
        help_levels=HELP_LEVELS,
        form=request.form if request.method == "POST" else {},
        session_types=SESSION_TYPES,
        session_statuses=SESSION_STATUSES,
        participants_options=PARTICIPANT_OPTIONS,
        selected_participants=[],
        observation_checklist=OBSERVATION_CHECKLIST,
        observed=set(),
        observed_labels=set(),
        activity_categories=ACTIVITY_CATEGORIES,
    )


@care_bp.route(
    "/patients/<int:patient_id>/sessions/<int:session_id>", methods=["GET"]
)
@login_required
def sessions_view(patient_id: int, session_id: int):
    patient = _owned_patient_or_404(patient_id)
    session = _owned_session_or_404(patient_id, session_id)
    observations = session.observations.order_by(SessionObservation.id.asc()).all()
    activities = session.activities.order_by(ActivityRecord.id.asc()).all()
    linked_goals = [
        link.goal for link in session.intervention_goals.all() if link.goal
    ]
    return render_template(
        "panel/session_view.html",
        patient=patient,
        session=session,
        observations=observations,
        activities=activities,
        linked_goals=linked_goals,
        session_types=dict(SESSION_TYPES),
        session_statuses=dict(SESSION_STATUSES),
        participants=participants_from_storage(session.participants),
        help_levels=dict(HELP_LEVELS),
    )


@care_bp.route(
    "/patients/<int:patient_id>/sessions/<int:session_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def sessions_edit(patient_id: int, session_id: int):
    patient = _owned_patient_or_404(patient_id)
    session = _owned_session_or_404(patient_id, session_id)
    plans, assessments, instruments, intervention_plans, intervention_goals = (
        _session_form_context(patient)
    )

    if request.method == "POST":
        errors = _apply_session_fields(session, request.form)
        if errors:
            for e in errors:
                flash(e, "error")
        else:
            _sync_observations(session, request.form)
            _sync_intervention_goals(session, request.form)
            activity_name = (request.form.get("activity_name") or "").strip()
            if activity_name:
                cat = request.form.get("activity_category") or "outro"
                db.session.add(
                    ActivityRecord(
                        session_id=session.id,
                        name=activity_name,
                        category=cat,
                        objective=(request.form.get("activity_objective") or "").strip()
                        or None,
                        description=(request.form.get("activity_description") or "").strip()
                        or None,
                        observed_response=(
                            request.form.get("activity_observed_response") or ""
                        ).strip()
                        or None,
                        notes=(request.form.get("activity_notes") or "").strip() or None,
                    )
                )
            db.session.commit()
            flash("Sessão atualizada.", "success")
            return redirect(
                url_for(
                    "care.sessions_view", patient_id=patient.id, session_id=session.id
                )
            )

    observed = {
        o.label
        for o in session.observations.filter(SessionObservation.value == "observado").all()
    }
    selected_goal_ids = {
        link.intervention_goal_id for link in session.intervention_goals.all()
    }
    return render_template(
        "panel/session_form.html",
        patient=patient,
        session=session,
        plans=plans,
        assessments=assessments,
        instruments=instruments,
        intervention_plans=intervention_plans,
        intervention_goals=intervention_goals,
        selected_goal_ids=selected_goal_ids,
        help_levels=HELP_LEVELS,
        session_types=SESSION_TYPES,
        session_statuses=SESSION_STATUSES,
        participants_options=PARTICIPANT_OPTIONS,
        selected_participants=participants_from_storage(session.participants),
        observation_checklist=OBSERVATION_CHECKLIST,
        observed=observed,
        observed_labels=observed,
        activity_categories=ACTIVITY_CATEGORIES,
        mode="edit",
        form={},
    )


# ---------- Encaminhamentos ----------


@care_bp.route("/patients/<int:patient_id>/referrals", methods=["GET", "POST"])
@login_required
def referrals(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    if request.method == "POST":
        specialty = (request.form.get("specialty") or "").strip()
        if not specialty:
            flash("Especialidade é obrigatória.", "error")
        else:
            status = request.form.get("status") or "suggested"
            if status not in dict(REFERRAL_STATUSES):
                status = "suggested"
            db.session.add(
                Referral(
                    patient_id=patient.id,
                    professional_id=current_user.id,
                    referral_date=_parse_date(request.form.get("referral_date"))
                    or datetime.utcnow().date(),
                    specialty=specialty,
                    reason=(request.form.get("reason") or "").strip() or None,
                    status=status,
                    professional_or_service=(
                        request.form.get("professional_or_service") or ""
                    ).strip()
                    or None,
                    notes=(request.form.get("notes") or "").strip() or None,
                    session_id=request.form.get("session_id", type=int),
                    assessment_plan_id=request.form.get("assessment_plan_id", type=int),
                )
            )
            db.session.commit()
            flash("Encaminhamento registado.", "success")
            return redirect(url_for("care.referrals", patient_id=patient.id))

    rows = (
        Referral.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(Referral.referral_date.desc())
        .all()
    )
    return render_template(
        "panel/referrals_list.html",
        patient=patient,
        rows=rows,
        specialties=REFERRAL_SPECIALTIES,
        statuses=REFERRAL_STATUSES,
        status_labels=dict(REFERRAL_STATUSES),
    )


# ---------- Contacto escolar ----------


@care_bp.route("/patients/<int:patient_id>/school-contacts", methods=["GET", "POST"])
@login_required
def school_contacts(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    if request.method == "POST":
        db.session.add(
            SchoolContact(
                patient_id=patient.id,
                professional_id=current_user.id,
                contact_date=_parse_date(request.form.get("contact_date"))
                or datetime.utcnow().date(),
                school_name=(request.form.get("school_name") or "").strip() or None,
                contact_person=(request.form.get("contact_person") or "").strip() or None,
                role=(request.form.get("role") or "").strip() or None,
                purpose=(request.form.get("purpose") or "").strip() or None,
                summary=(request.form.get("summary") or "").strip() or None,
                recommendations=(request.form.get("recommendations") or "").strip()
                or None,
                notes=(request.form.get("notes") or "").strip() or None,
            )
        )
        db.session.commit()
        flash("Contacto escolar registado.", "success")
        return redirect(url_for("care.school_contacts", patient_id=patient.id))

    rows = (
        SchoolContact.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(SchoolContact.contact_date.desc())
        .all()
    )
    return render_template(
        "panel/school_contacts.html", patient=patient, rows=rows
    )


# ---------- Documentos (metadados) + Consentimentos ----------


@care_bp.route("/patients/<int:patient_id>/documents", methods=["GET", "POST"])
@login_required
def documents(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    if request.method == "POST":
        kind = request.form.get("form_kind") or "document"
        if kind == "consent":
            accepted = request.form.get("accepted") == "on"
            db.session.add(
                PatientConsent(
                    patient_id=patient.id,
                    professional_id=current_user.id,
                    guardian_id=request.form.get("guardian_id", type=int),
                    consent_type=request.form.get("consent_type") or "assessment",
                    accepted=accepted,
                    accepted_at=utcnow() if accepted else None,
                    notes=(
                        (request.form.get("notes") or "").strip()
                        or "MODELO DEMONSTRATIVO — REVISÃO JURÍDICA NECESSÁRIA."
                    ),
                )
            )
            db.session.commit()
            flash("Consentimento registado (demonstrativo).", "success")
        else:
            title = (request.form.get("title") or "").strip()
            if not title:
                flash("Título do documento é obrigatório.", "error")
            else:
                db.session.add(
                    PatientDocument(
                        patient_id=patient.id,
                        professional_id=current_user.id,
                        document_type=request.form.get("document_type") or "other",
                        title=title,
                        description=(request.form.get("description") or "").strip()
                        or None,
                        recorded_at=_parse_date(request.form.get("recorded_at"))
                        or datetime.utcnow().date(),
                        notes=(request.form.get("notes") or "").strip() or None,
                    )
                )
                db.session.commit()
                flash(
                    "Documento registado (metadados). Upload de ficheiros numa fase posterior.",
                    "success",
                )
        return redirect(url_for("care.documents", patient_id=patient.id))

    docs = (
        PatientDocument.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(PatientDocument.recorded_at.desc())
        .all()
    )
    consents = (
        PatientConsent.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(PatientConsent.created_at.desc())
        .all()
    )
    return render_template(
        "panel/documents_list.html",
        patient=patient,
        docs=docs,
        consents=consents,
        document_types=DOCUMENT_TYPES,
        consent_types=CONSENT_TYPES,
    )
