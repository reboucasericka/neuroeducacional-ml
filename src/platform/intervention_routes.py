"""Devolutiva, plano de intervenção e evolução longitudinal."""

from __future__ import annotations

from datetime import date, datetime

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from src.platform.care_flow_constants import (
    ASSESSMENT_TYPES,
    FEEDBACK_STATUSES,
    GOAL_PRIORITIES,
    HELP_LEVELS,
    INTERVENTION_GOAL_STATUSES,
    INTERVENTION_PLAN_STATUSES,
    INTERVENTION_REVIEW_DECISIONS,
    PROGRESS_STATUSES,
    STRATEGY_EXAMPLES,
)
from src.platform.evidence_panel import collect_evidence
from src.platform.extensions import db
from src.platform.models import (
    Assessment,
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    FeedbackReport,
    InterventionGoal,
    InterventionPlan,
    InterventionPlanReview,
    InterventionStrategy,
    Patient,
    ProfessionalSession,
    ProgressMeasure,
    ProgressNote,
    SessionInterventionGoal,
    utcnow,
)
from src.platform.terminology import practice_context


intervention_bp = Blueprint("intervention", __name__, url_prefix="/panel")


def _owned_patient_or_404(patient_id: int) -> Patient:
    patient = Patient.query.filter_by(
        id=patient_id, professional_id=current_user.id
    ).first()
    if patient is None:
        abort(404)
    return patient


def _owned_feedback_or_404(patient_id: int, feedback_id: int) -> FeedbackReport:
    row = FeedbackReport.query.filter_by(
        id=feedback_id, patient_id=patient_id, professional_id=current_user.id
    ).first()
    if row is None:
        abort(404)
    return row


def _owned_plan_or_404(patient_id: int, plan_id: int) -> InterventionPlan:
    row = InterventionPlan.query.filter_by(
        id=plan_id, patient_id=patient_id, professional_id=current_user.id
    ).first()
    if row is None:
        abort(404)
    return row


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return None


def _context_ui_hints(pro_type: str | None) -> dict:
    ctx = practice_context(pro_type)
    if ctx == "institutional":
        return {
            "guidance_first": "school",
            "emphasis": "Contexto escolar, observação e estratégias educacionais.",
        }
    if ctx == "psychopedagogical":
        return {
            "guidance_first": "learning",
            "emphasis": "Aprendizagem, potencialidades e estratégias com família/escola.",
        }
    return {
        "guidance_first": "family",
        "emphasis": "Família, avaliação, intervenção e encaminhamentos.",
    }


# ---------- Devolutivas ----------


@intervention_bp.route("/patients/<int:patient_id>/feedbacks")
@login_required
def feedbacks_list(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    rows = (
        FeedbackReport.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(FeedbackReport.feedback_date.desc(), FeedbackReport.id.desc())
        .all()
    )
    return render_template(
        "panel/feedbacks_list.html",
        patient=patient,
        rows=rows,
        status_labels=dict(FEEDBACK_STATUSES),
        ui_hints=_context_ui_hints(current_user.professional_type),
    )


@intervention_bp.route("/patients/<int:patient_id>/feedbacks/new", methods=["GET", "POST"])
@login_required
def feedbacks_new(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    evidence = collect_evidence(patient.id, current_user.id)
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Título é obrigatório.", "error")
        else:
            report = FeedbackReport(
                patient_id=patient.id,
                professional_id=current_user.id,
                title=title,
                status="draft",
            )
            _apply_feedback_fields(report, request.form)
            db.session.add(report)
            db.session.commit()
            flash("Devolutiva criada (rascunho).", "success")
            return redirect(
                url_for(
                    "intervention.feedbacks_edit",
                    patient_id=patient.id,
                    feedback_id=report.id,
                )
            )
    return render_template(
        "panel/feedback_form.html",
        patient=patient,
        report=None,
        mode="new",
        evidence=evidence,
        status_labels=dict(FEEDBACK_STATUSES),
        ui_hints=_context_ui_hints(current_user.professional_type),
        form=request.form if request.method == "POST" else {},
    )


def _apply_feedback_fields(report: FeedbackReport, form) -> None:
    report.title = (form.get("title") or report.title or "").strip() or report.title
    fd = _parse_date(form.get("feedback_date"))
    if fd:
        report.feedback_date = fd
    report.assessment_plan_id = form.get("assessment_plan_id", type=int) or None
    for field in (
        "summary",
        "reason_for_assessment",
        "history_summary",
        "assessment_summary",
        "strengths",
        "difficulties",
        "resources_and_strategies",
        "preserved_areas",
        "interests",
        "professional_conclusion",
        "recommendations",
        "family_guidance",
        "school_guidance",
        "learning_strategies",
        "suggested_adaptations",
        "referral_notes",
    ):
        setattr(report, field, (form.get(field) or "").strip() or None)
    report.touch()


@intervention_bp.route(
    "/patients/<int:patient_id>/feedbacks/<int:feedback_id>", methods=["GET"]
)
@login_required
def feedbacks_view(patient_id: int, feedback_id: int):
    patient = _owned_patient_or_404(patient_id)
    report = _owned_feedback_or_404(patient_id, feedback_id)
    return render_template(
        "panel/feedback_view.html",
        patient=patient,
        report=report,
        status_labels=dict(FEEDBACK_STATUSES),
        ui_hints=_context_ui_hints(current_user.professional_type),
        print_mode=request.args.get("print") == "1",
    )


@intervention_bp.route(
    "/patients/<int:patient_id>/feedbacks/<int:feedback_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def feedbacks_edit(patient_id: int, feedback_id: int):
    patient = _owned_patient_or_404(patient_id)
    report = _owned_feedback_or_404(patient_id, feedback_id)
    if report.status == "completed" and request.method == "GET":
        flash("Devolutiva concluída — reabra para editar.", "info")
        return redirect(
            url_for(
                "intervention.feedbacks_view",
                patient_id=patient.id,
                feedback_id=report.id,
            )
        )
    if report.status == "completed":
        abort(403)
    evidence = collect_evidence(patient.id, current_user.id)
    if request.method == "POST":
        action = request.form.get("action") or "save"
        _apply_feedback_fields(report, request.form)
        if action == "complete":
            report.status = "completed"
            report.completed_at = utcnow()
            flash("Devolutiva concluída.", "success")
        else:
            report.status = "draft"
            flash("Rascunho guardado.", "success")
        db.session.commit()
        if action == "complete":
            return redirect(
                url_for(
                    "intervention.feedbacks_view",
                    patient_id=patient.id,
                    feedback_id=report.id,
                )
            )
        return redirect(
            url_for(
                "intervention.feedbacks_edit",
                patient_id=patient.id,
                feedback_id=report.id,
            )
        )
    return render_template(
        "panel/feedback_form.html",
        patient=patient,
        report=report,
        mode="edit",
        evidence=evidence,
        status_labels=dict(FEEDBACK_STATUSES),
        ui_hints=_context_ui_hints(current_user.professional_type),
        form=None,
    )


@intervention_bp.route(
    "/patients/<int:patient_id>/feedbacks/<int:feedback_id>/reopen",
    methods=["POST"],
)
@login_required
def feedbacks_reopen(patient_id: int, feedback_id: int):
    patient = _owned_patient_or_404(patient_id)
    report = _owned_feedback_or_404(patient_id, feedback_id)
    report.status = "draft"
    report.completed_at = None
    report.touch()
    db.session.commit()
    flash("Devolutiva reaberta para edição.", "success")
    return redirect(
        url_for(
            "intervention.feedbacks_edit",
            patient_id=patient.id,
            feedback_id=report.id,
        )
    )


# ---------- Planos de intervenção ----------


@intervention_bp.route("/patients/<int:patient_id>/interventions")
@login_required
def interventions_list(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    plans = (
        InterventionPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(InterventionPlan.updated_at.desc())
        .all()
    )
    return render_template(
        "panel/interventions_list.html",
        patient=patient,
        plans=plans,
        status_labels=dict(INTERVENTION_PLAN_STATUSES),
        ui_hints=_context_ui_hints(current_user.professional_type),
    )


@intervention_bp.route(
    "/patients/<int:patient_id>/interventions/new", methods=["GET", "POST"]
)
@login_required
def interventions_new(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    feedbacks = (
        FeedbackReport.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(FeedbackReport.feedback_date.desc())
        .all()
    )
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        if not title:
            flash("Título é obrigatório.", "error")
        else:
            plan = InterventionPlan(
                patient_id=patient.id,
                professional_id=current_user.id,
                title=title,
                status="draft",
            )
            _apply_plan_fields(plan, request.form)
            db.session.add(plan)
            db.session.commit()
            flash("Plano de intervenção criado.", "success")
            return redirect(
                url_for(
                    "intervention.interventions_edit",
                    patient_id=patient.id,
                    plan_id=plan.id,
                )
            )
    return render_template(
        "panel/intervention_plan_form.html",
        patient=patient,
        plan=None,
        mode="new",
        feedbacks=feedbacks,
        status_labels=dict(INTERVENTION_PLAN_STATUSES),
        form={},
    )


def _apply_plan_fields(plan: InterventionPlan, form) -> None:
    plan.title = (form.get("title") or plan.title or "").strip() or plan.title
    status = form.get("status") or plan.status
    if status in dict(INTERVENTION_PLAN_STATUSES):
        plan.status = status
        if status == "completed" and not plan.completed_at:
            plan.completed_at = utcnow()
    plan.reason = (form.get("reason") or "").strip() or None
    plan.general_goal = (form.get("general_goal") or "").strip() or None
    plan.notes = (form.get("notes") or "").strip() or None
    plan.feedback_report_id = form.get("feedback_report_id", type=int) or None
    plan.start_date = _parse_date(form.get("start_date"))
    plan.end_date = _parse_date(form.get("end_date"))
    plan.review_date = _parse_date(form.get("review_date"))
    plan.touch()


@intervention_bp.route(
    "/patients/<int:patient_id>/interventions/<int:plan_id>",
    methods=["GET", "POST"],
)
@login_required
def interventions_edit(patient_id: int, plan_id: int):
    patient = _owned_patient_or_404(patient_id)
    plan = _owned_plan_or_404(patient_id, plan_id)
    domains = CognitiveDomain.query.order_by(CognitiveDomain.sort_order.asc()).all()
    skills = CognitiveSkill.query.order_by(CognitiveSkill.name.asc()).all()
    feedbacks = (
        FeedbackReport.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(FeedbackReport.feedback_date.desc())
        .all()
    )
    if request.method == "POST":
        action = request.form.get("action") or "save_plan"
        if action == "save_plan":
            _apply_plan_fields(plan, request.form)
            db.session.commit()
            flash("Plano atualizado.", "success")
        elif action == "add_goal":
            title = (request.form.get("goal_title") or "").strip()
            if not title:
                flash("Título do objetivo é obrigatório.", "error")
            else:
                goal = InterventionGoal(
                    intervention_plan_id=plan.id,
                    title=title,
                    description=(request.form.get("goal_description") or "").strip()
                    or None,
                    develop_what=(request.form.get("develop_what") or "").strip()
                    or None,
                    how_observed=(request.form.get("how_observed") or "").strip()
                    or None,
                    context_notes=(request.form.get("context_notes") or "").strip()
                    or None,
                    how_know_progress=(request.form.get("how_know_progress") or "").strip()
                    or None,
                    review_deadline=_parse_date(request.form.get("review_deadline")),
                    priority=request.form.get("priority") or None,
                    baseline_notes=(request.form.get("baseline_notes") or "").strip()
                    or None,
                    success_criteria=(request.form.get("success_criteria") or "").strip()
                    or None,
                    domain_id=request.form.get("domain_id", type=int) or None,
                    skill_id=request.form.get("skill_id", type=int) or None,
                    status=request.form.get("goal_status") or "planned",
                    sort_order=plan.goals.count(),
                )
                if goal.status not in dict(INTERVENTION_GOAL_STATUSES):
                    goal.status = "planned"
                db.session.add(goal)
                plan.touch()
                db.session.commit()
                flash("Objetivo adicionado.", "success")
        elif action == "add_strategy":
            goal_id = request.form.get("strategy_goal_id", type=int)
            name = (request.form.get("strategy_name") or "").strip()
            goal = InterventionGoal.query.filter_by(
                id=goal_id, intervention_plan_id=plan.id
            ).first()
            if not goal or not name:
                flash("Estratégia inválida.", "error")
            else:
                db.session.add(
                    InterventionStrategy(
                        intervention_goal_id=goal.id,
                        name=name,
                        description=(request.form.get("strategy_description") or "").strip()
                        or None,
                        frequency=(request.form.get("strategy_frequency") or "").strip()
                        or None,
                        materials=(request.form.get("strategy_materials") or "").strip()
                        or None,
                        context=(request.form.get("strategy_context") or "").strip()
                        or None,
                        notes=(request.form.get("strategy_notes") or "").strip() or None,
                        sort_order=goal.strategies.count(),
                    )
                )
                db.session.commit()
                flash("Estratégia adicionada.", "success")
        elif action == "cancel_goal":
            gid = request.form.get("goal_id", type=int)
            goal = InterventionGoal.query.filter_by(
                id=gid, intervention_plan_id=plan.id
            ).first()
            if goal:
                goal.status = "cancelled"
                goal.touch()
                db.session.commit()
                flash("Objetivo marcado como cancelado (histórico preservado).", "success")
        elif action == "add_review":
            decision = request.form.get("decision") or "continue"
            if decision not in dict(INTERVENTION_REVIEW_DECISIONS):
                decision = "continue"
            review = InterventionPlanReview(
                intervention_plan_id=plan.id,
                professional_id=current_user.id,
                review_date=_parse_date(request.form.get("review_date"))
                or date.today(),
                summary=(request.form.get("review_summary") or "").strip() or None,
                goals_review=(request.form.get("goals_review") or "").strip() or None,
                changes=(request.form.get("review_changes") or "").strip() or None,
                decision=decision,
            )
            db.session.add(review)
            if decision == "pause":
                plan.status = "paused"
            elif decision == "complete":
                plan.status = "completed"
                plan.completed_at = utcnow()
            elif decision == "continue" and plan.status == "paused":
                plan.status = "active"
            plan.touch()
            db.session.commit()
            flash("Revisão registada.", "success")
        return redirect(
            url_for(
                "intervention.interventions_edit",
                patient_id=patient.id,
                plan_id=plan.id,
            )
        )

    goal_rows = []
    for g in plan.goals.order_by(InterventionGoal.sort_order.asc()).all():
        session_count = SessionInterventionGoal.query.filter_by(
            intervention_goal_id=g.id
        ).count()
        last_note = (
            ProgressNote.query.filter_by(
                intervention_goal_id=g.id, professional_id=current_user.id
            )
            .order_by(ProgressNote.recorded_at.desc())
            .first()
        )
        goal_rows.append(
            {
                "goal": g,
                "session_count": session_count,
                "last_note": last_note,
                "strategies": g.strategies.filter_by(is_active=True).all(),
            }
        )
    reviews = plan.reviews.order_by(InterventionPlanReview.review_date.desc()).all()
    return render_template(
        "panel/intervention_plan_form.html",
        patient=patient,
        plan=plan,
        mode="edit",
        feedbacks=feedbacks,
        goal_rows=goal_rows,
        reviews=reviews,
        domains=domains,
        skills=skills,
        status_labels=dict(INTERVENTION_PLAN_STATUSES),
        goal_statuses=INTERVENTION_GOAL_STATUSES,
        priorities=GOAL_PRIORITIES,
        review_decisions=INTERVENTION_REVIEW_DECISIONS,
        strategy_examples=STRATEGY_EXAMPLES,
        progress_labels=dict(PROGRESS_STATUSES),
    )


# ---------- Evolução ----------


@intervention_bp.route("/patients/<int:patient_id>/evolution")
@login_required
def evolution_view(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    plans = (
        InterventionPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(InterventionPlan.updated_at.desc())
        .all()
    )
    notes = (
        ProgressNote.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(ProgressNote.recorded_at.desc())
        .limit(40)
        .all()
    )
    reassessments = (
        Assessment.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .filter(Assessment.assessment_type.in_(("follow_up", "reevaluation")))
        .order_by(Assessment.assessment_date.desc())
        .all()
    )
    indicators = (
        CognitiveIndicator.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(CognitiveIndicator.recorded_at.desc())
        .limit(30)
        .all()
    )
    intervention_sessions = (
        ProfessionalSession.query.filter_by(
            patient_id=patient.id,
            professional_id=current_user.id,
            session_type="intervention",
        )
        .order_by(ProfessionalSession.session_date.desc())
        .limit(20)
        .all()
    )
    return render_template(
        "panel/evolution.html",
        patient=patient,
        plans=plans,
        notes=notes,
        reassessments=reassessments,
        indicators=indicators,
        intervention_sessions=intervention_sessions,
        progress_labels=dict(PROGRESS_STATUSES),
        plan_status_labels=dict(INTERVENTION_PLAN_STATUSES),
        assessment_types=dict(ASSESSMENT_TYPES),
        ui_hints=_context_ui_hints(current_user.professional_type),
    )


@intervention_bp.route(
    "/patients/<int:patient_id>/progress-notes/new", methods=["GET", "POST"]
)
@login_required
def progress_notes_new(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    plans = (
        InterventionPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(InterventionPlan.title.asc())
        .all()
    )
    goals = []
    for p in plans:
        goals.extend(p.goals.all())
    sessions = (
        ProfessionalSession.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(ProfessionalSession.session_date.desc())
        .limit(30)
        .all()
    )
    if request.method == "POST":
        status = request.form.get("progress_status") or "not_observed"
        if status not in dict(PROGRESS_STATUSES):
            status = "not_observed"
        note = ProgressNote(
            patient_id=patient.id,
            professional_id=current_user.id,
            progress_status=status,
            summary=(request.form.get("summary") or "").strip() or None,
            evidence=(request.form.get("evidence") or "").strip() or None,
            professional_interpretation=(
                request.form.get("professional_interpretation") or ""
            ).strip()
            or None,
            next_step=(request.form.get("next_step") or "").strip() or None,
            session_id=request.form.get("session_id", type=int) or None,
            intervention_plan_id=request.form.get("intervention_plan_id", type=int)
            or None,
            intervention_goal_id=request.form.get("intervention_goal_id", type=int)
            or None,
            recorded_at=utcnow(),
        )
        db.session.add(note)
        db.session.flush()
        m_label = (request.form.get("measure_label") or "").strip()
        if m_label:
            raw_val = (request.form.get("measure_value") or "").strip()
            value = None
            if raw_val:
                try:
                    value = float(raw_val.replace(",", "."))
                except ValueError:
                    value = None
            db.session.add(
                ProgressMeasure(
                    progress_note_id=note.id,
                    label=m_label,
                    value_numeric=value,
                    unit=(request.form.get("measure_unit") or "").strip() or None,
                    scale_reference=(request.form.get("measure_scale") or "").strip()
                    or None,
                    notes=(request.form.get("measure_notes") or "").strip() or None,
                )
            )
        db.session.commit()
        flash("Evolução registada.", "success")
        return redirect(url_for("intervention.evolution_view", patient_id=patient.id))
    return render_template(
        "panel/progress_note_form.html",
        patient=patient,
        plans=plans,
        goals=goals,
        sessions=sessions,
        progress_statuses=PROGRESS_STATUSES,
        form={},
    )
