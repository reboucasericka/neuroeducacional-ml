"""Navegação do prontuário: tabs, ações e breadcrumbs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import url_for


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    url: str
    external: bool = False


@dataclass(frozen=True)
class BreadcrumbItem:
    label: str
    url: str | None = None


def patient_record_tabs(patient_id: int, *, active: str = "overview") -> list[dict[str, Any]]:
    """Tabs do prontuário — Contactos escolares agrupados em Encaminhamentos/Contexto."""
    tabs = [
        NavItem("overview", "Visão Geral", url_for("panel.patient_detail", patient_id=patient_id, tab="overview")),
        NavItem("anamnesis", "Anamnese", url_for("panel.patient_detail", patient_id=patient_id, tab="anamnesis")),
        NavItem("plan", "Planeamento", url_for("care.plans_list", patient_id=patient_id), True),
        NavItem("sessions", "Sessões", url_for("care.sessions_list", patient_id=patient_id), True),
        NavItem("assessments", "Avaliações", url_for("panel.patient_detail", patient_id=patient_id, tab="assessments")),
        NavItem("profile", "Perfil Cognitivo", url_for("cognitive.cognitive_profile", patient_id=patient_id), True),
        NavItem("feedbacks", "Devolutivas", url_for("intervention.feedbacks_list", patient_id=patient_id), True),
        NavItem("intervention", "Intervenção", url_for("intervention.interventions_list", patient_id=patient_id), True),
        NavItem("evolution", "Evolução", url_for("intervention.evolution_view", patient_id=patient_id), True),
        NavItem(
            "referrals",
            "Encaminhamentos",
            url_for("care.referrals", patient_id=patient_id),
            True,
        ),
        NavItem("documents", "Documentos", url_for("care.documents", patient_id=patient_id), True),
        NavItem("timeline", "Timeline", url_for("panel.patient_detail", patient_id=patient_id, tab="timeline")),
    ]
    return [
        {
            "key": t.key,
            "label": t.label,
            "url": t.url,
            "active": t.key == active,
        }
        for t in tabs
    ]


def patient_new_record_actions(patient_id: int) -> list[dict[str, str]]:
    """Ações já implementadas para o menu '+ Novo registo'."""
    return [
        {
            "label": "Nova anamnese",
            "url": url_for("anamnesis.patient_anamnesis_new", patient_id=patient_id),
        },
        {
            "label": "Nova sessão",
            "url": url_for("care.sessions_new", patient_id=patient_id),
        },
        {
            "label": "Nova avaliação",
            "url": url_for("assessment.patient_assessment_new", patient_id=patient_id),
        },
        {
            "label": "Novo plano de avaliação",
            "url": url_for("care.plans_new", patient_id=patient_id),
        },
        {
            "label": "Novo encaminhamento",
            "url": url_for("care.referrals", patient_id=patient_id) + "#novo",
        },
        {
            "label": "Nova devolutiva",
            "url": url_for("intervention.feedbacks_new", patient_id=patient_id),
        },
        {
            "label": "Novo plano de intervenção",
            "url": url_for("intervention.interventions_new", patient_id=patient_id),
        },
        {
            "label": "Nova evolução",
            "url": url_for("intervention.progress_notes_new", patient_id=patient_id),
        },
    ]


def sidebar_active_key(endpoint: str | None) -> str:
    """Identifica secção ativa da sidebar sem substring frágil genérica."""
    ep = endpoint or ""
    mapping = {
        "panel.dashboard": "dashboard",
        "panel.patients_list": "patients",
        "panel.patients_new": "patients",
        "panel.patient_detail": "patients",
        "panel.profile": "profile",
        "panel.reports_placeholder": "reports",
        "panel.settings_placeholder": "settings",
        "anamnesis.templates_list": "anamneses",
        "anamnesis.templates_new": "anamneses",
        "anamnesis.templates_edit": "anamneses",
        "anamnesis.template_structure": "anamneses",
        "assessment.instruments_list": "instruments",
        "assessment.instruments_new": "instruments",
        "assessment.instruments_edit": "instruments",
        "assessment.instruments_view": "instruments",
        "assessment.assessments_list": "assessments",
        "cognitive.instrument_mappings": "settings",
    }
    if ep in mapping:
        return mapping[ep]
    if ep.startswith("anamnesis.patient_"):
        return "patients"
    if ep.startswith("assessment.patient_"):
        return "patients"
    if ep.startswith("care."):
        return "patients"
    if ep.startswith("intervention."):
        return "patients"
    if ep.startswith("cognitive."):
        return "patients"
    return ""


TIMELINE_FILTERS = [
    ("", "Tudo"),
    ("anamnesis", "Anamneses"),
    ("plan", "Planos"),
    ("session", "Sessões"),
    ("assessment", "Avaliações"),
    ("indicator", "Perfil"),
    ("feedback", "Devolutivas"),
    ("intervention", "Intervenções"),
    ("progress", "Evoluções"),
    ("referral", "Encaminhamentos"),
    ("school", "Escola"),
]

TIMELINE_KIND_LABELS = {
    "anamnesis": "Anamnese",
    "assessment": "Avaliação",
    "plan": "Plano",
    "session": "Sessão",
    "referral": "Encaminhamento",
    "school": "Escola",
    "indicator": "Perfil",
    "history": "Histórico",
    "feedback": "Devolutiva",
    "intervention_plan": "Intervenção",
    "intervention_goal": "Objetivo",
    "intervention_review": "Revisão",
    "progress": "Evolução",
    "document": "Documento",
}

FILTER_KIND_GROUPS = {
    "anamnesis": {"anamnesis"},
    "plan": {"plan"},
    "session": {"session"},
    "assessment": {"assessment"},
    "indicator": {"indicator"},
    "feedback": {"feedback"},
    "intervention": {"intervention_plan", "intervention_goal", "intervention_review"},
    "progress": {"progress"},
    "referral": {"referral"},
    "school": {"school"},
    "history": {"history"},
}


def timeline_kind_matches(kind: str, filter_key: str) -> bool:
    if not filter_key:
        return True
    allowed = FILTER_KIND_GROUPS.get(filter_key)
    if not allowed:
        return kind == filter_key
    return kind in allowed
