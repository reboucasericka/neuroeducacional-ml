"""Rotas do catálogo de instrumentos e avaliações profissionais."""

from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from src.platform.anamnesis_utils import slugify
from src.platform.cognitive_indicators import (
    remove_indicator_for_result,
    upsert_indicator_from_result,
)
from src.platform.extensions import db
from src.platform.care_flow_constants import ASSESSMENT_TYPES
from src.platform.instruments_seed import (
    INSTRUMENT_CATEGORIES,
    LICENSE_STATUSES,
    ensure_scopes_for_instrument,
)
from src.platform.models import (
    Assessment,
    AssessmentInstrument,
    AssessmentResult,
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    Instrument,
    InstrumentProfessionalScope,
    Patient,
    utcnow,
)
from src.platform.pagination_utils import paginate_query
from src.platform.terminology import (
    COPYRIGHT_STATUSES,
    DIGITAL_USE_STATUSES,
    normalize_professional_type,
    professional_type_label,
    scope_status_label,
)

assessment_bp = Blueprint("assessment", __name__, url_prefix="/panel")

STATUS_LABELS = {
    "draft": "Rascunho",
    "completed": "Concluída",
    "archived": "Arquivada",
}

AI_STATUS_LABELS = {
    "pending": "Pendente",
    "in_progress": "Em progresso",
    "completed": "Concluído",
    "skipped": "Omitido",
}

LICENSE_LABELS = dict(LICENSE_STATUSES)

POPULATION_CHOICES = [
    ("crianca", "Criança"),
    ("adolescente", "Adolescente"),
    ("adulto", "Adulto"),
    ("crianca_adolescente", "Criança / Adolescente"),
    ("adolescente_adulto", "Adolescente / Adulto"),
    ("crianca_adolescente_adulto", "Todas as idades"),
    ("outro", "Outro"),
]


def _owned_patient_or_404(patient_id: int) -> Patient:
    patient = Patient.query.filter_by(
        id=patient_id, professional_id=current_user.id
    ).first()
    if patient is None:
        abort(404)
    return patient


def _owned_assessment_or_404(patient_id: int, assessment_id: int) -> Assessment:
    assessment = Assessment.query.filter_by(
        id=assessment_id,
        patient_id=patient_id,
        professional_id=current_user.id,
    ).first()
    if assessment is None:
        abort(404)
    return assessment


def _parse_optional_int(raw: str | None) -> int | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_optional_float(raw: str | None) -> float | None:
    value = (raw or "").strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _unique_instrument_slug(base: str, exclude_id: int | None = None) -> str:
    candidate = base or "instrumento"
    n = 2
    while True:
        q = Instrument.query.filter_by(slug=candidate)
        if exclude_id is not None:
            q = q.filter(Instrument.id != exclude_id)
        if q.first() is None:
            return candidate
        candidate = f"{base}-{n}"
        n += 1


def age_outside_instrument_range(
    age: int | None, minimum_age: int | None, maximum_age: int | None
) -> bool:
    if age is None:
        return False
    if minimum_age is not None and age < minimum_age:
        return True
    if maximum_age is not None and age > maximum_age:
        return True
    return False


def _instrument_form_from_model(instrument: Instrument) -> dict:
    return {
        "name": instrument.name,
        "short_name": instrument.short_name or "",
        "slug": instrument.slug or "",
        "category": instrument.category,
        "description": instrument.description or "",
        "target_population": instrument.target_population or "",
        "minimum_age": "" if instrument.minimum_age is None else str(instrument.minimum_age),
        "maximum_age": "" if instrument.maximum_age is None else str(instrument.maximum_age),
        "purpose": instrument.purpose or "",
        "license_status": instrument.license_status or "unknown",
        "reference": instrument.reference or "",
        "notes": instrument.notes or "",
    }


def _apply_instrument_form(instrument: Instrument, form) -> list[str]:
    errors: list[str] = []
    name = (form.get("name") or "").strip()
    if not name:
        errors.append("Nome é obrigatório.")
    short_name = (form.get("short_name") or "").strip() or None
    slug_raw = (form.get("slug") or "").strip() or name
    slug = _unique_instrument_slug(
        slugify(slug_raw), exclude_id=getattr(instrument, "id", None)
    )
    category = (form.get("category") or "Outros").strip() or "Outros"
    if category not in INSTRUMENT_CATEGORIES:
        category = "Outros"
    license_status = (form.get("license_status") or "unknown").strip()
    if license_status not in LICENSE_LABELS:
        license_status = "unknown"

    if errors:
        return errors

    instrument.name = name
    instrument.short_name = short_name
    instrument.slug = slug
    instrument.category = category
    instrument.description = (form.get("description") or "").strip() or None
    instrument.target_population = (form.get("target_population") or "").strip() or None
    instrument.minimum_age = _parse_optional_int(form.get("minimum_age"))
    instrument.maximum_age = _parse_optional_int(form.get("maximum_age"))
    instrument.purpose = (form.get("purpose") or "").strip() or None
    instrument.license_status = license_status
    instrument.reference = (form.get("reference") or "").strip() or None
    instrument.notes = (form.get("notes") or "").strip() or None
    instrument.touch()
    return []


# ---------- Catálogo de instrumentos ----------


@assessment_bp.route("/instruments")
@login_required
def instruments_list():
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    population = (request.args.get("population") or "").strip()
    active_only = request.args.get("active") == "1"

    query = Instrument.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Instrument.name.ilike(like),
                Instrument.short_name.ilike(like),
                Instrument.slug.ilike(like),
            )
        )
    if category:
        query = query.filter(Instrument.category == category)
    if population:
        query = query.filter(Instrument.target_population == population)
    if active_only:
        query = query.filter(Instrument.is_active.is_(True))

    page_obj = paginate_query(query.order_by(Instrument.name.asc()))
    instruments = page_obj.items
    ptype = normalize_professional_type(current_user.professional_type)
    scope_by_id: dict[int, str] = {}
    if instruments:
        ids = [inst.id for inst in instruments]
        scopes = InstrumentProfessionalScope.query.filter(
            InstrumentProfessionalScope.instrument_id.in_(ids),
            InstrumentProfessionalScope.professional_type == ptype,
        ).all()
        scope_by_id = {s.instrument_id: s.status for s in scopes}
        for inst in instruments:
            scope_by_id.setdefault(inst.id, "verify")

    return render_template(
        "panel/instruments_list.html",
        instruments=instruments,
        page_obj=page_obj,
        q=q,
        category=category,
        population=population,
        active_only=active_only,
        categories=INSTRUMENT_CATEGORIES,
        populations=POPULATION_CHOICES,
        license_labels=LICENSE_LABELS,
        scope_by_id=scope_by_id,
        scope_status_label=scope_status_label,
        breadcrumbs=[
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {"label": "Instrumentos", "url": None},
        ],
    )


@assessment_bp.route("/instruments/new", methods=["GET", "POST"])
@login_required
def instruments_new():
    if request.method == "POST":
        instrument = Instrument(
            is_active=True,
            license_status="unknown",
            copyright_status="unknown",
            digital_use_status="verify",
        )
        errors = _apply_instrument_form(instrument, request.form)
        if errors:
            for err in errors:
                flash(err, "error")
            return render_template(
                "panel/instrument_form.html",
                form=request.form,
                mode="new",
                categories=INSTRUMENT_CATEGORIES,
                license_statuses=LICENSE_STATUSES,
                populations=POPULATION_CHOICES,
            )
        db.session.add(instrument)
        db.session.flush()
        ensure_scopes_for_instrument(instrument)
        db.session.commit()
        flash("Instrumento criado no catálogo.", "success")
        return redirect(url_for("assessment.instruments_view", instrument_id=instrument.id))
    return render_template(
        "panel/instrument_form.html",
        form={"license_status": "unknown", "category": "Outros"},
        mode="new",
        categories=INSTRUMENT_CATEGORIES,
        license_statuses=LICENSE_STATUSES,
        populations=POPULATION_CHOICES,
    )


@assessment_bp.route("/instruments/<int:instrument_id>")
@login_required
def instruments_view(instrument_id: int):
    instrument = db.session.get(Instrument, instrument_id)
    if instrument is None:
        abort(404)
    scopes = (
        InstrumentProfessionalScope.query.filter_by(instrument_id=instrument.id)
        .order_by(InstrumentProfessionalScope.professional_type.asc())
        .all()
    )
    return render_template(
        "panel/instrument_view.html",
        instrument=instrument,
        license_labels=LICENSE_LABELS,
        scopes=scopes,
        professional_type_label=professional_type_label,
        scope_status_label=scope_status_label,
        copyright_labels=dict(COPYRIGHT_STATUSES),
        digital_labels=dict(DIGITAL_USE_STATUSES),
    )


@assessment_bp.route("/instruments/<int:instrument_id>/edit", methods=["GET", "POST"])
@login_required
def instruments_edit(instrument_id: int):
    instrument = db.session.get(Instrument, instrument_id)
    if instrument is None:
        abort(404)
    if request.method == "POST":
        errors = _apply_instrument_form(instrument, request.form)
        if errors:
            for err in errors:
                flash(err, "error")
        else:
            db.session.commit()
            flash("Instrumento atualizado.", "success")
            return redirect(url_for("assessment.instruments_view", instrument_id=instrument.id))
    return render_template(
        "panel/instrument_form.html",
        form=_instrument_form_from_model(instrument),
        mode="edit",
        instrument=instrument,
        categories=INSTRUMENT_CATEGORIES,
        license_statuses=LICENSE_STATUSES,
        populations=POPULATION_CHOICES,
    )


@assessment_bp.route("/instruments/<int:instrument_id>/toggle", methods=["POST"])
@login_required
def instruments_toggle(instrument_id: int):
    instrument = db.session.get(Instrument, instrument_id)
    if instrument is None:
        abort(404)
    instrument.is_active = not instrument.is_active
    instrument.touch()
    db.session.commit()
    flash(
        "Instrumento ativado." if instrument.is_active else "Instrumento desativado.",
        "success",
    )
    return redirect(url_for("assessment.instruments_list"))


# ---------- Avaliações ----------


@assessment_bp.route("/assessments")
@login_required
def assessments_list():
    status = (request.args.get("status") or "").strip()
    query = Assessment.query.filter_by(professional_id=current_user.id)
    if status:
        query = query.filter(Assessment.status == status)
    page_obj = paginate_query(
        query.order_by(Assessment.assessment_date.desc(), Assessment.id.desc())
    )
    assessments = page_obj.items
    counts: dict[int, int] = {}
    if assessments:
        ids = [a.id for a in assessments]
        rows_count = (
            db.session.query(
                AssessmentInstrument.assessment_id,
                func.count(AssessmentInstrument.id),
            )
            .filter(AssessmentInstrument.assessment_id.in_(ids))
            .group_by(AssessmentInstrument.assessment_id)
            .all()
        )
        counts = {aid: int(cnt) for aid, cnt in rows_count}
    rows = [
        {
            "assessment": assessment,
            "instrument_count": counts.get(assessment.id, 0),
        }
        for assessment in assessments
    ]
    return render_template(
        "panel/assessments_list.html",
        rows=rows,
        page_obj=page_obj,
        status=status,
        status_labels=STATUS_LABELS,
        breadcrumbs=[
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {"label": "Avaliações", "url": None},
        ],
    )


@assessment_bp.route("/patients/<int:patient_id>/assessments")
@login_required
def patient_assessments(patient_id: int):
    return redirect(
        url_for("panel.patient_detail", patient_id=patient_id, tab="assessments")
    )


@assessment_bp.route(
    "/patients/<int:patient_id>/assessments/new", methods=["GET", "POST"]
)
@login_required
def patient_assessment_new(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()
    population = (request.args.get("population") or "").strip()

    query = Instrument.query.filter_by(is_active=True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Instrument.name.ilike(like), Instrument.short_name.ilike(like))
        )
    if category:
        query = query.filter(Instrument.category == category)
    if population:
        query = query.filter(Instrument.target_population == population)
    catalog = query.order_by(Instrument.category.asc(), Instrument.name.asc()).all()

    age = patient.age_years
    catalog_rows = [
        {
            "instrument": inst,
            "age_warning": age_outside_instrument_range(
                age, inst.minimum_age, inst.maximum_age
            ),
        }
        for inst in catalog
    ]

    if request.method == "POST":
        reason = (request.form.get("reason") or "").strip()
        date_raw = (request.form.get("assessment_date") or "").strip()
        selected_ids = request.form.getlist("instrument_ids")
        try:
            assessment_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Data da avaliação inválida.", "error")
            return render_template(
                "panel/patient_assessment_new.html",
                patient=patient,
                catalog_rows=catalog_rows,
                q=q,
                category=category,
                population=population,
                categories=INSTRUMENT_CATEGORIES,
                populations=POPULATION_CHOICES,
                form=request.form,
                selected_ids={int(x) for x in selected_ids if str(x).isdigit()},
            )

        if not reason:
            flash("Motivo da avaliação é obrigatório.", "error")
            return render_template(
                "panel/patient_assessment_new.html",
                patient=patient,
                catalog_rows=catalog_rows,
                q=q,
                category=category,
                population=population,
                categories=INSTRUMENT_CATEGORIES,
                populations=POPULATION_CHOICES,
                form=request.form,
                selected_ids={int(x) for x in selected_ids if str(x).isdigit()},
            )

        ids = [int(x) for x in selected_ids if str(x).isdigit()]
        instruments = (
            Instrument.query.filter(Instrument.id.in_(ids), Instrument.is_active.is_(True)).all()
            if ids
            else []
        )
        if not instruments:
            flash("Selecione pelo menos um instrumento ativo.", "error")
            return render_template(
                "panel/patient_assessment_new.html",
                patient=patient,
                catalog_rows=catalog_rows,
                q=q,
                category=category,
                population=population,
                categories=INSTRUMENT_CATEGORIES,
                populations=POPULATION_CHOICES,
                form=request.form,
                selected_ids=set(ids),
            )

        assessment = Assessment(
            patient_id=patient.id,
            professional_id=current_user.id,
            assessment_date=assessment_date,
            reason=reason,
            assessment_type=(
                request.form.get("assessment_type")
                if request.form.get("assessment_type") in dict(ASSESSMENT_TYPES)
                else "initial"
            ),
            status="draft",
            general_notes=(request.form.get("general_notes") or "").strip() or None,
        )
        db.session.add(assessment)
        db.session.flush()

        now = utcnow()
        for inst in instruments:
            db.session.add(
                AssessmentInstrument(
                    assessment_id=assessment.id,
                    instrument_id=inst.id,
                    instrument_name=inst.name,
                    instrument_short_name=inst.short_name,
                    status="pending",
                    created_at=now,
                    updated_at=now,
                )
            )
        db.session.commit()
        flash("Avaliação criada como rascunho.", "success")
        return redirect(
            url_for(
                "assessment.patient_assessment_edit",
                patient_id=patient.id,
                assessment_id=assessment.id,
            )
        )

    return render_template(
        "panel/patient_assessment_new.html",
        patient=patient,
        catalog_rows=catalog_rows,
        q=q,
        category=category,
        population=population,
        categories=INSTRUMENT_CATEGORIES,
        populations=POPULATION_CHOICES,
            form={"assessment_date": date.today().isoformat()},
        selected_ids=set(),
    )


def _load_assessment_instruments(assessment: Assessment) -> list[AssessmentInstrument]:
    return (
        AssessmentInstrument.query.filter_by(assessment_id=assessment.id)
        .order_by(AssessmentInstrument.id.asc())
        .all()
    )


def _metrics_for(item: AssessmentInstrument) -> list[AssessmentResult]:
    return (
        AssessmentResult.query.filter_by(assessment_instrument_id=item.id)
        .order_by(AssessmentResult.sort_order.asc(), AssessmentResult.id.asc())
        .all()
    )


def _cognitive_context():
    domains = (
        CognitiveDomain.query.filter_by(is_active=True)
        .order_by(CognitiveDomain.sort_order.asc())
        .all()
    )
    skills = (
        CognitiveSkill.query.filter_by(is_active=True)
        .order_by(CognitiveSkill.domain_id.asc(), CognitiveSkill.sort_order.asc())
        .all()
    )
    return domains, skills


def _indicator_map_for_results(result_ids: list[int]) -> dict[int, CognitiveIndicator]:
    if not result_ids:
        return {}
    rows = CognitiveIndicator.query.filter(
        CognitiveIndicator.assessment_result_id.in_(result_ids),
        CognitiveIndicator.professional_id == current_user.id,
    ).all()
    return {r.assessment_result_id: r for r in rows if r.assessment_result_id}


def _save_assessment_instruments(assessment: Assessment, form) -> None:
    items = _load_assessment_instruments(assessment)
    for item in items:
        prefix = f"ai_{item.id}_"
        item.status = (form.get(prefix + "status") or item.status).strip()
        if item.status not in AI_STATUS_LABELS:
            item.status = "pending"
        item.raw_score = _parse_optional_float(form.get(prefix + "raw_score"))
        item.standard_score = _parse_optional_float(form.get(prefix + "standard_score"))
        item.classification = (form.get(prefix + "classification") or "").strip() or None
        item.professional_interpretation = (
            form.get(prefix + "professional_interpretation") or ""
        ).strip() or None
        item.notes = (form.get(prefix + "notes") or "").strip() or None
        if item.status == "completed" and item.completed_at is None:
            item.completed_at = utcnow()
        if item.status == "in_progress" and item.started_at is None:
            item.started_at = utcnow()
        if item.status in ("pending", "skipped"):
            item.completed_at = None
        item.touch()

        # Métricas existentes
        for result in item.results.order_by(AssessmentResult.sort_order.asc()).all():
            rprefix = f"metric_{result.id}_"
            if form.get(rprefix + "delete") == "on":
                remove_indicator_for_result(result.id, current_user.id)
                db.session.delete(result)
                continue
            name = (form.get(rprefix + "metric_name") or "").strip()
            if not name:
                continue
            result.metric_name = name
            result.raw_value = (form.get(rprefix + "raw_value") or "").strip() or None
            result.normalized_value = (
                form.get(rprefix + "normalized_value") or ""
            ).strip() or None
            result.unit = (form.get(rprefix + "unit") or "").strip() or None
            result.interpretation = (
                form.get(rprefix + "interpretation") or ""
            ).strip() or None
            result.source = "professional"
            result.touch()

            if form.get(rprefix + "link_profile") == "on":
                upsert_indicator_from_result(
                    assessment=assessment,
                    item=item,
                    result=result,
                    domain_id=form.get(rprefix + "domain_id", type=int),
                    skill_id=form.get(rprefix + "skill_id", type=int),
                    professional_id=current_user.id,
                )
            else:
                remove_indicator_for_result(result.id, current_user.id)

        # Nova métrica opcional por instrumento
        nprefix = f"new_metric_{item.id}_"
        new_name = (form.get(nprefix + "metric_name") or "").strip()
        if new_name:
            order = item.results.count()
            result = AssessmentResult(
                assessment_instrument_id=item.id,
                metric_name=new_name,
                raw_value=(form.get(nprefix + "raw_value") or "").strip() or None,
                normalized_value=(
                    form.get(nprefix + "normalized_value") or ""
                ).strip()
                or None,
                unit=(form.get(nprefix + "unit") or "").strip() or None,
                interpretation=(
                    form.get(nprefix + "interpretation") or ""
                ).strip()
                or None,
                source="professional",
                sort_order=order,
            )
            db.session.add(result)
            db.session.flush()
            if form.get(nprefix + "link_profile") == "on":
                upsert_indicator_from_result(
                    assessment=assessment,
                    item=item,
                    result=result,
                    domain_id=form.get(nprefix + "domain_id", type=int),
                    skill_id=form.get(nprefix + "skill_id", type=int),
                    professional_id=current_user.id,
                )


@assessment_bp.route(
    "/patients/<int:patient_id>/assessments/<int:assessment_id>",
    methods=["GET"],
)
@login_required
def patient_assessment_view(patient_id: int, assessment_id: int):
    patient = _owned_patient_or_404(patient_id)
    assessment = _owned_assessment_or_404(patient_id, assessment_id)
    items = _load_assessment_instruments(assessment)
    metrics_by_item = {item.id: _metrics_for(item) for item in items}
    all_result_ids = [m.id for ms in metrics_by_item.values() for m in ms]
    indicator_map = _indicator_map_for_results(all_result_ids)
    domains, skills = _cognitive_context()
    item_rows = [
        {
            "item": item,
            "metrics": metrics_by_item[item.id],
            "indicator_map": {
                m.id: indicator_map.get(m.id) for m in metrics_by_item[item.id]
            },
        }
        for item in items
    ]
    return render_template(
        "panel/patient_assessment_view.html",
        patient=patient,
        assessment=assessment,
        item_rows=item_rows,
        status_labels=STATUS_LABELS,
        ai_status_labels=AI_STATUS_LABELS,
        domains=domains,
        skills=skills,
    )


@assessment_bp.route(
    "/patients/<int:patient_id>/assessments/<int:assessment_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def patient_assessment_edit(patient_id: int, assessment_id: int):
    patient = _owned_patient_or_404(patient_id)
    assessment = _owned_assessment_or_404(patient_id, assessment_id)

    def _edit_context():
        items = _load_assessment_instruments(assessment)
        metrics_by_item = {item.id: _metrics_for(item) for item in items}
        all_result_ids = [m.id for ms in metrics_by_item.values() for m in ms]
        indicator_map = _indicator_map_for_results(all_result_ids)
        domains, skills = _cognitive_context()
        return {
            "patient": patient,
            "assessment": assessment,
            "item_rows": [
                {
                    "item": item,
                    "metrics": metrics_by_item[item.id],
                    "indicator_map": {
                        m.id: indicator_map.get(m.id) for m in metrics_by_item[item.id]
                    },
                }
                for item in items
            ],
            "status_labels": STATUS_LABELS,
            "ai_status_labels": AI_STATUS_LABELS,
            "domains": domains,
            "skills": skills,
        }

    if assessment.status == "completed" and request.method == "GET":
        flash(
            "Esta avaliação está concluída. Reabra como rascunho para editar.",
            "warning",
        )

    if request.method == "POST":
        action = request.form.get("action") or "draft"
        if assessment.status == "completed" and action != "reopen":
            flash(
                "Avaliação concluída. Use “Reabrir como rascunho” para editar.",
                "error",
            )
            return redirect(
                url_for(
                    "assessment.patient_assessment_view",
                    patient_id=patient.id,
                    assessment_id=assessment.id,
                )
            )

        if action == "reopen":
            assessment.status = "draft"
            assessment.completed_at = None
            assessment.touch()
            db.session.commit()
            flash("Avaliação reaberta como rascunho.", "success")
            return redirect(
                url_for(
                    "assessment.patient_assessment_edit",
                    patient_id=patient.id,
                    assessment_id=assessment.id,
                )
            )

        reason = (request.form.get("reason") or "").strip()
        date_raw = (request.form.get("assessment_date") or "").strip()
        try:
            assessment_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
        except ValueError:
            flash("Data da avaliação inválida.", "error")
            return render_template(
                "panel/patient_assessment_edit.html", **_edit_context()
            )

        if not reason:
            flash("Motivo da avaliação é obrigatório.", "error")
            return render_template(
                "panel/patient_assessment_edit.html", **_edit_context()
            )

        assessment.reason = reason
        assessment.assessment_date = assessment_date
        atype = request.form.get("assessment_type") or assessment.assessment_type
        if atype in dict(ASSESSMENT_TYPES):
            assessment.assessment_type = atype
        assessment.general_notes = (
            request.form.get("general_notes") or ""
        ).strip() or None
        _save_assessment_instruments(assessment, request.form)
        assessment.touch()

        if action == "complete":
            assessment.status = "completed"
            assessment.completed_at = utcnow()
            db.session.commit()
            flash("Avaliação concluída.", "success")
            return redirect(
                url_for(
                    "assessment.patient_assessment_view",
                    patient_id=patient.id,
                    assessment_id=assessment.id,
                )
            )

        assessment.status = "draft"
        db.session.commit()
        flash("Rascunho guardado.", "success")
        return redirect(
            url_for(
                "assessment.patient_assessment_edit",
                patient_id=patient.id,
                assessment_id=assessment.id,
            )
        )

    return render_template("panel/patient_assessment_edit.html", **_edit_context())
