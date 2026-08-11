"""Helpers para criar CognitiveIndicator a partir de resultados de avaliação."""

from __future__ import annotations

from src.platform.extensions import db
from src.platform.models import (
    Assessment,
    AssessmentInstrument,
    AssessmentResult,
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    utcnow,
)


def _parse_numeric(raw: str | None) -> float | None:
    value = (raw or "").strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def upsert_indicator_from_result(
    *,
    assessment: Assessment,
    item: AssessmentInstrument,
    result: AssessmentResult,
    domain_id: int | None,
    skill_id: int | None,
    professional_id: int,
) -> CognitiveIndicator | None:
    """Cria ou atualiza indicador ligado a um AssessmentResult (sem duplicar)."""
    if not domain_id:
        return None
    domain = db.session.get(CognitiveDomain, domain_id)
    if domain is None:
        return None
    skill = None
    if skill_id:
        skill = CognitiveSkill.query.filter_by(
            id=skill_id, domain_id=domain.id
        ).first()

    existing = CognitiveIndicator.query.filter_by(
        assessment_result_id=result.id,
        professional_id=professional_id,
    ).first()

    label = result.metric_name
    value_numeric = _parse_numeric(result.raw_value)
    if value_numeric is None:
        value_numeric = _parse_numeric(result.normalized_value)
    value_text = result.raw_value or result.normalized_value
    recorded = utcnow()
    if assessment.assessment_date:
        recorded = utcnow().replace(
            year=assessment.assessment_date.year,
            month=assessment.assessment_date.month,
            day=assessment.assessment_date.day,
        )

    if existing:
        existing.domain_id = domain.id
        existing.skill_id = skill.id if skill else None
        existing.label = label
        existing.value_numeric = value_numeric
        existing.value_text = value_text
        existing.unit = result.unit
        existing.interpretation = result.interpretation or item.professional_interpretation
        existing.assessment_id = assessment.id
        existing.assessment_instrument_id = item.id
        existing.recorded_at = recorded
        existing.touch()
        return existing

    indicator = CognitiveIndicator(
        patient_id=assessment.patient_id,
        professional_id=professional_id,
        assessment_id=assessment.id,
        assessment_instrument_id=item.id,
        assessment_result_id=result.id,
        domain_id=domain.id,
        skill_id=skill.id if skill else None,
        recorded_at=recorded,
        label=label,
        value_numeric=value_numeric,
        value_text=value_text,
        unit=result.unit,
        interpretation=result.interpretation or item.professional_interpretation,
        source_type="assessment_result",
    )
    db.session.add(indicator)
    return indicator


def remove_indicator_for_result(result_id: int, professional_id: int) -> None:
    CognitiveIndicator.query.filter_by(
        assessment_result_id=result_id,
        professional_id=professional_id,
    ).delete()
