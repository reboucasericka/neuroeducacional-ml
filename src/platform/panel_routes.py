"""Área profissional (/panel): dashboard, pacientes e placeholders."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from src.platform.cognitive_timeline import build_patient_timeline
from src.platform.extensions import db
from src.platform.models import (
    Assessment,
    AssessmentPlan,
    CognitiveIndicator,
    Patient,
    PatientAnamnesis,
    PatientGuardian,
    ProfessionalSession,
    Referral,
)
from src.platform.models import FeedbackReport, InterventionPlan, ProgressNote
from src.platform.pagination_utils import paginate_query
from src.platform.record_nav import (
    TIMELINE_FILTERS,
    TIMELINE_KIND_LABELS,
    patient_new_record_actions,
    patient_record_tabs,
)
from src.platform.terminology import (
    DEFAULT_SUBJECT_BY_TYPE,
    PROFESSIONAL_TYPE_BLURBS,
    PROFESSIONAL_TYPE_LABELS,
    PROFESSIONAL_TYPES,
    SUBJECT_TERMS,
    subject_label,
    subject_label_plural,
)
from src.platform.ui_status import STATUS_LABELS as UI_STATUS_LABELS


panel_bp = Blueprint("panel", __name__, url_prefix="/panel")

SEX_CHOICES = [
    ("feminino", "Feminino"),
    ("masculino", "Masculino"),
    ("outro", "Outro"),
    ("nao_informado", "Não informado"),
]

STATUS_LABELS = {
    "draft": "Rascunho",
    "completed": "Concluída",
    "archived": "Arquivada",
}

AGE_BANDS = [
    ("0-6", "0–6 anos"),
    ("7-12", "7–12 anos"),
    ("13-17", "13–17 anos"),
    ("18+", "18+ anos"),
]

PATIENT_STATUS_FILTERS = [
    ("ativo", "Ativo"),
    ("inativo", "Inativo"),
    ("archived", "Arquivado"),
]


def _owned_patient_or_404(patient_id: int) -> Patient:
    patient = Patient.query.filter_by(
        id=patient_id, professional_id=current_user.id
    ).first()
    if patient is None:
        abort(404)
    return patient


def _shift_years(d: date, years: int) -> date:
    """Subtrai/adiciona anos sem dependência externa (aprox. para filtros de idade)."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # 29 fev → 28 fev
        return d.replace(month=2, day=28, year=d.year + years)


def _birth_date_bounds(band: str) -> tuple[date | None, date | None]:
    """Retorna (min_birth, max_birth) inclusivos para a faixa etária."""
    today = date.today()
    if band == "0-6":
        return _shift_years(today, -7) + timedelta(days=1), today
    if band == "7-12":
        return (
            _shift_years(today, -13) + timedelta(days=1),
            _shift_years(today, -7),
        )
    if band == "13-17":
        return (
            _shift_years(today, -18) + timedelta(days=1),
            _shift_years(today, -13),
        )
    if band == "18+":
        return None, _shift_years(today, -18)
    return None, None


@panel_bp.route("/")
@login_required
def dashboard():
    patients = (
        Patient.query.filter_by(professional_id=current_user.id)
        .order_by(Patient.updated_at.desc())
        .limit(5)
        .all()
    )
    assessments = (
        Assessment.query.filter_by(professional_id=current_user.id)
        .options(joinedload(Assessment.patient))
        .order_by(Assessment.assessment_date.desc())
        .limit(5)
        .all()
    )
    recent_anamneses = (
        PatientAnamnesis.query.filter_by(professional_id=current_user.id)
        .options(
            joinedload(PatientAnamnesis.template),
            joinedload(PatientAnamnesis.patient),
        )
        .order_by(PatientAnamnesis.updated_at.desc())
        .limit(5)
        .all()
    )
    today = date.today()
    sessions_today = (
        ProfessionalSession.query.filter_by(professional_id=current_user.id)
        .options(joinedload(ProfessionalSession.patient))
        .filter(ProfessionalSession.session_date == today)
        .order_by(ProfessionalSession.start_time.asc())
        .limit(8)
        .all()
    )
    upcoming_sessions = (
        ProfessionalSession.query.filter_by(professional_id=current_user.id)
        .options(joinedload(ProfessionalSession.patient))
        .filter(ProfessionalSession.session_date > today)
        .filter(ProfessionalSession.status == "planned")
        .order_by(ProfessionalSession.session_date.asc())
        .limit(8)
        .all()
    )
    active_plans = AssessmentPlan.query.filter_by(
        professional_id=current_user.id, status="active"
    ).count()
    active_interventions = InterventionPlan.query.filter_by(
        professional_id=current_user.id, status="active"
    ).count()
    pending_referrals = Referral.query.filter(
        Referral.professional_id == current_user.id,
        Referral.status.in_(["suggested", "referred", "scheduled"]),
    ).count()
    upcoming_reviews = (
        InterventionPlan.query.filter_by(professional_id=current_user.id)
        .options(joinedload(InterventionPlan.patient))
        .filter(InterventionPlan.status.in_(["active", "paused"]))
        .filter(InterventionPlan.review_date.isnot(None))
        .filter(InterventionPlan.review_date >= today)
        .order_by(InterventionPlan.review_date.asc())
        .limit(5)
        .all()
    )
    recent_progress = (
        ProgressNote.query.filter_by(professional_id=current_user.id)
        .options(joinedload(ProgressNote.patient))
        .order_by(ProgressNote.recorded_at.desc())
        .limit(5)
        .all()
    )
    stats = {
        "patients": Patient.query.filter_by(professional_id=current_user.id).count(),
        "assessments_draft": Assessment.query.filter_by(
            professional_id=current_user.id, status="draft"
        ).count(),
        "anamneses_open": PatientAnamnesis.query.filter_by(
            professional_id=current_user.id, status="draft"
        ).count(),
        "sessions_today": len(sessions_today),
        "active_plans": active_plans,
        "active_interventions": active_interventions,
        "pending_referrals": pending_referrals,
        "upcoming_reviews": len(upcoming_reviews),
        "feedbacks_draft": FeedbackReport.query.filter_by(
            professional_id=current_user.id, status="draft"
        ).count(),
    }
    return render_template(
        "panel/dashboard.html",
        stats=stats,
        recent_patients=patients,
        recent_assessments=assessments,
        recent_anamneses=recent_anamneses,
        sessions_today=sessions_today,
        upcoming_sessions=upcoming_sessions,
        upcoming_reviews=upcoming_reviews,
        recent_progress=recent_progress,
        status_labels=STATUS_LABELS,
        breadcrumbs=[{"label": "Dashboard", "url": None}],
    )


@panel_bp.route("/patients")
@login_required
def patients_list():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    age_band = (request.args.get("age") or "").strip()
    education = (request.args.get("education") or "").strip()

    query = Patient.query.filter_by(professional_id=current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Patient.name.ilike(like), Patient.internal_code.ilike(like))
        )
    if status:
        query = query.filter(Patient.status == status)
    if education:
        query = query.filter(Patient.education_level == education)
    if age_band:
        min_birth, max_birth = _birth_date_bounds(age_band)
        if min_birth is not None:
            query = query.filter(Patient.birth_date >= min_birth)
        if max_birth is not None:
            query = query.filter(Patient.birth_date <= max_birth)

    query = query.order_by(Patient.name.asc())
    page_obj = paginate_query(query)
    education_options = [
        row[0]
        for row in (
            db.session.query(Patient.education_level)
            .filter(
                Patient.professional_id == current_user.id,
                Patient.education_level.isnot(None),
                Patient.education_level != "",
            )
            .distinct()
            .order_by(Patient.education_level.asc())
            .all()
        )
        if row[0]
    ]
    return render_template(
        "panel/patients_list.html",
        patients=page_obj.items,
        page_obj=page_obj,
        q=q,
        status=status,
        age_band=age_band,
        education=education,
        age_bands=AGE_BANDS,
        status_filters=PATIENT_STATUS_FILTERS,
        education_options=education_options,
        breadcrumbs=[
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {"label": subject_label_plural(current_user), "url": None},
        ],
    )


@panel_bp.route("/patients/new", methods=["GET", "POST"])
@login_required
def patients_new():
    crumbs = [
        {"label": "Dashboard", "url": url_for("panel.dashboard")},
        {
            "label": subject_label_plural(current_user),
            "url": url_for("panel.patients_list"),
        },
        {"label": f"Novo {subject_label(current_user).lower()}", "url": None},
    ]
    if request.method == "POST":
        try:
            birth_date = datetime.strptime(
                request.form.get("birth_date") or "", "%Y-%m-%d"
            ).date()
        except ValueError:
            flash("Data de nascimento inválida.", "error")
            return render_template(
                "panel/patient_form.html",
                sex_choices=SEX_CHOICES,
                form=request.form,
                breadcrumbs=crumbs,
            )

        code = (request.form.get("internal_code") or "").strip().upper()
        name = (request.form.get("name") or "").strip()
        sex = request.form.get("sex") or "nao_informado"
        is_minor = request.form.get("is_minor") == "on"

        if not code or not name:
            flash("Código interno e nome são obrigatórios.", "error")
            return render_template(
                "panel/patient_form.html",
                sex_choices=SEX_CHOICES,
                form=request.form,
                breadcrumbs=crumbs,
            )

        exists = Patient.query.filter_by(
            professional_id=current_user.id, internal_code=code
        ).first()
        if exists:
            flash(
                f"Já existe um {subject_label(current_user).lower()} com esse código interno.",
                "error",
            )
            return render_template(
                "panel/patient_form.html",
                sex_choices=SEX_CHOICES,
                form=request.form,
                breadcrumbs=crumbs,
            )

        patient = Patient(
            professional_id=current_user.id,
            internal_code=code,
            name=name,
            birth_date=birth_date,
            sex=sex,
            gender=(request.form.get("gender") or "").strip() or None,
            education_level=(request.form.get("education_level") or "").strip() or None,
            occupation=(request.form.get("occupation") or "").strip() or None,
            contact_phone=(request.form.get("contact_phone") or "").strip() or None,
            contact_email=(request.form.get("contact_email") or "").strip() or None,
            is_minor=is_minor,
            notes=(request.form.get("notes") or "").strip() or None,
            status="ativo",
        )
        db.session.add(patient)
        db.session.flush()

        if is_minor:
            g_name = (request.form.get("guardian_name") or "").strip()
            if g_name:
                db.session.add(
                    PatientGuardian(
                        patient_id=patient.id,
                        name=g_name,
                        relationship=(
                            request.form.get("guardian_relationship") or "responsável"
                        ).strip(),
                        phone=(request.form.get("guardian_phone") or "").strip() or None,
                        email=(request.form.get("guardian_email") or "").strip() or None,
                        is_primary=True,
                    )
                )

        db.session.commit()
        flash(f"{subject_label(current_user)} criado com sucesso.", "success")
        return redirect(url_for("panel.patient_detail", patient_id=patient.id))

    return render_template(
        "panel/patient_form.html",
        sex_choices=SEX_CHOICES,
        form={},
        breadcrumbs=crumbs,
    )


@panel_bp.route("/patients/<int:patient_id>")
@login_required
def patient_detail(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    tab = request.args.get("tab") or "overview"
    if tab == "history":
        return redirect(
            url_for("panel.patient_detail", patient_id=patient.id, tab="timeline")
        )
    if tab == "profile":
        return redirect(url_for("cognitive.cognitive_profile", patient_id=patient.id))
    if tab == "plan":
        return redirect(url_for("care.plans_list", patient_id=patient.id))
    if tab == "sessions":
        return redirect(url_for("care.sessions_list", patient_id=patient.id))
    if tab == "referrals":
        return redirect(url_for("care.referrals", patient_id=patient.id))
    if tab == "documents":
        return redirect(url_for("care.documents", patient_id=patient.id))
    if tab in ("feedbacks", "devolutiva"):
        return redirect(url_for("intervention.feedbacks_list", patient_id=patient.id))
    if tab == "intervention":
        return redirect(url_for("intervention.interventions_list", patient_id=patient.id))
    if tab == "evolution":
        return redirect(url_for("intervention.evolution_view", patient_id=patient.id))

    assessments = (
        Assessment.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .options(joinedload(Assessment.professional))
        .order_by(Assessment.assessment_date.desc(), Assessment.id.desc())
        .all()
    )
    instruments_by_assessment: dict[int, list] = {}
    if assessments:
        from collections import defaultdict

        from src.platform.models import AssessmentInstrument

        grouped: dict[int, list] = defaultdict(list)
        for item in (
            AssessmentInstrument.query.filter(
                AssessmentInstrument.assessment_id.in_([a.id for a in assessments])
            )
            .order_by(AssessmentInstrument.id.asc())
            .all()
        ):
            grouped[item.assessment_id].append(item)
        instruments_by_assessment = grouped

    assessment_rows = []
    instruments_used: dict[str, str] = {}
    for assessment in assessments:
        items = instruments_by_assessment.get(assessment.id, [])
        for item in items:
            instruments_used[item.display_name] = item.display_short_name or ""
        assessment_rows.append(
            {
                "assessment": assessment,
                "instrument_count": len(items),
                "instrument_names": ", ".join(
                    i.display_short_name or i.display_name for i in items
                )
                or "—",
            }
        )
    anamneses = (
        PatientAnamnesis.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .options(
            joinedload(PatientAnamnesis.template),
            joinedload(PatientAnamnesis.professional),
        )
        .order_by(PatientAnamnesis.started_at.desc())
        .all()
    )
    anamnesis_summary = {
        "total": len(anamneses),
        "draft": sum(1 for a in anamneses if a.status == "draft"),
        "completed": sum(1 for a in anamneses if a.status == "completed"),
        "last": anamneses[0] if anamneses else None,
    }
    assessment_summary = {
        "total": len(assessments),
        "draft": sum(1 for a in assessments if a.status == "draft"),
        "completed": sum(1 for a in assessments if a.status == "completed"),
        "last": assessments[0] if assessments else None,
        "instruments_used": sorted(instruments_used.keys()),
        "recent": assessments[:3],
    }
    active_plan = (
        AssessmentPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id, status="active"
        )
        .order_by(AssessmentPlan.updated_at.desc())
        .first()
    )
    active_intervention = (
        InterventionPlan.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id, status="active"
        )
        .order_by(InterventionPlan.updated_at.desc())
        .first()
    )
    today = date.today()
    next_session = (
        ProfessionalSession.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id, status="planned"
        )
        .filter(ProfessionalSession.session_date >= today)
        .order_by(ProfessionalSession.session_date.asc())
        .first()
    )
    last_session = (
        ProfessionalSession.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(ProfessionalSession.session_date.desc())
        .first()
    )
    last_indicator = (
        CognitiveIndicator.query.filter_by(
            patient_id=patient.id, professional_id=current_user.id
        )
        .order_by(CognitiveIndicator.updated_at.desc())
        .first()
    )
    pending_referrals = Referral.query.filter(
        Referral.patient_id == patient.id,
        Referral.professional_id == current_user.id,
        Referral.status.in_(["suggested", "referred", "scheduled"]),
    ).count()
    care_summary = {
        "active_plan": active_plan,
        "active_intervention": active_intervention,
        "next_session": next_session,
        "last_session": last_session,
        "last_indicator": last_indicator,
        "pending_referrals": pending_referrals,
        "next_review": active_intervention.review_date if active_intervention else None,
    }

    timeline_filter = (request.args.get("kind") or "").strip()
    timeline_period = (request.args.get("period") or "all").strip()
    months = {"3m": 3, "6m": 6, "12m": 12}.get(timeline_period)
    timeline_events = []
    recent_activity = []
    if tab in ("overview", "timeline"):
        timeline_events = build_patient_timeline(
            patient,
            current_user.id,
            months=months if tab == "timeline" else 6,
            kind_filter=timeline_filter if tab == "timeline" else None,
        )
        if tab == "overview":
            recent_activity = timeline_events[:6]
            timeline_events = []

    tab_label = {
        "overview": "Visão Geral",
        "anamnesis": "Anamnese",
        "assessments": "Avaliações",
        "timeline": "Timeline",
    }.get(tab, tab)
    crumbs = [
        {"label": "Dashboard", "url": url_for("panel.dashboard")},
        {
            "label": subject_label_plural(current_user),
            "url": url_for("panel.patients_list"),
        },
        {
            "label": patient.name,
            "url": (
                url_for("panel.patient_detail", patient_id=patient.id)
                if tab != "overview"
                else None
            ),
        },
    ]
    if tab != "overview":
        crumbs.append({"label": tab_label, "url": None})

    return render_template(
        "panel/patient_detail.html",
        patient=patient,
        tab=tab,
        assessments=assessments,
        assessment_rows=assessment_rows,
        assessment_summary=assessment_summary,
        anamneses=anamneses,
        anamnesis_summary=anamnesis_summary,
        care_summary=care_summary,
        sex_choices=dict(SEX_CHOICES),
        status_labels={**UI_STATUS_LABELS, **STATUS_LABELS},
        record_tabs=patient_record_tabs(patient.id, active=tab),
        new_record_actions=patient_new_record_actions(patient.id),
        timeline_events=timeline_events,
        recent_activity=recent_activity,
        timeline_filters=TIMELINE_FILTERS,
        timeline_kind_labels=TIMELINE_KIND_LABELS,
        timeline_filter=timeline_filter,
        timeline_period=timeline_period,
        breadcrumbs=crumbs,
    )


@panel_bp.route("/reports")
@login_required
def reports_placeholder():
    return render_template(
        "panel/placeholder.html",
        title="Relatórios",
        message="Placeholder. Relatórios profissionais serão desenvolvidos mais tarde.",
        breadcrumbs=[
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {"label": "Relatórios", "url": None},
        ],
    )


@panel_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    """Escolha leve de área de atuação (arquitetura preparada; sem signup público)."""
    if current_user.onboarding_completed:
        return redirect(url_for("panel.dashboard"))

    if request.method == "POST":
        ptype = (request.form.get("professional_type") or "").strip()
        if ptype not in PROFESSIONAL_TYPES:
            flash("Selecione uma área de atuação válida.", "error")
        else:
            current_user.professional_type = ptype
            term = (request.form.get("preferred_subject_term") or "").strip()
            if term not in SUBJECT_TERMS:
                term = DEFAULT_SUBJECT_BY_TYPE[ptype]
            current_user.preferred_subject_term = term
            current_user.onboarding_completed = True
            current_user.touch()
            db.session.commit()
            flash("Perfil configurado.", "success")
            return redirect(url_for("panel.dashboard"))

    return render_template(
        "panel/onboarding.html",
        types=PROFESSIONAL_TYPES,
        type_labels=PROFESSIONAL_TYPE_LABELS,
        type_blurbs=PROFESSIONAL_TYPE_BLURBS,
        defaults=DEFAULT_SUBJECT_BY_TYPE,
    )


@panel_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    crumbs = [
        {"label": "Dashboard", "url": url_for("panel.dashboard")},
        {"label": "Perfil", "url": None},
    ]
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        ptype = (request.form.get("professional_type") or "").strip()
        subject_term = (request.form.get("preferred_subject_term") or "").strip()

        errors = []
        if not name:
            errors.append("Nome é obrigatório.")
        if not email:
            errors.append("E-mail é obrigatório.")
        if ptype not in PROFESSIONAL_TYPES:
            errors.append("Tipo profissional inválido.")
        if subject_term and subject_term not in SUBJECT_TERMS:
            errors.append("Termo preferido inválido.")

        from src.platform.models import Professional

        other = Professional.query.filter(
            Professional.email == email, Professional.id != current_user.id
        ).first()
        if other:
            errors.append("Esse e-mail já está em uso.")

        if errors:
            for err in errors:
                flash(err, "error")
        else:
            current_user.name = name
            current_user.email = email
            current_user.professional_type = ptype
            current_user.registration_number = (
                request.form.get("registration_number") or ""
            ).strip() or None
            current_user.education = (request.form.get("education") or "").strip() or None
            current_user.specialization = (
                request.form.get("specialization") or ""
            ).strip() or None
            current_user.workplace = (request.form.get("workplace") or "").strip() or None
            current_user.phone = (request.form.get("phone") or "").strip() or None
            current_user.city = (request.form.get("city") or "").strip() or None
            current_user.state = (request.form.get("state") or "").strip() or None
            current_user.bio = (request.form.get("bio") or "").strip() or None
            if subject_term:
                current_user.preferred_subject_term = subject_term
            elif not current_user.preferred_subject_term:
                current_user.preferred_subject_term = DEFAULT_SUBJECT_BY_TYPE[ptype]
            current_user.touch()
            db.session.commit()
            flash("Perfil atualizado.", "success")
            return redirect(url_for("panel.profile"))

    return render_template(
        "panel/profile.html",
        types=PROFESSIONAL_TYPES,
        type_labels=PROFESSIONAL_TYPE_LABELS,
        breadcrumbs=crumbs,
    )


@panel_bp.route("/settings")
@login_required
def settings_placeholder():
    return render_template(
        "panel/settings.html",
        breadcrumbs=[
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {"label": "Configurações", "url": None},
        ],
    )
