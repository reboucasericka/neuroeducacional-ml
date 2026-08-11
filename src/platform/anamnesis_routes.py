"""Rotas do módulo de anamneses configuráveis."""

from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from sqlalchemy import func

from src.platform.anamnesis_utils import (
    FIELD_TYPES,
    anamnesis_fill_progress,
    deserialize_response_value,
    display_response_value,
    dump_options,
    group_fields_by_section,
    parse_options,
    responses_map,
    serialize_response_value,
    slugify,
    upsert_responses,
    validate_required_fields,
)
from src.platform.extensions import db
from src.platform.models import (
    AnamnesisField,
    AnamnesisTemplate,
    Patient,
    PatientAnamnesis,
    utcnow,
)
from src.platform.pagination_utils import paginate_query
from src.platform.record_nav import patient_new_record_actions, patient_record_tabs

SEX_CHOICES = {
    "feminino": "Feminino",
    "masculino": "Masculino",
    "outro": "Outro",
    "nao_informado": "Não informado",
}

anamnesis_bp = Blueprint("anamnesis", __name__, url_prefix="/panel")

STATUS_LABELS = {
    "draft": "Rascunho",
    "completed": "Concluída",
    "archived": "Arquivada",
}


def _owned_patient_or_404(patient_id: int) -> Patient:
    patient = Patient.query.filter_by(
        id=patient_id, professional_id=current_user.id
    ).first()
    if patient is None:
        abort(404)
    return patient


def _owned_anamnesis_or_404(patient_id: int, anamnesis_id: int) -> PatientAnamnesis:
    anamnesis = PatientAnamnesis.query.filter_by(
        id=anamnesis_id,
        patient_id=patient_id,
        professional_id=current_user.id,
    ).first()
    if anamnesis is None:
        abort(404)
    return anamnesis


def _active_fields(template_id: int) -> list[AnamnesisField]:
    return (
        AnamnesisField.query.filter_by(template_id=template_id, is_active=True)
        .order_by(AnamnesisField.sort_order.asc(), AnamnesisField.id.asc())
        .all()
    )


# ---------- Catálogo de templates ----------


@anamnesis_bp.route("/anamneses")
@login_required
def templates_list():
    query = AnamnesisTemplate.query.order_by(AnamnesisTemplate.name.asc())
    page_obj = paginate_query(query)
    templates = page_obj.items
    counts: dict[int, int] = {}
    if templates:
        ids = [t.id for t in templates]
        rows_count = (
            db.session.query(AnamnesisField.template_id, func.count(AnamnesisField.id))
            .filter(
                AnamnesisField.template_id.in_(ids),
                AnamnesisField.is_active.is_(True),
            )
            .group_by(AnamnesisField.template_id)
            .all()
        )
        counts = {tid: int(cnt) for tid, cnt in rows_count}
    rows = [
        {"template": template, "field_count": counts.get(template.id, 0)}
        for template in templates
    ]
    return render_template(
        "panel/anamnesis_templates_list.html",
        rows=rows,
        page_obj=page_obj,
        breadcrumbs=[
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {"label": "Anamneses", "url": None},
        ],
    )


@anamnesis_bp.route("/anamneses/new", methods=["GET", "POST"])
@login_required
def templates_new():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        slug = slugify(request.form.get("slug") or name)
        if not name:
            flash("Nome é obrigatório.", "error")
            return render_template("panel/anamnesis_template_form.html", form=request.form, mode="new")
        if AnamnesisTemplate.query.filter_by(slug=slug).first():
            flash("Já existe um modelo com este slug.", "error")
            return render_template("panel/anamnesis_template_form.html", form=request.form, mode="new")
        template = AnamnesisTemplate(
            name=name,
            slug=slug,
            category=(request.form.get("category") or "geral").strip(),
            target_population=(request.form.get("target_population") or "").strip() or None,
            description=(request.form.get("description") or "").strip() or None,
            is_active=True,
        )
        db.session.add(template)
        db.session.commit()
        flash("Modelo criado. Adicione campos à estrutura.", "success")
        return redirect(url_for("anamnesis.template_structure", template_id=template.id))
    return render_template("panel/anamnesis_template_form.html", form={}, mode="new")


@anamnesis_bp.route("/anamneses/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def templates_edit(template_id: int):
    template = db.session.get(AnamnesisTemplate, template_id)
    if template is None:
        abort(404)
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        slug = slugify(request.form.get("slug") or name)
        conflict = AnamnesisTemplate.query.filter(
            AnamnesisTemplate.slug == slug, AnamnesisTemplate.id != template.id
        ).first()
        if not name:
            flash("Nome é obrigatório.", "error")
        elif conflict:
            flash("Slug já utilizado por outro modelo.", "error")
        else:
            template.name = name
            template.slug = slug
            template.category = (request.form.get("category") or "geral").strip()
            template.target_population = (
                request.form.get("target_population") or ""
            ).strip() or None
            template.description = (request.form.get("description") or "").strip() or None
            template.touch()
            db.session.commit()
            flash("Modelo atualizado.", "success")
            return redirect(url_for("anamnesis.templates_list"))
    form = {
        "name": template.name,
        "slug": template.slug,
        "category": template.category,
        "target_population": template.target_population or "",
        "description": template.description or "",
    }
    return render_template(
        "panel/anamnesis_template_form.html", form=form, mode="edit", template=template
    )


@anamnesis_bp.route("/anamneses/<int:template_id>/toggle", methods=["POST"])
@login_required
def templates_toggle(template_id: int):
    template = db.session.get(AnamnesisTemplate, template_id)
    if template is None:
        abort(404)
    template.is_active = not template.is_active
    template.touch()
    db.session.commit()
    flash(
        "Modelo ativado." if template.is_active else "Modelo desativado.",
        "success",
    )
    return redirect(url_for("anamnesis.templates_list"))


@anamnesis_bp.route("/anamneses/<int:template_id>/structure", methods=["GET", "POST"])
@login_required
def template_structure(template_id: int):
    template = db.session.get(AnamnesisTemplate, template_id)
    if template is None:
        abort(404)

    if request.method == "POST":
        label = (request.form.get("label") or "").strip()
        section = (request.form.get("section") or "Geral").strip() or "Geral"
        field_type = request.form.get("field_type") or "text"
        if field_type not in FIELD_TYPES:
            flash("Tipo de campo inválido.", "error")
        elif not label:
            flash("Etiqueta do campo é obrigatória.", "error")
        else:
            options_raw = (request.form.get("options") or "").strip()
            options = [p.strip() for p in options_raw.split("|") if p.strip()]
            order = template.fields.count() + 1
            db.session.add(
                AnamnesisField(
                    template_id=template.id,
                    section=section,
                    label=label,
                    help_text=(request.form.get("help_text") or "").strip() or None,
                    field_type=field_type,
                    options_json=dump_options(options) if options else None,
                    placeholder=(request.form.get("placeholder") or "").strip() or None,
                    is_required=request.form.get("is_required") == "on",
                    sort_order=int(request.form.get("sort_order") or order),
                    is_active=True,
                )
            )
            template.touch()
            db.session.commit()
            flash("Campo adicionado.", "success")
            return redirect(url_for("anamnesis.template_structure", template_id=template.id))

    fields = (
        AnamnesisField.query.filter_by(template_id=template.id)
        .order_by(AnamnesisField.sort_order.asc(), AnamnesisField.id.asc())
        .all()
    )
    grouped = group_fields_by_section([f for f in fields if f.is_active])
    return render_template(
        "panel/anamnesis_template_structure.html",
        template=template,
        fields=fields,
        grouped=grouped,
        field_types=FIELD_TYPES,
        parse_options=parse_options,
    )


@anamnesis_bp.route(
    "/anamneses/<int:template_id>/fields/<int:field_id>/toggle", methods=["POST"]
)
@login_required
def field_toggle(template_id: int, field_id: int):
    field = AnamnesisField.query.filter_by(id=field_id, template_id=template_id).first()
    if field is None:
        abort(404)
    field.is_active = not field.is_active
    field.template.touch()
    db.session.commit()
    flash("Campo atualizado.", "success")
    return redirect(url_for("anamnesis.template_structure", template_id=template_id))


# ---------- Aplicação ao paciente ----------


@anamnesis_bp.route("/patients/<int:patient_id>/anamneses")
@login_required
def patient_anamneses(patient_id: int):
    return redirect(
        url_for("panel.patient_detail", patient_id=patient_id, tab="anamnesis")
    )


@anamnesis_bp.route("/patients/<int:patient_id>/anamneses/new", methods=["GET", "POST"])
@login_required
def patient_anamnesis_new(patient_id: int):
    patient = _owned_patient_or_404(patient_id)
    templates = (
        AnamnesisTemplate.query.filter_by(is_active=True)
        .order_by(AnamnesisTemplate.name.asc())
        .all()
    )
    if request.method == "POST":
        template_id = request.form.get("template_id", type=int)
        template = AnamnesisTemplate.query.filter_by(
            id=template_id, is_active=True
        ).first()
        if template is None:
            flash("Modelo inválido ou inativo.", "error")
            return render_template(
                "panel/patient_anamnesis_new.html",
                patient=patient,
                templates=templates,
            )
        anamnesis = PatientAnamnesis(
            patient_id=patient.id,
            template_id=template.id,
            professional_id=current_user.id,
            status="draft",
            notes=(request.form.get("notes") or "").strip() or None,
        )
        db.session.add(anamnesis)
        db.session.commit()
        flash("Anamnese iniciada como rascunho.", "success")
        return redirect(
            url_for(
                "anamnesis.patient_anamnesis_edit",
                patient_id=patient.id,
                anamnesis_id=anamnesis.id,
            )
        )
    return render_template(
        "panel/patient_anamnesis_new.html", patient=patient, templates=templates
    )


def _anamnesis_edit_context(
    patient: Patient,
    anamnesis: PatientAnamnesis,
    *,
    grouped,
    values,
    errors,
    fields,
):
    return {
        "patient": patient,
        "anamnesis": anamnesis,
        "grouped": grouped,
        "values": values,
        "errors": errors,
        "fill_progress": anamnesis_fill_progress(fields, values),
        "status_labels": STATUS_LABELS,
        "deserialize_response_value": deserialize_response_value,
        "parse_options": parse_options,
        "sex_choices": SEX_CHOICES,
        "record_tabs": patient_record_tabs(patient.id, active="anamnesis"),
        "new_record_actions": patient_new_record_actions(patient.id),
        "breadcrumbs": [
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {
                "label": patient.name,
                "url": url_for("panel.patient_detail", patient_id=patient.id, tab="anamnesis"),
            },
            {"label": anamnesis.template.name, "url": None},
        ],
    }


@anamnesis_bp.route(
    "/patients/<int:patient_id>/anamneses/<int:anamnesis_id>",
    methods=["GET"],
)
@login_required
def patient_anamnesis_view(patient_id: int, anamnesis_id: int):
    patient = _owned_patient_or_404(patient_id)
    anamnesis = _owned_anamnesis_or_404(patient_id, anamnesis_id)
    fields = _active_fields(anamnesis.template_id)
    values = responses_map(anamnesis.id)
    grouped = group_fields_by_section(fields)
    return render_template(
        "panel/patient_anamnesis_view.html",
        patient=patient,
        anamnesis=anamnesis,
        grouped=grouped,
        values=values,
        status_labels=STATUS_LABELS,
        display_response_value=display_response_value,
        deserialize_response_value=deserialize_response_value,
        sex_choices=SEX_CHOICES,
        record_tabs=patient_record_tabs(patient.id, active="anamnesis"),
        new_record_actions=patient_new_record_actions(patient.id),
        breadcrumbs=[
            {"label": "Dashboard", "url": url_for("panel.dashboard")},
            {
                "label": patient.name,
                "url": url_for("panel.patient_detail", patient_id=patient.id, tab="anamnesis"),
            },
            {"label": anamnesis.template.name, "url": None},
        ],
    )


@anamnesis_bp.route(
    "/patients/<int:patient_id>/anamneses/<int:anamnesis_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def patient_anamnesis_edit(patient_id: int, anamnesis_id: int):
    patient = _owned_patient_or_404(patient_id)
    anamnesis = _owned_anamnesis_or_404(patient_id, anamnesis_id)
    fields = _active_fields(anamnesis.template_id)
    grouped = group_fields_by_section(fields)

    if anamnesis.status == "completed" and request.method == "GET":
        flash(
            "Esta anamnese está concluída. Reabra como rascunho para editar.",
            "warning",
        )

    if request.method == "POST":
        action = request.form.get("action") or "draft"
        if anamnesis.status == "completed" and action != "reopen":
            flash("Anamnese concluída. Use “Reabrir como rascunho” para editar.", "error")
            return redirect(
                url_for(
                    "anamnesis.patient_anamnesis_view",
                    patient_id=patient.id,
                    anamnesis_id=anamnesis.id,
                )
            )

        if action == "reopen":
            anamnesis.status = "draft"
            anamnesis.completed_at = None
            anamnesis.touch()
            db.session.commit()
            flash("Anamnese reaberta como rascunho.", "success")
            return redirect(
                url_for(
                    "anamnesis.patient_anamnesis_edit",
                    patient_id=patient.id,
                    anamnesis_id=anamnesis.id,
                )
            )

        errors = {}
        if action == "complete":
            errors = validate_required_fields(fields, request.form)
            if errors:
                flash(f"Revise {len(errors)} campos obrigatórios.", "error")
                values = {
                    field.id: deserialize_response_value(
                        field, serialize_response_value(field, request.form)
                    )
                    for field in fields
                }
                return render_template(
                    "panel/patient_anamnesis_edit.html",
                    **_anamnesis_edit_context(
                        patient,
                        anamnesis,
                        grouped=grouped,
                        values=values,
                        errors=errors,
                        fields=fields,
                    ),
                )

        upsert_responses(anamnesis.id, fields, request.form)
        anamnesis.notes = (request.form.get("notes") or "").strip() or None
        anamnesis.touch()
        if action == "complete":
            anamnesis.status = "completed"
            anamnesis.completed_at = utcnow()
            flash("Anamnese concluída.", "success")
            db.session.commit()
            return redirect(
                url_for(
                    "anamnesis.patient_anamnesis_view",
                    patient_id=patient.id,
                    anamnesis_id=anamnesis.id,
                )
            )

        anamnesis.status = "draft"
        db.session.commit()
        flash("Rascunho guardado.", "success")
        return redirect(
            url_for(
                "anamnesis.patient_anamnesis_edit",
                patient_id=patient.id,
                anamnesis_id=anamnesis.id,
            )
        )

    values = {
        field.id: deserialize_response_value(field, responses_map(anamnesis.id).get(field.id))
        for field in fields
    }
    return render_template(
        "panel/patient_anamnesis_edit.html",
        **_anamnesis_edit_context(
            patient,
            anamnesis,
            grouped=grouped,
            values=values,
            errors={},
            fields=fields,
        ),
    )