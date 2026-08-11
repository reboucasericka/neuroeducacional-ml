"""
Utilitários de anamnese: opções, respostas e validação.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any

from src.platform.extensions import db
from src.platform.models import AnamnesisField, PatientAnamnesisResponse


FIELD_TYPES = (
    "text",
    "textarea",
    "number",
    "date",
    "select",
    "radio",
    "checkbox",
    "boolean",
)


def slugify(text: str) -> str:
    raw = (text or "").strip().lower()
    mapping = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçñ",
        "aaaaaeeeeiiiiooooouuuucn",
    )
    raw = raw.translate(mapping)
    out = []
    prev_dash = False
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif ch in " _-/":
            if not prev_dash and out:
                out.append("-")
                prev_dash = True
    return "".join(out).strip("-") or "template"


def parse_options(options_json: str | None) -> list[str]:
    if not options_json:
        return []
    try:
        data = json.loads(options_json)
    except json.JSONDecodeError:
        return [part.strip() for part in options_json.split(",") if part.strip()]
    if isinstance(data, list):
        return [str(item) for item in data]
    return []


def dump_options(options: list[str] | None) -> str | None:
    if not options:
        return None
    return json.dumps(options, ensure_ascii=False)


def serialize_response_value(field: AnamnesisField, form_data) -> str | None:
    key = f"field_{field.id}"
    if field.field_type == "checkbox":
        values = form_data.getlist(key)
        return json.dumps(values, ensure_ascii=False) if values else None
    if field.field_type == "boolean":
        return "true" if form_data.get(key) in ("on", "true", "1", "yes") else "false"
    value = form_data.get(key)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def deserialize_response_value(field: AnamnesisField, raw: str | None) -> Any:
    if raw is None or raw == "":
        if field.field_type == "checkbox":
            return []
        if field.field_type == "boolean":
            return False
        return ""
    if field.field_type == "checkbox":
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else [str(data)]
        except json.JSONDecodeError:
            return [raw]
    if field.field_type == "boolean":
        return str(raw).lower() in ("true", "1", "yes", "on")
    return raw


def display_response_value(field: AnamnesisField, raw: str | None) -> str:
    value = deserialize_response_value(field, raw)
    if field.field_type == "checkbox":
        return ", ".join(value) if value else "—"
    if field.field_type == "boolean":
        return "Sim" if value else "Não"
    return str(value) if value not in (None, "") else "—"


def responses_map(anamnesis_id: int) -> dict[int, str | None]:
    rows = PatientAnamnesisResponse.query.filter_by(
        patient_anamnesis_id=anamnesis_id
    ).all()
    return {row.field_id: row.value for row in rows}


def upsert_responses(anamnesis_id: int, fields: list[AnamnesisField], form_data) -> None:
    existing = {
        row.field_id: row
        for row in PatientAnamnesisResponse.query.filter_by(
            patient_anamnesis_id=anamnesis_id
        ).all()
    }
    for field in fields:
        if not field.is_active:
            continue
        value = serialize_response_value(field, form_data)
        row = existing.get(field.id)
        if row is None:
            row = PatientAnamnesisResponse(
                patient_anamnesis_id=anamnesis_id,
                field_id=field.id,
                value=value,
            )
            db.session.add(row)
        else:
            row.value = value
            row.touch()


def validate_required_fields(
    fields: list[AnamnesisField], form_data
) -> dict[int, str]:
    errors: dict[int, str] = {}
    for field in fields:
        if not field.is_active or not field.is_required:
            continue
        value = serialize_response_value(field, form_data)
        empty = value is None or value == "" or value == "[]" or value == "false"
        # boolean required means must be explicitly checked? Treat false as filled.
        if field.field_type == "boolean":
            continue
        if empty:
            errors[field.id] = "Campo obrigatório."
    return errors


def group_fields_by_section(fields: list[AnamnesisField]) -> OrderedDict[str, list]:
    grouped: OrderedDict[str, list] = OrderedDict()
    for field in sorted(fields, key=lambda f: (f.sort_order, f.id)):
        grouped.setdefault(field.section or "Geral", []).append(field)
    return grouped
