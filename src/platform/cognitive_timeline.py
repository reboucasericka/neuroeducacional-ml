"""
Serviços do Perfil Cognitivo: timeline longitudinal e agregações qualitativas.

Não calcula scores agregados nem normaliza escalas incompatíveis.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from src.platform.models import (
    Assessment,
    AssessmentInstrument,
    AssessmentPlan,
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    FeedbackReport,
    InterventionPlan,
    Patient,
    PatientAnamnesis,
    PatientHistoryEntry,
    ProfessionalSession,
    ProgressNote,
    Referral,
    SchoolContact,
)


@dataclass
class TimelineEvent:
    when: datetime
    kind: str
    title: str
    detail: str
    url: str | None = None
    meta: dict[str, Any] | None = None


def build_patient_timeline(
    patient: Patient,
    professional_id: int,
    *,
    months: int | None = None,
) -> list[TimelineEvent]:
    """Combina anamneses, avaliações, indicadores e histórico (eventos, não scores)."""
    events: list[TimelineEvent] = []
    cutoff = None
    if months:
        cutoff = datetime.utcnow() - timedelta(days=30 * months)

    for a in PatientAnamnesis.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = a.started_at or a.created_at
        if when and cutoff and when.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
            continue
        if when is None:
            continue
        events.append(
            TimelineEvent(
                when=when.replace(tzinfo=None) if when.tzinfo else when,
                kind="anamnesis",
                title=a.template.name if a.template else "Anamnese",
                detail=f"Estado: {a.status}",
                url=f"/panel/patients/{patient.id}/anamneses/{a.id}",
            )
        )

    for assessment in Assessment.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = datetime.combine(assessment.assessment_date, datetime.min.time())
        if cutoff and when < cutoff.replace(tzinfo=None):
            continue
        instruments = (
            AssessmentInstrument.query.filter_by(assessment_id=assessment.id)
            .order_by(AssessmentInstrument.id.asc())
            .all()
        )
        names = ", ".join(i.display_short_name or i.display_name for i in instruments) or "—"
        events.append(
            TimelineEvent(
                when=when,
                kind="assessment",
                title=assessment.reason or "Avaliação",
                detail=f"{len(instruments)} instrumento(s): {names}",
                url=f"/panel/patients/{patient.id}/assessments/{assessment.id}",
            )
        )

    for plan in AssessmentPlan.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = plan.created_at or plan.updated_at
        if when is None:
            continue
        when_naive = when.replace(tzinfo=None) if when.tzinfo else when
        if cutoff and when_naive < cutoff.replace(tzinfo=None):
            continue
        events.append(
            TimelineEvent(
                when=when_naive,
                kind="plan",
                title=plan.title or "Plano de avaliação",
                detail=f"Estado: {plan.status}",
                url=f"/panel/patients/{patient.id}/assessment-plans/{plan.id}",
            )
        )

    for session in ProfessionalSession.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = datetime.combine(session.session_date, datetime.min.time())
        if cutoff and when < cutoff.replace(tzinfo=None):
            continue
        events.append(
            TimelineEvent(
                when=when,
                kind="session",
                title=f"Sessão ({session.session_type})",
                detail=(session.objective or session.summary or session.status)[:160],
                url=f"/panel/patients/{patient.id}/sessions/{session.id}",
            )
        )

    for ref in Referral.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = datetime.combine(ref.referral_date, datetime.min.time())
        if cutoff and when < cutoff.replace(tzinfo=None):
            continue
        events.append(
            TimelineEvent(
                when=when,
                kind="referral",
                title=f"Encaminhamento: {ref.specialty}",
                detail=f"Estado: {ref.status}",
                url=f"/panel/patients/{patient.id}/referrals",
            )
        )

    for sc in SchoolContact.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = datetime.combine(sc.contact_date, datetime.min.time())
        if cutoff and when < cutoff.replace(tzinfo=None):
            continue
        events.append(
            TimelineEvent(
                when=when,
                kind="school",
                title="Contacto escolar",
                detail=sc.school_name or sc.purpose or "—",
                url=f"/panel/patients/{patient.id}/school-contacts",
            )
        )

    for ind in CognitiveIndicator.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = ind.recorded_at
        if when is None:
            continue
        when_naive = when.replace(tzinfo=None) if when.tzinfo else when
        if cutoff and when_naive < cutoff.replace(tzinfo=None):
            continue
        domain_name = ind.domain.name if ind.domain else "Domínio"
        skill_name = ind.skill.name if ind.skill else ""
        events.append(
            TimelineEvent(
                when=when_naive,
                kind="indicator",
                title=f"Indicador: {ind.label}",
                detail=f"{domain_name}" + (f" · {skill_name}" if skill_name else ""),
                url=f"/panel/patients/{patient.id}/cognitive-profile",
            )
        )

    for h in PatientHistoryEntry.query.filter_by(patient_id=patient.id).all():
        when = h.recorded_at
        if when is None:
            continue
        when_naive = when.replace(tzinfo=None) if when.tzinfo else when
        if cutoff and when_naive < cutoff.replace(tzinfo=None):
            continue
        if h.professional_id and h.professional_id != professional_id:
            continue
        events.append(
            TimelineEvent(
                when=when_naive,
                kind="history",
                title=h.title,
                detail=h.category or "histórico",
                url=f"/panel/patients/{patient.id}?tab=history",
            )
        )

    for fb in FeedbackReport.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = datetime.combine(fb.feedback_date, datetime.min.time())
        if fb.completed_at:
            when = fb.completed_at.replace(tzinfo=None) if fb.completed_at.tzinfo else fb.completed_at
        if cutoff and when < cutoff.replace(tzinfo=None):
            continue
        events.append(
            TimelineEvent(
                when=when,
                kind="feedback",
                title=f"Devolutiva: {fb.title}",
                detail=fb.status,
                url=f"/panel/patients/{patient.id}/feedbacks/{fb.id}",
            )
        )

    for ip in InterventionPlan.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = ip.created_at.replace(tzinfo=None) if ip.created_at and ip.created_at.tzinfo else (ip.created_at or datetime.min)
        if cutoff and when < cutoff.replace(tzinfo=None):
            continue
        events.append(
            TimelineEvent(
                when=when,
                kind="intervention_plan",
                title=f"Plano de intervenção: {ip.title}",
                detail=ip.status,
                url=f"/panel/patients/{patient.id}/interventions/{ip.id}",
            )
        )
        for goal in ip.goals.all():
            gwhen = goal.created_at.replace(tzinfo=None) if goal.created_at and goal.created_at.tzinfo else (goal.created_at or when)
            if cutoff and gwhen < cutoff.replace(tzinfo=None):
                continue
            events.append(
                TimelineEvent(
                    when=gwhen,
                    kind="intervention_goal",
                    title=f"Objetivo: {goal.title}",
                    detail=goal.status,
                    url=f"/panel/patients/{patient.id}/interventions/{ip.id}",
                )
            )
        for rev in ip.reviews.all():
            rwhen = datetime.combine(rev.review_date, datetime.min.time())
            if cutoff and rwhen < cutoff.replace(tzinfo=None):
                continue
            events.append(
                TimelineEvent(
                    when=rwhen,
                    kind="intervention_review",
                    title=f"Revisão do plano: {ip.title}",
                    detail=rev.decision,
                    url=f"/panel/patients/{patient.id}/interventions/{ip.id}",
                )
            )

    for note in ProgressNote.query.filter_by(
        patient_id=patient.id, professional_id=professional_id
    ).all():
        when = note.recorded_at.replace(tzinfo=None) if note.recorded_at and note.recorded_at.tzinfo else (note.recorded_at or datetime.min)
        if cutoff and when < cutoff.replace(tzinfo=None):
            continue
        events.append(
            TimelineEvent(
                when=when,
                kind="progress",
                title="Evolução registada",
                detail=note.progress_status,
                url=f"/panel/patients/{patient.id}/evolution",
            )
        )

    events.sort(key=lambda e: e.when, reverse=True)
    return events


def domain_cards_for_patient(
    patient_id: int,
    professional_id: int,
    *,
    domain_id: int | None = None,
    instrument_id: int | None = None,
    months: int | None = None,
) -> list[dict[str, Any]]:
    domains = (
        CognitiveDomain.query.filter_by(is_active=True)
        .order_by(CognitiveDomain.sort_order.asc())
        .all()
    )
    cutoff = None
    if months:
        cutoff = datetime.utcnow() - timedelta(days=30 * months)

    q = CognitiveIndicator.query.filter_by(
        patient_id=patient_id, professional_id=professional_id
    )
    if domain_id:
        q = q.filter_by(domain_id=domain_id)
    indicators = q.order_by(CognitiveIndicator.recorded_at.desc()).all()

    filtered: list[CognitiveIndicator] = []
    for ind in indicators:
        when = ind.recorded_at
        if when and when.tzinfo:
            when = when.replace(tzinfo=None)
        if cutoff and when and when < cutoff.replace(tzinfo=None):
            continue
        if instrument_id:
            ai = ind.assessment_instrument
            if ai is None or ai.instrument_id != instrument_id:
                continue
        filtered.append(ind)

    by_domain: dict[int, list[CognitiveIndicator]] = defaultdict(list)
    for ind in filtered:
        by_domain[ind.domain_id].append(ind)

    cards = []
    for domain in domains:
        if domain_id and domain.id != domain_id:
            continue
        inds = by_domain.get(domain.id, [])
        skill_ids = {i.skill_id for i in inds if i.skill_id}
        latest = inds[0] if inds else None
        instrument_names = []
        seen = set()
        for ind in inds:
            ai = ind.assessment_instrument
            if ai:
                name = ai.display_short_name or ai.display_name
                if name not in seen:
                    seen.add(name)
                    instrument_names.append(name)
        skill_previews = []
        for ind in inds:
            if not ind.skill_id:
                continue
            key = ind.skill_id
            if any(p["skill_id"] == key for p in skill_previews):
                continue
            skill_previews.append(
                {
                    "skill_id": key,
                    "skill_name": ind.skill.name if ind.skill else "Habilidade",
                    "source": (
                        (ind.assessment_instrument.display_short_name
                         or ind.assessment_instrument.display_name)
                        if ind.assessment_instrument
                        else ind.source_type
                    ),
                    "date": ind.recorded_at,
                }
            )
            if len(skill_previews) >= 4:
                break

        cards.append(
            {
                "domain": domain,
                "skills_count": len(skill_ids),
                "indicators_count": len(inds),
                "last_date": latest.recorded_at if latest else None,
                "last_indicator": latest,
                "instruments": instrument_names,
                "skill_previews": skill_previews,
                "latest_interpretation": latest.interpretation if latest else None,
            }
        )
    return cards


def skill_history(
    patient_id: int,
    professional_id: int,
    domain_id: int,
) -> list[dict[str, Any]]:
    skills = (
        CognitiveSkill.query.filter_by(domain_id=domain_id, is_active=True)
        .order_by(CognitiveSkill.sort_order.asc())
        .all()
    )
    indicators = (
        CognitiveIndicator.query.filter_by(
            patient_id=patient_id,
            professional_id=professional_id,
            domain_id=domain_id,
        )
        .order_by(CognitiveIndicator.recorded_at.desc())
        .all()
    )
    by_skill: dict[int | None, list[CognitiveIndicator]] = defaultdict(list)
    for ind in indicators:
        by_skill[ind.skill_id].append(ind)

    rows = []
    for skill in skills:
        inds = by_skill.get(skill.id, [])
        evolution = _compatible_evolution(inds)
        rows.append({"skill": skill, "indicators": inds, "evolution": evolution})

    # Indicadores sem habilidade
    orphan = by_skill.get(None, [])
    if orphan:
        rows.append({"skill": None, "indicators": orphan, "evolution": []})
    return rows


def _compatible_evolution(indicators: list[CognitiveIndicator]) -> list[dict[str, Any]]:
    """Só série temporal se mesma label + mesma unit e valores numéricos."""
    if len(indicators) < 2:
        return []
    groups: dict[tuple[str, str | None], list[CognitiveIndicator]] = defaultdict(list)
    for ind in indicators:
        if ind.value_numeric is None:
            continue
        key = (ind.label.strip().lower(), (ind.unit or "").strip().lower() or None)
        groups[key].append(ind)

    best: list[dict[str, Any]] = []
    for (_label, _unit), items in groups.items():
        if len(items) < 2:
            continue
        ordered = sorted(
            items,
            key=lambda i: i.recorded_at.replace(tzinfo=None)
            if i.recorded_at and i.recorded_at.tzinfo
            else (i.recorded_at or datetime.min),
        )
        series = [
            {
                "date": i.recorded_at,
                "value": i.value_numeric,
                "unit": i.unit,
                "label": i.label,
            }
            for i in ordered
        ]
        if len(series) > len(best):
            best = series
    return best


def indicator_source_label(ind: CognitiveIndicator) -> str:
    if ind.assessment_instrument:
        name = (
            ind.assessment_instrument.display_short_name
            or ind.assessment_instrument.display_name
        )
        if ind.assessment and ind.assessment.assessment_date:
            return f"{name} · Avaliação {ind.assessment.assessment_date.strftime('%d/%m/%Y')}"
        return name
    if ind.source_type == "professional_observation":
        return "Observação profissional"
    if ind.source_type == "manual_entry":
        return "Entrada manual"
    return ind.source_type or "—"
