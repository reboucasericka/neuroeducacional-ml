"""
Terminologia e identidade profissional (contexto brasileiro).

Camada de apresentação — NÃO renomeia o model interno ``Patient``
(tabela ``patients``), para evitar migration destrutiva.

Glossário EN ↔ PT (o utilizador só vê PT):

- learner   → Aprendente / Aprendentes   (termo preferencial da área)
- evaluatee → Avaliando / Avaliandos
- patient   → Paciente / Pacientes       (opção clínica; não é o nome “da área”)

Em inglês, o sujeito típico da neuropsicopedagogia/psicopedagogia
é **learner**, não patient.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.platform.models import Professional

# Tipos permitidos (únicos utilizadores da plataforma)
PROFESSIONAL_TYPES = (
    "clinical_neuropsychopedagogue",
    "institutional_neuropsychopedagogue",
    "psychopedagogue",
)

PROFESSIONAL_TYPE_LABELS = {
    "clinical_neuropsychopedagogue": "Neuropsicopedagogia Clínica",
    "institutional_neuropsychopedagogue": "Neuropsicopedagogia Institucional",
    "psychopedagogue": "Psicopedagogia",
}

PROFESSIONAL_TYPE_BLURBS = {
    "clinical_neuropsychopedagogue": (
        "Avaliação e acompanhamento das funções cognitivas relacionadas "
        "à aprendizagem, em contexto clínico."
    ),
    "institutional_neuropsychopedagogue": (
        "Observação e acompanhamento dos processos de aprendizagem "
        "em contextos institucionais e educacionais."
    ),
    "psychopedagogue": (
        "Avaliação e acompanhamento das dificuldades e potencialidades "
        "relacionadas ao processo de aprendizagem."
    ),
}

PRACTICE_CONTEXTS = {
    "clinical_neuropsychopedagogue": "clinical",
    "institutional_neuropsychopedagogue": "institutional",
    "psychopedagogue": "psychopedagogical",
}

PRACTICE_CONTEXT_LABELS = {
    "clinical": "Clínico",
    "institutional": "Institucional",
    "psychopedagogical": "Psicopedagógico",
}

SUBJECT_TERMS = ("patient", "learner", "evaluatee")

SUBJECT_LABELS = {
    "patient": ("Paciente", "Pacientes"),
    "learner": ("Aprendente", "Aprendentes"),
    "evaluatee": ("Avaliando", "Avaliandos"),
}

DEFAULT_SUBJECT_BY_TYPE = {
    "clinical_neuropsychopedagogue": "patient",
    "institutional_neuropsychopedagogue": "learner",
    "psychopedagogue": "learner",
}

# Migração de valores legados
LEGACY_TYPE_MAP = {
    "psicologo": "clinical_neuropsychopedagogue",
    "psychologist": "clinical_neuropsychopedagogue",
    "": "clinical_neuropsychopedagogue",
}

SCOPE_STATUSES = (
    ("verify", "Verificar"),
    ("allowed", "Permitido"),
    ("not_applicable", "Não aplicável"),
    ("restricted", "Restrito"),
)

DIGITAL_USE_STATUSES = (
    ("verify", "Verificar"),
    ("permitted", "Permitido"),
    ("permission_required", "Requer autorização"),
    ("restricted", "Restrito"),
)

COPYRIGHT_STATUSES = (
    ("unknown", "Desconhecido"),
    ("verify", "Verificar"),
    ("public", "Público"),
    ("restricted", "Restrito"),
    ("proprietary", "Proprietário"),
)


def normalize_professional_type(raw: str | None) -> str:
    value = (raw or "").strip()
    if value in PROFESSIONAL_TYPES:
        return value
    mapped = LEGACY_TYPE_MAP.get(value)
    if mapped:
        return mapped
    return "clinical_neuropsychopedagogue"


def professional_type_label(raw: str | None) -> str:
    key = normalize_professional_type(raw)
    return PROFESSIONAL_TYPE_LABELS[key]


def practice_context(raw_type: str | None) -> str:
    key = normalize_professional_type(raw_type)
    return PRACTICE_CONTEXTS[key]


def resolve_subject_term(professional: Professional | None) -> str:
    if professional is None:
        return "patient"
    preferred = getattr(professional, "preferred_subject_term", None)
    if preferred in SUBJECT_TERMS:
        return preferred
    return DEFAULT_SUBJECT_BY_TYPE.get(
        normalize_professional_type(professional.professional_type),
        "patient",
    )


def subject_label(professional: Professional | None = None, *, plural: bool = False) -> str:
    term = resolve_subject_term(professional)
    singular, plural_label = SUBJECT_LABELS[term]
    return plural_label if plural else singular


def subject_label_plural(professional: Professional | None = None) -> str:
    return subject_label(professional, plural=True)


def scope_status_label(status: str | None) -> str:
    return dict(SCOPE_STATUSES).get(status or "verify", status or "Verificar")


def digital_use_label(status: str | None) -> str:
    return dict(DIGITAL_USE_STATUSES).get(status or "verify", status or "Verificar")
