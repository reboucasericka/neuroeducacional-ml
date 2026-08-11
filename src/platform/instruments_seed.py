"""
Catálogo seed de instrumentos (apenas metadados).

Não inclui itens, normas, scoring ou conteúdo protegido.
"""

from __future__ import annotations

from sqlalchemy import or_

from src.platform.anamnesis_utils import slugify
from src.platform.extensions import db
from src.platform.models import Instrument, InstrumentProfessionalScope, utcnow
from src.platform.terminology import PROFESSIONAL_TYPES

INSTRUMENT_CATEGORIES = [
    "Neuropsicologia",
    "Funções Executivas",
    "Atenção",
    "Memória",
    "Linguagem",
    "Aprendizagem",
    "Leitura",
    "Escrita",
    "Aritmética",
    "Ansiedade",
    "Depressão",
    "Estresse",
    "Risco",
    "Qualidade de Vida",
    "Autoestima",
    "Comportamento",
    "Entrevista Clínica",
    "Outros",
]

LICENSE_STATUSES = [
    ("unknown", "Desconhecido"),
    ("public", "Público"),
    ("restricted", "Restrito"),
    ("proprietary", "Proprietário"),
    ("permission_required", "Requer autorização"),
]

CATALOG_SEED = [
    {
        "name": "Stroop",
        "short_name": "Stroop",
        "slug": "stroop",
        "category": "Funções Executivas",
        "target_population": "crianca_adolescente_adulto",
        "minimum_age": 6,
        "maximum_age": None,
        "purpose": "Catálogo — referência conceptual a controlo inibitório/interferência.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem conteúdo interno do teste.",
    },
    {
        "name": "Torre de Londres",
        "short_name": "ToL",
        "slug": "torre-de-londres",
        "category": "Funções Executivas",
        "target_population": "crianca_adolescente_adulto",
        "minimum_age": 7,
        "maximum_age": None,
        "purpose": "Catálogo — referência conceptual a planeamento.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem conteúdo interno do teste.",
    },
    {
        "name": "Protocolo de Avaliação de Habilidades Cognitivo-Linguísticas",
        "short_name": "PAHCL",
        "slug": "pahcl",
        "category": "Aprendizagem",
        "target_population": "crianca_adolescente",
        "minimum_age": 5,
        "maximum_age": 15,
        "purpose": "Catálogo — metadado de protocolo cognitivo-linguístico.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem conteúdo interno.",
    },
    {
        "name": "GAD-7",
        "short_name": "GAD-7",
        "slug": "gad-7",
        "category": "Ansiedade",
        "target_population": "adulto",
        "minimum_age": 18,
        "maximum_age": None,
        "purpose": "Catálogo — metadado de instrumento de ansiedade.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem perguntas nem scoring.",
    },
    {
        "name": "PHQ-9",
        "short_name": "PHQ-9",
        "slug": "phq-9",
        "category": "Depressão",
        "target_population": "adulto",
        "minimum_age": 18,
        "maximum_age": None,
        "purpose": "Catálogo — metadado de instrumento de depressão.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem perguntas nem scoring.",
    },
    {
        "name": "HADS",
        "short_name": "HADS",
        "slug": "hads",
        "category": "Ansiedade",
        "target_population": "adulto",
        "minimum_age": 16,
        "maximum_age": None,
        "purpose": "Catálogo — metadado.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem perguntas nem scoring.",
    },
    {
        "name": "DASS-21",
        "short_name": "DASS-21",
        "slug": "dass-21",
        "category": "Estresse",
        "target_population": "adolescente_adulto",
        "minimum_age": 14,
        "maximum_age": None,
        "purpose": "Catálogo — metadado.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem perguntas nem scoring.",
    },
    {
        "name": "SCARED",
        "short_name": "SCARED",
        "slug": "scared",
        "category": "Ansiedade",
        "target_population": "crianca_adolescente",
        "minimum_age": 8,
        "maximum_age": 18,
        "purpose": "Catálogo — metadado.",
        "license_status": "unknown",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem perguntas nem scoring.",
    },
    {
        "name": "BDI-II",
        "short_name": "BDI-II",
        "slug": "bdi-ii",
        "category": "Depressão",
        "target_population": "adolescente_adulto",
        "minimum_age": 13,
        "maximum_age": None,
        "purpose": "Catálogo — metadado.",
        "license_status": "proprietary",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem perguntas nem scoring.",
    },
    {
        "name": "C-SSRS",
        "short_name": "C-SSRS",
        "slug": "c-ssrs",
        "category": "Risco",
        "target_population": "adolescente_adulto",
        "minimum_age": 12,
        "maximum_age": None,
        "purpose": "Catálogo — metadado.",
        "license_status": "permission_required",
        "reference": "Metadado de catálogo (sem itens).",
        "notes": "DEMONSTRAÇÃO — sem perguntas nem scoring.",
    },
]


def ensure_instrument_catalog() -> None:
    now = utcnow()
    for spec in CATALOG_SEED:
        instrument = Instrument.query.filter_by(slug=spec["slug"]).first()
        if instrument is None:
            instrument = Instrument.query.filter_by(name=spec["name"]).first()
        if instrument is None:
            db.session.add(
                Instrument(
                    name=spec["name"],
                    short_name=spec["short_name"],
                    slug=spec["slug"],
                    category=spec["category"],
                    description="Entrada de catálogo. Sem conteúdo interno do instrumento.",
                    target_population=spec["target_population"],
                    minimum_age=spec["minimum_age"],
                    maximum_age=spec["maximum_age"],
                    purpose=spec["purpose"],
                    license_status=spec["license_status"],
                    reference=spec["reference"],
                    notes=spec["notes"],
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            instrument.short_name = spec["short_name"]
            instrument.slug = spec["slug"]
            instrument.category = spec["category"]
            instrument.target_population = spec["target_population"]
            instrument.minimum_age = spec["minimum_age"]
            instrument.maximum_age = spec["maximum_age"]
            instrument.purpose = spec["purpose"]
            if instrument.license_status in (None, "", "a_verificar"):
                instrument.license_status = spec["license_status"]
            instrument.reference = spec["reference"]
            if not instrument.notes:
                instrument.notes = spec["notes"]
            instrument.touch()

    for instrument in Instrument.query.filter(
        or_(Instrument.slug.is_(None), Instrument.slug == "")
    ).all():
        base = slugify(instrument.short_name or instrument.name)
        candidate = base
        n = 2
        while Instrument.query.filter(
            Instrument.slug == candidate, Instrument.id != instrument.id
        ).first():
            candidate = f"{base}-{n}"
            n += 1
        instrument.slug = candidate

    db.session.commit()
    ensure_instrument_professional_scopes()


def ensure_instrument_professional_scopes() -> None:
    """Cria escopos N:N com status=verify (nunca assume allowed)."""
    instruments = Instrument.query.all()
    if not instruments:
        return
    for instrument in instruments:
        if not getattr(instrument, "digital_use_status", None):
            instrument.digital_use_status = "verify"
        if not getattr(instrument, "copyright_status", None):
            instrument.copyright_status = "unknown"
        for ptype in PROFESSIONAL_TYPES:
            exists = InstrumentProfessionalScope.query.filter_by(
                instrument_id=instrument.id,
                professional_type=ptype,
            ).first()
            if exists is None:
                db.session.add(
                    InstrumentProfessionalScope(
                        instrument_id=instrument.id,
                        professional_type=ptype,
                        status="verify",
                    )
                )
    db.session.commit()


def ensure_scopes_for_instrument(instrument: Instrument) -> None:
    for ptype in PROFESSIONAL_TYPES:
        exists = InstrumentProfessionalScope.query.filter_by(
            instrument_id=instrument.id,
            professional_type=ptype,
        ).first()
        if exists is None:
            db.session.add(
                InstrumentProfessionalScope(
                    instrument_id=instrument.id,
                    professional_type=ptype,
                    status="verify",
                )
            )
