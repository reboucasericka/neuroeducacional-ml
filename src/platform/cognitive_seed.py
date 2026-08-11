"""
Seeds do Perfil Cognitivo V1 (domínios, habilidades, mappings demonstrativos).

Não cria scores clínicos nem normas. CognitiveDomainSummary fica documentado
como melhoria futura (não implementado nesta fase).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from src.platform.anamnesis_utils import slugify
from src.platform.extensions import db
from src.platform.models import (
    Assessment,
    AssessmentInstrument,
    AssessmentResult,
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    Instrument,
    InstrumentSkillMapping,
    Patient,
    Professional,
    utcnow,
)

DOMAINS_V1 = [
    ("Atenção e Funções Executivas", "atencao-funcoes-executivas", 1),
    ("Memória de Trabalho", "memoria-de-trabalho", 2),
    ("Linguagem Oral / Processamento Fonológico", "linguagem-oral", 3),
    ("Leitura", "leitura", 4),
    ("Escrita", "escrita", 5),
    ("Aritmética", "aritmetica", 6),
]

SKILLS_BY_DOMAIN = {
    "atencao-funcoes-executivas": [
        "Atenção seletiva",
        "Atenção sustentada",
        "Controle inibitório",
        "Flexibilidade cognitiva",
        "Planejamento",
        "Monitoramento",
    ],
    "memoria-de-trabalho": [
        "Span verbal",
        "Manutenção verbal",
        "Memória visuoespacial",
        "Manipulação de informação",
    ],
    "linguagem-oral": [
        "Discriminação fonológica",
        "Consciência fonológica",
        "Consciência sintática",
        "Vocabulário receptivo",
        "Nomeação",
        "Repetição de palavras",
        "Repetição de pseudopalavras",
        "Compreensão oral",
    ],
    "leitura": [
        "Decodificação de palavras",
        "Decodificação de pseudopalavras",
        "Precisão de leitura",
        "Fluência de leitura",
        "Compreensão leitora",
    ],
    "escrita": [
        "Codificação fonema-grafema",
        "Ortografia",
        "Precisão de escrita",
        "Produção textual",
    ],
    "aritmetica": [
        "Processamento numérico",
        "Cálculo",
        "Fatos aritméticos",
        "Precisão de cálculo",
    ],
}

# Mappings demonstrativos (catálogo → domínio/habilidade). Configuráveis.
MAPPING_SPECS = [
    ("stroop", "atencao-funcoes-executivas", "controle-inibitorio"),
    ("torre-de-londres", "atencao-funcoes-executivas", "planejamento"),
    ("pahcl", "linguagem-oral", "consciencia-fonologica"),
    ("pahcl", "leitura", "decodificacao-de-palavras"),
    ("pahcl", "escrita", "ortografia"),
]


def ensure_cognitive_catalog() -> None:
    for name, slug, order in DOMAINS_V1:
        domain = CognitiveDomain.query.filter_by(slug=slug).first()
        if domain is None:
            domain = CognitiveDomain(
                name=name,
                slug=slug,
                description=f"Domínio V1 — {name}.",
                sort_order=order,
                is_active=True,
            )
            db.session.add(domain)
            db.session.flush()
        else:
            domain.name = name
            domain.sort_order = order
            domain.is_active = True

        for idx, skill_name in enumerate(SKILLS_BY_DOMAIN.get(slug, []), start=1):
            skill_slug = slugify(skill_name)
            skill = CognitiveSkill.query.filter_by(
                domain_id=domain.id, slug=skill_slug
            ).first()
            if skill is None:
                db.session.add(
                    CognitiveSkill(
                        domain_id=domain.id,
                        name=skill_name,
                        slug=skill_slug,
                        sort_order=idx,
                        is_active=True,
                    )
                )
            else:
                skill.name = skill_name
                skill.sort_order = idx
                skill.is_active = True

    db.session.commit()
    _ensure_instrument_mappings()


def _ensure_instrument_mappings() -> None:
    for instrument_slug, domain_slug, skill_slug in MAPPING_SPECS:
        instrument = Instrument.query.filter_by(slug=instrument_slug).first()
        domain = CognitiveDomain.query.filter_by(slug=domain_slug).first()
        if instrument is None or domain is None:
            continue
        skill = CognitiveSkill.query.filter_by(
            domain_id=domain.id, slug=skill_slug
        ).first()
        existing = InstrumentSkillMapping.query.filter_by(
            instrument_id=instrument.id,
            domain_id=domain.id,
            skill_id=skill.id if skill else None,
        ).first()
        if existing is None:
            db.session.add(
                InstrumentSkillMapping(
                    instrument_id=instrument.id,
                    domain_id=domain.id,
                    skill_id=skill.id if skill else None,
                    notes="DEMONSTRAÇÃO — mapping configurável de catálogo.",
                    is_active=True,
                )
            )
    db.session.commit()


def ensure_demo_cognitive_patient() -> None:
    """Paciente DEMO-001 com indicadores fictícios claramente marcados."""
    pro = Professional.query.filter_by(email="demo@neurolearn.local").first()
    if pro is None:
        return

    patient = Patient.query.filter_by(
        professional_id=pro.id, internal_code="DEMO-001"
    ).first()
    if patient is None:
        patient = Patient(
            professional_id=pro.id,
            internal_code="DEMO-001",
            name="Lara Mendes",
            birth_date=date(2016, 3, 15),
            sex="feminino",
            education_level="5º ano",
            is_minor=True,
            status="ativo",
            notes=(
                "DEMONSTRAÇÃO — perfil cognitivo fictício para portfólio. "
                "Não são normas. Dados fictícios."
            ),
        )
        db.session.add(patient)
        db.session.flush()

    # Evitar recriar indicadores demo se já existirem.
    if (
        CognitiveIndicator.query.filter_by(patient_id=patient.id)
        .filter(CognitiveIndicator.label.ilike("%DEMONSTRAÇÃO%"))
        .count()
        > 0
    ):
        db.session.commit()
        return

    stroop = Instrument.query.filter_by(slug="stroop").first()
    tol = Instrument.query.filter_by(slug="torre-de-londres").first()
    domain_fe = CognitiveDomain.query.filter_by(slug="atencao-funcoes-executivas").first()
    domain_read = CognitiveDomain.query.filter_by(slug="leitura").first()
    if not domain_fe:
        db.session.commit()
        return

    skill_inhib = CognitiveSkill.query.filter_by(
        domain_id=domain_fe.id, slug="controle-inibitorio"
    ).first()
    skill_plan = CognitiveSkill.query.filter_by(
        domain_id=domain_fe.id, slug="planejamento"
    ).first()
    skill_fluency = None
    if domain_read:
        skill_fluency = CognitiveSkill.query.filter_by(
            domain_id=domain_read.id, slug="fluencia-de-leitura"
        ).first()

    assessment = Assessment(
        patient_id=patient.id,
        professional_id=pro.id,
        assessment_date=datetime.now(timezone.utc).date() - timedelta(days=5),
        reason="Avaliação demonstrativa — perfil cognitivo",
        status="completed",
        general_notes="DEMONSTRAÇÃO — sem instrumentos reais aplicados.",
        completed_at=utcnow(),
    )
    db.session.add(assessment)
    db.session.flush()

    now = utcnow()
    ai_stroop = None
    ai_tol = None
    if stroop:
        ai_stroop = AssessmentInstrument(
            assessment_id=assessment.id,
            instrument_id=stroop.id,
            instrument_name=stroop.name,
            instrument_short_name=stroop.short_name,
            status="completed",
            raw_score=None,
            professional_interpretation="DEMONSTRAÇÃO — interpretação fictícia.",
            completed_at=now,
        )
        db.session.add(ai_stroop)
        db.session.flush()
        result = AssessmentResult(
            assessment_instrument_id=ai_stroop.id,
            metric_name="interferência (demo)",
            raw_value="18",
            unit="erros",
            interpretation="DEMONSTRAÇÃO — valor fictício.",
            source="professional",
            sort_order=0,
        )
        db.session.add(result)
        db.session.flush()
        db.session.add(
            CognitiveIndicator(
                patient_id=patient.id,
                professional_id=pro.id,
                assessment_id=assessment.id,
                assessment_instrument_id=ai_stroop.id,
                assessment_result_id=result.id,
                domain_id=domain_fe.id,
                skill_id=skill_inhib.id if skill_inhib else None,
                recorded_at=now - timedelta(days=5),
                label="DEMONSTRAÇÃO — interferência Stroop",
                value_numeric=18.0,
                value_text="18",
                unit="erros",
                interpretation="DEMONSTRAÇÃO — não é norma clínica.",
                source_type="assessment_result",
            )
        )

    if tol:
        ai_tol = AssessmentInstrument(
            assessment_id=assessment.id,
            instrument_id=tol.id,
            instrument_name=tol.name,
            instrument_short_name=tol.short_name,
            status="completed",
            professional_interpretation="DEMONSTRAÇÃO — interpretação fictícia.",
            completed_at=now,
        )
        db.session.add(ai_tol)
        db.session.flush()
        result_tol = AssessmentResult(
            assessment_instrument_id=ai_tol.id,
            metric_name="escore (demo)",
            raw_value="22",
            unit="pontos",
            interpretation="DEMONSTRAÇÃO — valor fictício.",
            source="professional",
            sort_order=0,
        )
        db.session.add(result_tol)
        db.session.flush()
        db.session.add(
            CognitiveIndicator(
                patient_id=patient.id,
                professional_id=pro.id,
                assessment_id=assessment.id,
                assessment_instrument_id=ai_tol.id,
                assessment_result_id=result_tol.id,
                domain_id=domain_fe.id,
                skill_id=skill_plan.id if skill_plan else None,
                recorded_at=now - timedelta(days=5),
                label="DEMONSTRAÇÃO — escore ToL",
                value_numeric=22.0,
                value_text="22",
                unit="pontos",
                interpretation="DEMONSTRAÇÃO — não é norma clínica.",
                source_type="assessment_result",
            )
        )

    # Evolução comparável (mesma métrica/unidade) — apenas demo.
    if domain_read and skill_fluency:
        for months_ago, value in ((8, 42.0), (4, 48.0), (0, 56.0)):
            recorded = now - timedelta(days=30 * months_ago)
            db.session.add(
                CognitiveIndicator(
                    patient_id=patient.id,
                    professional_id=pro.id,
                    domain_id=domain_read.id,
                    skill_id=skill_fluency.id,
                    recorded_at=recorded,
                    label="DEMONSTRAÇÃO — fluência de leitura",
                    value_numeric=value,
                    value_text=str(int(value)),
                    unit="ppm",
                    interpretation="DEMONSTRAÇÃO — série fictícia comparável (mesma unidade).",
                    source_type="manual_entry",
                )
            )

    db.session.commit()
