"""Rotas do Perfil Cognitivo (rastreável e longitudinal)."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src.platform.cognitive_timeline import (
    build_patient_timeline,
    domain_cards_for_patient,
    indicator_source_label,
    skill_history,
)
from src.platform.extensions import db
from src.platform.models import (
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    Instrument,
    InstrumentSkillMapping,
    Patient,
    utcnow,
)

cognitive_bp = Blueprint("cognitive", __name__, url_prefix="/panel")

SEX_LABELS = {
    "feminino": "Feminino",
    "masculino": "Masculino",
    "outro": "Outro",
    "nao_informado": "Não informado",
}


def _owned_patient_or_404(patient_id: int) -> Patient:
    patient = Patient.query.filter_by(
        id=patient_id, professional_id=current_user.id
    ).first()
    if patient is None:
        abort(404)
    return patient


def _owned_indicator_or_404(patient_id: int, indicator_id: int) -> CognitiveIndicator:
    indicator = CognitiveIndicator.query.filter_by(
        id=indicator_id,
        patient_id=patient_id,
        professional_id=current_user.id,
    ).first()
    if indicator is None:
        abort(404)
    return indicator


@cognitive_bp.route("/patients/<int:patient_id>/cognitive-profile")
@login_required
def cognitive_profile(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    domain_filter = request.args.get("domain_id", type=int)
    instrument_filter = request.args.get("instrument_id", type=int)
    period = request.args.get("period") or "all"
    months = None
    if period == "12m":
        months = 12
    elif period == "6m":
        months = 6
    elif period == "3m":
        months = 3

    cards = domain_cards_for_patient(
        patient.id,
        current_user.id,
        domain_id=domain_filter,
        instrument_id=instrument_filter,
        months=months,
    )
    timeline = build_patient_timeline(patient, current_user.id, months=months)
    domains = (
        CognitiveDomain.query.filter_by(is_active=True)
        .order_by(CognitiveDomain.sort_order.asc())
        .all()
    )
    # Instrumentos já usados em indicadores deste paciente
    indicators = CognitiveIndicator.query.filter_by(
        patient_id=patient.id, professional_id=current_user.id
    ).all()
    instrument_options = {}
    for ind in indicators:
        if ind.assessment_instrument and ind.assessment_instrument.instrument_id:
            inst = ind.assessment_instrument.instrument
            if inst:
                instrument_options[inst.id] = inst.short_name or inst.name

    return render_template(
        "panel/cognitive_profile.html",
        patient=patient,
        cards=cards,
        timeline=timeline,
        domains=domains,
        instrument_options=instrument_options,
        domain_filter=domain_filter,
        instrument_filter=instrument_filter,
        period=period,
        sex_labels=SEX_LABELS,
        source_label=indicator_source_label,
    )


@cognitive_bp.route(
    "/patients/<int:patient_id>/cognitive-profile/domains/<int:domain_id>"
)
@login_required
def cognitive_domain_detail(patient_id: int, domain_id: int):
    patient = _owned_patient_or_404(patient_id)
    domain = db.session.get(CognitiveDomain, domain_id)
    if domain is None or not domain.is_active:
        abort(404)
    rows = skill_history(patient.id, current_user.id, domain.id)
    return render_template(
        "panel/cognitive_domain_detail.html",
        patient=patient,
        domain=domain,
        rows=rows,
        sex_labels=SEX_LABELS,
        source_label=indicator_source_label,
    )


@cognitive_bp.route(
    "/patients/<int:patient_id>/cognitive-indicators/new", methods=["GET", "POST"]
)
@login_required
def cognitive_indicator_new(patient_id: int):
    """Entrada manual / observação profissional (não anamnese automática)."""
    patient = _owned_patient_or_404(patient_id)
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
    if request.method == "POST":
        domain_id = request.form.get("domain_id", type=int)
        skill_id = request.form.get("skill_id", type=int)
        label = (request.form.get("label") or "").strip()
        source_type = request.form.get("source_type") or "manual_entry"
        if source_type not in ("manual_entry", "professional_observation"):
            source_type = "manual_entry"
        domain = db.session.get(CognitiveDomain, domain_id) if domain_id else None
        if domain is None or not label:
            flash("Domínio e etiqueta são obrigatórios.", "error")
        else:
            skill = None
            if skill_id:
                skill = CognitiveSkill.query.filter_by(
                    id=skill_id, domain_id=domain.id
                ).first()
            value_raw = (request.form.get("value_numeric") or "").strip().replace(",", ".")
            value_numeric = None
            if value_raw:
                try:
                    value_numeric = float(value_raw)
                except ValueError:
                    flash("Valor numérico inválido.", "error")
                    return render_template(
                        "panel/cognitive_indicator_form.html",
                        patient=patient,
                        domains=domains,
                        skills=skills,
                        form=request.form,
                    )
            db.session.add(
                CognitiveIndicator(
                    patient_id=patient.id,
                    professional_id=current_user.id,
                    domain_id=domain.id,
                    skill_id=skill.id if skill else None,
                    recorded_at=utcnow(),
                    label=label,
                    value_numeric=value_numeric,
                    value_text=(request.form.get("value_text") or "").strip() or None,
                    unit=(request.form.get("unit") or "").strip() or None,
                    interpretation=(request.form.get("interpretation") or "").strip()
                    or None,
                    source_type=source_type,
                )
            )
            db.session.commit()
            flash("Indicador adicionado ao perfil cognitivo.", "success")
            return redirect(
                url_for("cognitive.cognitive_profile", patient_id=patient.id)
            )
    return render_template(
        "panel/cognitive_indicator_form.html",
        patient=patient,
        domains=domains,
        skills=skills,
        form={},
    )


@cognitive_bp.route("/instrument-mappings", methods=["GET", "POST"])
@login_required
def instrument_mappings():
    """Catálogo de mappings instrumento → domínio/habilidade."""
    if request.method == "POST":
        action = request.form.get("action") or "create"
        if action == "toggle":
            mid = request.form.get("mapping_id", type=int)
            mapping = db.session.get(InstrumentSkillMapping, mid) if mid else None
            if mapping is None:
                abort(404)
            mapping.is_active = not mapping.is_active
            db.session.commit()
            flash("Mapping atualizado.", "success")
            return redirect(url_for("cognitive.instrument_mappings"))

        instrument_id = request.form.get("instrument_id", type=int)
        domain_id = request.form.get("domain_id", type=int)
        skill_id = request.form.get("skill_id", type=int)
        instrument = db.session.get(Instrument, instrument_id) if instrument_id else None
        domain = db.session.get(CognitiveDomain, domain_id) if domain_id else None
        if instrument is None or domain is None:
            flash("Instrumento e domínio são obrigatórios.", "error")
        else:
            skill = None
            if skill_id:
                skill = CognitiveSkill.query.filter_by(
                    id=skill_id, domain_id=domain.id
                ).first()
            db.session.add(
                InstrumentSkillMapping(
                    instrument_id=instrument.id,
                    domain_id=domain.id,
                    skill_id=skill.id if skill else None,
                    notes=(request.form.get("notes") or "").strip() or None,
                    is_active=True,
                )
            )
            db.session.commit()
            flash("Mapping criado.", "success")
            return redirect(url_for("cognitive.instrument_mappings"))

    mappings = (
        InstrumentSkillMapping.query.order_by(InstrumentSkillMapping.id.desc()).all()
    )
    instruments = Instrument.query.order_by(Instrument.name.asc()).all()
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
    return render_template(
        "panel/instrument_mappings.html",
        mappings=mappings,
        instruments=instruments,
        domains=domains,
        skills=skills,
    )
