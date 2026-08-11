"""Painel de evidências (somente leitura) para apoio à devolutiva."""

from __future__ import annotations

from src.platform.models import (
    Assessment,
    AssessmentInstrument,
    AssessmentPlan,
    AssessmentResult,
    CognitiveIndicator,
    PatientAnamnesis,
    ProfessionalSession,
    Referral,
)


def collect_evidence(patient_id: int, professional_id: int) -> dict:
    """Reúne dados existentes — não gera texto de devolutiva nem diagnóstico."""
    anamnesis = (
        PatientAnamnesis.query.filter_by(
            patient_id=patient_id, professional_id=professional_id
        )
        .order_by(PatientAnamnesis.updated_at.desc())
        .first()
    )
    plans = (
        AssessmentPlan.query.filter_by(
            patient_id=patient_id, professional_id=professional_id
        )
        .order_by(AssessmentPlan.updated_at.desc())
        .limit(5)
        .all()
    )
    sessions = (
        ProfessionalSession.query.filter_by(
            patient_id=patient_id, professional_id=professional_id
        )
        .order_by(ProfessionalSession.session_date.desc())
        .limit(12)
        .all()
    )
    assessments = (
        Assessment.query.filter_by(
            patient_id=patient_id, professional_id=professional_id
        )
        .order_by(Assessment.assessment_date.desc())
        .limit(8)
        .all()
    )
    instruments: list[str] = []
    results: list[dict] = []
    for a in assessments:
        for ai in a.instruments.order_by(AssessmentInstrument.id.asc()).all():
            name = ai.display_short_name or ai.display_name
            if name and name not in instruments:
                instruments.append(name)
            for r in (
                AssessmentResult.query.filter_by(assessment_instrument_id=ai.id)
                .order_by(AssessmentResult.sort_order.asc())
                .all()
            ):
                results.append(
                    {
                        "instrument": name,
                        "label": r.metric_name,
                        "value": r.raw_value or r.normalized_value or "—",
                    }
                )

    indicators = (
        CognitiveIndicator.query.filter_by(
            patient_id=patient_id, professional_id=professional_id
        )
        .order_by(CognitiveIndicator.recorded_at.desc())
        .limit(20)
        .all()
    )
    referrals = (
        Referral.query.filter_by(
            patient_id=patient_id, professional_id=professional_id
        )
        .order_by(Referral.referral_date.desc())
        .limit(10)
        .all()
    )
    return {
        "anamnesis": anamnesis,
        "plans": plans,
        "sessions": sessions,
        "assessments": assessments,
        "instruments": instruments,
        "results": results[:40],
        "indicators": indicators,
        "referrals": referrals,
    }
