"""
Seed de jornada profissional fictícia para portfólio (PORTFOLIO_DEMO_V2).

Dados 100% fictícios — sem pessoas reais e sem linguagem de diagnóstico clínico.
Idempotente: seguro chamar repetidamente.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

from src.platform.extensions import db
from src.platform.models import (
    AnamnesisField,
    AnamnesisTemplate,
    Assessment,
    AssessmentInstrument,
    AssessmentPlan,
    AssessmentPlanObjective,
    AssessmentResult,
    CognitiveDomain,
    CognitiveIndicator,
    CognitiveSkill,
    FeedbackReport,
    Instrument,
    InterventionGoal,
    InterventionPlan,
    InterventionStrategy,
    Patient,
    PatientAnamnesis,
    PatientAnamnesisResponse,
    PatientDocument,
    PatientGuardian,
    PatientHistoryEntry,
    Professional,
    ProfessionalSession,
    ProgressNote,
    Referral,
    SchoolContact,
)

PORTFOLIO_MARKER = "PORTFOLIO_DEMO_V2"
SEED_HISTORY_TITLE = "SEED:PORTFOLIO_DEMO_V2"
DEMO_NOTES = "DEMONSTRAÇÃO — dados fictícios."

ANAMNESIS_ANSWERS = [
    "Queixa principal: dificuldades em leitura fluente e manutenção da atenção em tarefas longas (DEMONSTRAÇÃO — fictício).",
    "Histórico escolar: boa participação em aula; prefere atividades com suporte visual (DEMONSTRAÇÃO).",
    "Potencialidades: interesse por materiais coloridos, persistência quando recebe orientação clara e pausas curtas.",
    "Atenção: consegue focar melhor em ambientes calmos e com instruções segmentadas.",
    "Leitura: decodifica palavras familiares com apoio; cansa-se em textos longos.",
    "Rotina em casa: rotina relativamente estável; gosta de histórias ilustradas.",
    "Interesses: artes visuais, jogos de construção e leitura compartilhada.",
    "Expectativas da família: apoiar organização da atenção e confiança na leitura (sem pretensão diagnóstica).",
]


def _dt(d: date, hour: int = 12, minute: int = 0) -> datetime:
    return datetime.combine(d, time(hour, minute), tzinfo=timezone.utc)


def _has_portfolio_marker(patient: Patient) -> bool:
    notes = patient.notes or ""
    if PORTFOLIO_MARKER in notes:
        return True
    return (
        PatientHistoryEntry.query.filter_by(
            patient_id=patient.id, title=SEED_HISTORY_TITLE
        ).first()
        is not None
    )


def _demo001_journey_complete(patient: Patient) -> bool:
    has_anamnesis = (
        PatientAnamnesis.query.filter_by(patient_id=patient.id, status="completed").first()
        is not None
    )
    has_feedback = (
        FeedbackReport.query.filter_by(patient_id=patient.id)
        .filter(FeedbackReport.title.ilike("%Devolutiva familiar — DEMO%"))
        .first()
        is not None
    )
    has_plan = (
        InterventionPlan.query.filter_by(patient_id=patient.id)
        .filter(
            InterventionPlan.title.ilike(
                "%Plano de intervenção — leitura e organização da atenção%"
            )
        )
        .first()
        is not None
    )
    return bool(has_anamnesis and has_feedback and has_plan and _has_portfolio_marker(patient))


def _ensure_guardian(
    patient: Patient,
    *,
    name: str,
    relationship: str = "mãe",
    phone: str = "+351 900 000 001",
    email: str = "responsavel.demo@example.invalid",
) -> None:
    if PatientGuardian.query.filter_by(patient_id=patient.id, is_primary=True).first():
        return
    existing = PatientGuardian.query.filter_by(patient_id=patient.id, name=name).first()
    if existing:
        return
    db.session.add(
        PatientGuardian(
            patient_id=patient.id,
            name=name,
            relationship=relationship,
            phone=phone,
            email=email,
            is_primary=True,
        )
    )


def _get_or_create_patient(
    pro: Professional,
    *,
    code: str,
    name: str,
    birth_date: date,
    sex: str,
    education_level: str,
    status: str = "ativo",
    is_minor: bool = True,
    notes: str = DEMO_NOTES,
) -> tuple[Patient, bool]:
    patient = Patient.query.filter_by(
        professional_id=pro.id, internal_code=code
    ).first()
    created = False
    if patient is None:
        patient = Patient(
            professional_id=pro.id,
            internal_code=code,
            name=name,
            birth_date=birth_date,
            sex=sex,
            education_level=education_level,
            is_minor=is_minor,
            status=status,
            notes=notes,
        )
        db.session.add(patient)
        db.session.flush()
        created = True
    return patient, created


def _ensure_demo001_patient(pro: Professional) -> Patient:
    patient, created = _get_or_create_patient(
        pro,
        code="DEMO-001",
        name="Lara Mendes",
        birth_date=date(2016, 3, 15),
        sex="feminino",
        education_level="5º ano",
        status="ativo",
        is_minor=True,
        notes=(
            "DEMONSTRAÇÃO — dados fictícios para portfólio (PORTFOLIO_DEMO_V2). "
            "Não corresponde a pessoa real."
        ),
    )
    # Atualizar caso legado (ex.: "Paciente DEMO Cognitivo").
    patient.name = "Lara Mendes"
    patient.birth_date = date(2016, 3, 15)
    patient.sex = "feminino"
    patient.education_level = "5º ano"
    patient.is_minor = True
    patient.status = "ativo"
    notes = patient.notes or ""
    if "DEMONSTRAÇÃO" not in notes or PORTFOLIO_MARKER not in notes:
        patient.notes = (
            "DEMONSTRAÇÃO — dados fictícios para portfólio (PORTFOLIO_DEMO_V2). "
            "Não corresponde a pessoa real. Conteúdo meramente ilustrativo."
        )
    _ensure_guardian(
        patient,
        name="Helena Mendes",
        relationship="mãe",
        phone="+351 910 000 001",
        email="helena.mendes@example.invalid",
    )
    if created:
        db.session.flush()
    return patient


def _ensure_anamnesis(pro: Professional, patient: Patient) -> PatientAnamnesis | None:
    existing = (
        PatientAnamnesis.query.filter_by(patient_id=patient.id)
        .filter(PatientAnamnesis.notes.ilike(f"%{PORTFOLIO_MARKER}%"))
        .first()
    )
    if existing is None:
        existing = (
            PatientAnamnesis.query.filter_by(patient_id=patient.id, status="completed")
            .order_by(PatientAnamnesis.id.asc())
            .first()
        )
        if existing and existing.notes and PORTFOLIO_MARKER in (existing.notes or ""):
            return existing
        # Se já há anamnese completa sem marker, não duplicar.
        if existing:
            if PORTFOLIO_MARKER not in (existing.notes or ""):
                existing.notes = (
                    (existing.notes or "")
                    + f" | DEMONSTRAÇÃO {PORTFOLIO_MARKER}"
                ).strip(" |")
            return existing

    template = AnamnesisTemplate.query.filter_by(
        slug="anamnese-neuroeducacional-v2", is_active=True
    ).first()
    if template is None:
        template = (
            AnamnesisTemplate.query.filter_by(is_active=True)
            .order_by(AnamnesisTemplate.id.asc())
            .first()
        )
    if template is None:
        return None

    started = _dt(date(2026, 3, 12), 10, 0)
    anamnesis = PatientAnamnesis(
        patient_id=patient.id,
        template_id=template.id,
        professional_id=pro.id,
        started_at=started,
        completed_at=_dt(date(2026, 3, 12), 11, 30),
        status="completed",
        notes=f"DEMONSTRAÇÃO — anamnese fictícia ({PORTFOLIO_MARKER}).",
        created_at=started,
        updated_at=started,
    )
    db.session.add(anamnesis)
    db.session.flush()

    fields = (
        AnamnesisField.query.filter_by(template_id=template.id, is_active=True)
        .order_by(AnamnesisField.sort_order.asc(), AnamnesisField.id.asc())
        .limit(8)
        .all()
    )
    for idx, field in enumerate(fields):
        answer = ANAMNESIS_ANSWERS[idx % len(ANAMNESIS_ANSWERS)]
        db.session.add(
            PatientAnamnesisResponse(
                patient_anamnesis_id=anamnesis.id,
                field_id=field.id,
                value=answer,
                created_at=started,
                updated_at=started,
            )
        )
    return anamnesis


def _ensure_assessment_plan(
    pro: Professional, patient: Patient
) -> AssessmentPlan | None:
    title = "Plano de avaliação — DEMO-001"
    plan = AssessmentPlan.query.filter_by(patient_id=patient.id, title=title).first()
    if plan is not None:
        return plan

    plan = AssessmentPlan(
        patient_id=patient.id,
        professional_id=pro.id,
        title=title,
        reason=(
            "DEMONSTRAÇÃO — mapear leitura, atenção e potencialidades "
            "em contexto escolar (dados fictícios)."
        ),
        objectives="Observar leitura oral, atenção sustentada e estratégias de apoio.",
        initial_hypotheses=(
            "Hipóteses de trabalho meramente ilustrativas — sem valor clínico."
        ),
        status="active",
        planned_start_date=date(2026, 3, 20),
        planned_end_date=date(2026, 5, 20),
        estimated_sessions=4,
        notes=f"DEMONSTRAÇÃO {PORTFOLIO_MARKER}",
        created_at=_dt(date(2026, 3, 20)),
        updated_at=_dt(date(2026, 3, 20)),
    )
    db.session.add(plan)
    db.session.flush()

    domain_read = CognitiveDomain.query.filter_by(slug="leitura").first()
    domain_att = CognitiveDomain.query.filter_by(
        slug="atencao-funcoes-executivas"
    ).first()
    db.session.add_all(
        [
            AssessmentPlanObjective(
                assessment_plan_id=plan.id,
                title="Observar fluência e compreensão leitora em textos curtos",
                description="DEMONSTRAÇÃO — objetivo fictício de avaliação.",
                domain_id=domain_read.id if domain_read else None,
                priority="alta",
                status="open",
                sort_order=1,
            ),
            AssessmentPlanObjective(
                assessment_plan_id=plan.id,
                title="Observar organização da atenção em tarefas guiadas",
                description="DEMONSTRAÇÃO — objetivo fictício de avaliação.",
                domain_id=domain_att.id if domain_att else None,
                priority="média",
                status="open",
                sort_order=2,
            ),
        ]
    )
    return plan


def _ensure_assessment_sessions(
    pro: Professional, patient: Patient, plan: AssessmentPlan | None
) -> None:
    specs = [
        (
            date(2026, 4, 8),
            "assessment",
            "Sessão de avaliação — leitura e atenção (DEMO)",
            (
                "Observou-se interesse por materiais visuais e boa colaboração "
                "quando as instruções foram segmentadas. Dificuldades aparentes "
                "em manter o ritmo em textos mais longos (DEMONSTRAÇÃO)."
            ),
            "Participação ativa; humor colaborativo; gosto por feedback imediato.",
            "Cansaço progressivo em leitura prolongada; necessidade de pausas.",
        ),
        (
            date(2026, 4, 22),
            "observation",
            "Sessão de observação — tarefas guiadas (DEMO)",
            (
                "Em ambiente estruturado, manteve engajamento com apoio visual. "
                "Pontos de dificuldade: organização da sequência de passos "
                "em tarefas multi-etapas (DEMONSTRAÇÃO — fictício)."
            ),
            "Persistência com orientação; uso espontâneo de apontar no texto.",
            "Distração com ruídos; necessidade de redirecionamento pontual.",
        ),
    ]
    for session_date, stype, objective, summary, strengths, difficulties in specs:
        exists = ProfessionalSession.query.filter_by(
            patient_id=patient.id,
            session_date=session_date,
            session_type=stype,
        ).first()
        if exists:
            continue
        db.session.add(
            ProfessionalSession(
                patient_id=patient.id,
                professional_id=pro.id,
                assessment_plan_id=plan.id if plan else None,
                session_date=session_date,
                start_time="14:00",
                end_time="15:00",
                session_type=stype,
                status="completed",
                objective=objective,
                summary=summary,
                professional_notes=summary,
                strengths_observed=strengths,
                difficulties_observed=difficulties,
                next_steps="Continuar observação com materiais de leitura curtos.",
                participants="paciente;mãe",
                created_at=_dt(session_date, 14, 0),
                updated_at=_dt(session_date, 15, 0),
            )
        )


def _ensure_may_assessment(pro: Professional, patient: Patient) -> Assessment | None:
    reason = "Avaliação multidimensional demonstrativa"
    assessment = Assessment.query.filter_by(
        patient_id=patient.id, reason=reason
    ).first()
    if assessment is not None:
        _ensure_may_cognitive_indicators(pro, patient, assessment)
        return assessment

    completed_at = _dt(date(2026, 5, 14), 16, 0)
    assessment = Assessment(
        patient_id=patient.id,
        professional_id=pro.id,
        assessment_date=date(2026, 5, 14),
        reason=reason,
        assessment_type="initial",
        status="completed",
        general_notes=(
            "DEMONSTRAÇÃO — avaliação fictícia multidimensional. "
            "Sem instrumentos reais aplicados; valores ilustrativos."
        ),
        created_at=_dt(date(2026, 5, 14), 9, 0),
        updated_at=completed_at,
        completed_at=completed_at,
    )
    db.session.add(assessment)
    db.session.flush()

    for slug in ("stroop", "pahcl"):
        instrument = Instrument.query.filter_by(slug=slug).first()
        if instrument is None:
            instrument = (
                Instrument.query.filter_by(is_active=True)
                .order_by(Instrument.id.asc())
                .first()
            )
        if instrument is None:
            continue
        already = AssessmentInstrument.query.filter_by(
            assessment_id=assessment.id, instrument_id=instrument.id
        ).first()
        if already:
            continue
        ai = AssessmentInstrument(
            assessment_id=assessment.id,
            instrument_id=instrument.id,
            instrument_name=instrument.name,
            instrument_short_name=instrument.short_name,
            status="completed",
            professional_interpretation=(
                "DEMONSTRAÇÃO — interpretação fictícia prudente, sem valor clínico."
            ),
            notes="DEMONSTRAÇÃO — métrica ilustrativa.",
            completed_at=completed_at,
            created_at=completed_at,
            updated_at=completed_at,
        )
        db.session.add(ai)
        db.session.flush()
        db.session.add(
            AssessmentResult(
                assessment_instrument_id=ai.id,
                metric_name="indicador demo",
                raw_value="demo",
                unit="n/a",
                interpretation="DEMONSTRAÇÃO — valor fictício.",
                source="professional",
                sort_order=0,
            )
        )

    _ensure_may_cognitive_indicators(pro, patient, assessment)
    return assessment


def _ensure_may_cognitive_indicators(
    pro: Professional, patient: Patient, assessment: Assessment | None
) -> None:
    """Indicadores de leitura/atenção em maio — não duplica se já houver DEMONSTRAÇÃO."""
    may_start = _dt(date(2026, 5, 1))
    may_end = _dt(date(2026, 5, 31), 23, 59)
    existing_may = (
        CognitiveIndicator.query.filter_by(patient_id=patient.id)
        .filter(CognitiveIndicator.label.ilike("%DEMONSTRAÇÃO%"))
        .filter(CognitiveIndicator.recorded_at >= may_start)
        .filter(CognitiveIndicator.recorded_at <= may_end)
        .count()
    )
    if existing_may > 0:
        return

    # Se já existem indicadores demo de leitura/atenção (seed cognitivo),
    # ainda assim adicionamos o marco de maio apenas se ausente.
    domain_att = CognitiveDomain.query.filter_by(
        slug="atencao-funcoes-executivas"
    ).first()
    domain_read = CognitiveDomain.query.filter_by(slug="leitura").first()
    if domain_att is None and domain_read is None:
        return

    skill_att = None
    if domain_att:
        skill_att = CognitiveSkill.query.filter_by(
            domain_id=domain_att.id, slug="atencao-sustentada"
        ).first()
    skill_read = None
    if domain_read:
        skill_read = CognitiveSkill.query.filter_by(
            domain_id=domain_read.id, slug="fluencia-de-leitura"
        ).first()

    recorded = _dt(date(2026, 5, 14), 16, 30)
    if domain_att:
        db.session.add(
            CognitiveIndicator(
                patient_id=patient.id,
                professional_id=pro.id,
                assessment_id=assessment.id if assessment else None,
                domain_id=domain_att.id,
                skill_id=skill_att.id if skill_att else None,
                recorded_at=recorded,
                label="DEMONSTRAÇÃO — atenção sustentada (maio)",
                value_numeric=3.0,
                value_text="observacional",
                unit="escala-demo",
                interpretation=(
                    "DEMONSTRAÇÃO — observação qualitativa fictícia; não é norma."
                ),
                source_type="manual_entry",
            )
        )
    if domain_read:
        db.session.add(
            CognitiveIndicator(
                patient_id=patient.id,
                professional_id=pro.id,
                assessment_id=assessment.id if assessment else None,
                domain_id=domain_read.id,
                skill_id=skill_read.id if skill_read else None,
                recorded_at=recorded,
                label="DEMONSTRAÇÃO — leitura (maio)",
                value_numeric=52.0,
                value_text="52",
                unit="ppm-demo",
                interpretation=(
                    "DEMONSTRAÇÃO — valor ilustrativo de fluência; não é norma."
                ),
                source_type="manual_entry",
            )
        )


def _ensure_feedback(
    pro: Professional, patient: Patient, plan: AssessmentPlan | None
) -> FeedbackReport | None:
    title = "Devolutiva familiar — DEMO"
    report = FeedbackReport.query.filter_by(patient_id=patient.id, title=title).first()
    if report is not None:
        return report

    completed_at = _dt(date(2026, 6, 10), 17, 0)
    report = FeedbackReport(
        patient_id=patient.id,
        professional_id=pro.id,
        assessment_plan_id=plan.id if plan else None,
        title=title,
        status="completed",
        feedback_date=date(2026, 6, 10),
        summary=(
            "DEMONSTRAÇÃO — devolutiva fictícia à família. "
            "Destacam-se potencialidades (participação, interesse visual e "
            "persistência com orientação) e áreas a apoiar (leitura prolongada "
            "e organização da atenção). Sem pretensão diagnóstica."
        ),
        reason_for_assessment=(
            "Apoiar compreensão da aprendizagem escolar e estratégias de suporte."
        ),
        history_summary=(
            "Histórico escolar ilustrativo com boa participação e necessidade "
            "de pausas em tarefas longas (dados fictícios)."
        ),
        assessment_summary=(
            "Observações e indicadores demonstrativos sugerem benefícios de "
            "materiais curtos, apoio visual e rotinas de atenção guiada."
        ),
        strengths=(
            "Interesse visual; colaboração; persistência com orientação clara; "
            "motivação em atividades lúdicas estruturadas."
        ),
        difficulties=(
            "Cansaço em leitura prolongada; necessidade de redirecionamento "
            "pontual em ambientes com muitos estímulos."
        ),
        resources_and_strategies=(
            "Segmentar instruções; pausas curtas; apoio visual; leitura "
            "compartilhada com textos adequados ao ritmo."
        ),
        preserved_areas="Compreensão oral aparente; participação social em sessão.",
        interests="Artes visuais, jogos de construção, histórias ilustradas.",
        professional_conclusion=(
            "Conclusão prudente e meramente ilustrativa: recomenda-se plano de "
            "apoio à leitura e organização da atenção, com revisão periódica. "
            "Não constitui diagnóstico."
        ),
        recommendations=(
            "Continuidade de sessões de intervenção educativa; articulação "
            "com escola; eventual parecer complementar em fonoaudiologia "
            "se a família e a escola considerarem útil."
        ),
        family_guidance=(
            "Privilegiar rotinas previsíveis, leitura compartilhada curta e "
            "reforço positivo das estratégias que já funcionam em casa."
        ),
        school_guidance=(
            "Preferir instruções segmentadas, tempo estendido em tarefas "
            "escritas longas e materiais com suporte visual."
        ),
        learning_strategies="Leitura em voz alta com pausas; checklist visual de passos.",
        suggested_adaptations="Textos mais curtos; ambientação com menos distrações.",
        referral_notes="Sugestão prudente de articulação com Fonoaudiologia (DEMO).",
        created_at=_dt(date(2026, 6, 10), 10, 0),
        updated_at=completed_at,
        completed_at=completed_at,
    )
    db.session.add(report)
    db.session.flush()
    return report


def _ensure_intervention_plan(
    pro: Professional, patient: Patient, feedback: FeedbackReport | None
) -> InterventionPlan | None:
    title = "Plano de intervenção — leitura e organização da atenção"
    plan = InterventionPlan.query.filter_by(patient_id=patient.id, title=title).first()
    if plan is not None:
        return plan

    domain_read = CognitiveDomain.query.filter_by(slug="leitura").first()
    domain_att = CognitiveDomain.query.filter_by(
        slug="atencao-funcoes-executivas"
    ).first()
    plan = InterventionPlan(
        patient_id=patient.id,
        professional_id=pro.id,
        feedback_report_id=feedback.id if feedback else None,
        title=title,
        reason=(
            "DEMONSTRAÇÃO — apoiar fluência leitora e organização da atenção "
            "com estratégias educativas (dados fictícios)."
        ),
        status="active",
        start_date=date(2026, 6, 18),
        review_date=date(2026, 8, 15),
        general_goal=(
            "Fortalecer estratégias de leitura e atenção sustentada em "
            "tarefas guiadas, valorizando potencialidades observadas."
        ),
        notes=f"DEMONSTRAÇÃO {PORTFOLIO_MARKER}",
        created_at=_dt(date(2026, 6, 18)),
        updated_at=_dt(date(2026, 6, 18)),
    )
    db.session.add(plan)
    db.session.flush()

    goal_read = InterventionGoal(
        intervention_plan_id=plan.id,
        domain_id=domain_read.id if domain_read else None,
        title="Ampliar tolerância a textos curtos com apoio visual",
        description="DEMONSTRAÇÃO — objetivo educativo fictício.",
        develop_what="Estratégias de leitura compartilhada e auto-monitoramento.",
        how_observed="Em sessão, com textos de 1–2 parágrafos e checklist visual.",
        context_notes="Consultório / sala de apoio (DEMO).",
        how_know_progress="Maior persistência e menos pedidos de abandono da tarefa.",
        review_deadline=date(2026, 8, 15),
        priority="alta",
        baseline_notes="Cansaço precoce em textos longos (observação DEMO).",
        success_criteria="Completar 2 textos curtos com 1 pausa planeada.",
        status="active",
        sort_order=1,
    )
    goal_att = InterventionGoal(
        intervention_plan_id=plan.id,
        domain_id=domain_att.id if domain_att else None,
        title="Organizar atenção em tarefas de 10–15 minutos",
        description="DEMONSTRAÇÃO — objetivo educativo fictício.",
        develop_what="Uso de timer visual e instruções segmentadas.",
        how_observed="Durante atividades guiadas em sessão.",
        how_know_progress="Redução de redirecionamentos necessários.",
        review_deadline=date(2026, 8, 15),
        priority="média",
        status="active",
        sort_order=2,
    )
    db.session.add_all([goal_read, goal_att])
    db.session.flush()

    db.session.add(
        InterventionStrategy(
            intervention_goal_id=goal_read.id,
            name="Leitura compartilhada com apoio visual",
            description="Textos curtos, apontar linha a linha, pausas planeadas.",
            frequency="2x/semana em sessão",
            materials="Textos ilustrados curtos; marcador de linha",
            context="Sessão individual",
            notes="DEMONSTRAÇÃO",
            sort_order=1,
        )
    )
    db.session.add(
        InterventionStrategy(
            intervention_goal_id=goal_att.id,
            name="Timer visual e checklist de passos",
            description="Segmentar a tarefa em 3 passos com reforço positivo.",
            frequency="em cada sessão de intervenção",
            materials="Timer visual; checklist impresso",
            context="Sessão individual",
            notes="DEMONSTRAÇÃO",
            sort_order=1,
        )
    )
    return plan


def _ensure_intervention_sessions(
    pro: Professional, patient: Patient, plan: InterventionPlan | None
) -> None:
    dates = [date(2026, 7, 2), date(2026, 7, 16), date(2026, 7, 30)]
    for idx, session_date in enumerate(dates, start=1):
        exists = ProfessionalSession.query.filter_by(
            patient_id=patient.id,
            session_date=session_date,
            session_type="intervention",
        ).first()
        if exists:
            continue
        db.session.add(
            ProfessionalSession(
                patient_id=patient.id,
                professional_id=pro.id,
                intervention_plan_id=plan.id if plan else None,
                session_date=session_date,
                start_time="15:00",
                end_time="15:50",
                session_type="intervention",
                status="completed",
                objective=f"Sessão de intervenção #{idx} — leitura e atenção (DEMO)",
                summary=(
                    f"DEMONSTRAÇÃO — sessão {idx}: trabalhou-se leitura curta e "
                    "organização da atenção com timer visual. Evolução qualitativa "
                    "positiva em engajamento."
                ),
                professional_notes=(
                    "Boa resposta a pausas planeadas; manteve colaboração. "
                    "Dificuldade residual em textos sem apoio visual (fictício)."
                ),
                strengths_observed="Persistência com orientação; humor colaborativo.",
                difficulties_observed="Distração pontual sem suporte visual.",
                facilitating_strategies="Checklist; timer; reforço positivo.",
                next_steps="Manter textos curtos e aumentar gradualmente a duração.",
                participants="paciente",
                created_at=_dt(session_date, 15, 0),
                updated_at=_dt(session_date, 15, 50),
            )
        )


def _ensure_progress_note(
    pro: Professional, patient: Patient, plan: InterventionPlan | None
) -> None:
    marker = "PORTFOLIO_DEMO_V2 progresso"
    existing = (
        ProgressNote.query.filter_by(patient_id=patient.id)
        .filter(ProgressNote.summary.ilike(f"%{marker}%"))
        .first()
    )
    if existing:
        return
    # Evitar duplicar por data aproximada
    day = date(2026, 8, 5)
    existing_day = (
        ProgressNote.query.filter_by(patient_id=patient.id)
        .filter(ProgressNote.recorded_at >= _dt(day, 0, 0))
        .filter(ProgressNote.recorded_at <= _dt(day, 23, 59))
        .first()
    )
    if existing_day:
        return

    db.session.add(
        ProgressNote(
            patient_id=patient.id,
            professional_id=pro.id,
            intervention_plan_id=plan.id if plan else None,
            recorded_at=_dt(day, 16, 0),
            progress_status="progress",
            summary=(
                f"DEMONSTRAÇÃO — {marker}: evolução qualitativa positiva. "
                "Maior persistência em textos curtos e uso espontâneo do "
                "checklist visual. Potencialidades: motivação, interesse visual "
                "e colaboração familiar."
            ),
            evidence=(
                "Completou duas atividades de leitura com uma pausa planeada; "
                "menos pedidos de abandono da tarefa (registo fictício)."
            ),
            professional_interpretation=(
                "Interpretação prudente e ilustrativa: as estratégias parecem "
                "facilitar a organização da atenção. Sem valor diagnóstico."
            ),
            next_step="Revisão do plano prevista para meados de agosto/2026.",
        )
    )


def _ensure_referral_and_school(pro: Professional, patient: Patient) -> None:
    referral = (
        Referral.query.filter_by(patient_id=patient.id, specialty="Fonoaudiologia")
        .filter(Referral.notes.ilike(f"%{PORTFOLIO_MARKER}%"))
        .first()
    )
    if referral is None:
        # Evitar duplicar encaminhamento genérico DEMO
        referral = Referral.query.filter_by(
            patient_id=patient.id, specialty="Fonoaudiologia"
        ).first()
    if referral is None:
        db.session.add(
            Referral(
                patient_id=patient.id,
                professional_id=pro.id,
                referral_date=date(2026, 5, 20),
                specialty="Fonoaudiologia",
                reason=(
                    "DEMONSTRAÇÃO — sugestão prudente de articulação multiprofissional "
                    "para apoio à linguagem oral/escrita, sem pretensão diagnóstica."
                ),
                status="suggested",
                professional_or_service="Serviço de Fonoaudiologia (fictício)",
                notes=f"DEMONSTRAÇÃO — encaminhamento pendente ({PORTFOLIO_MARKER}).",
                created_at=_dt(date(2026, 5, 20)),
                updated_at=_dt(date(2026, 5, 20)),
            )
        )

    school = SchoolContact.query.filter_by(
        patient_id=patient.id, contact_date=date(2026, 5, 22)
    ).first()
    if school is None:
        db.session.add(
            SchoolContact(
                patient_id=patient.id,
                professional_id=pro.id,
                contact_date=date(2026, 5, 22),
                school_name="Escola Municipal Demonstração",
                contact_person="Prof.ª Carla Oliveira",
                role="Professora titular",
                purpose="Alinhamento de estratégias de apoio em sala (DEMO)",
                summary=(
                    "DEMONSTRAÇÃO — contacto escolar fictício em maio/2026. "
                    "Partilha de estratégias de instrução segmentada e apoio visual."
                ),
                recommendations=(
                    "Preferir textos curtos; permitir pausas; reforçar potencialidades."
                ),
                notes=f"DEMONSTRAÇÃO {PORTFOLIO_MARKER}",
                created_at=_dt(date(2026, 5, 22)),
            )
        )


def _ensure_document(pro: Professional, patient: Patient) -> None:
    title = "Consentimento demonstrativo — DEMO-001"
    existing = PatientDocument.query.filter_by(
        patient_id=patient.id, title=title
    ).first()
    if existing:
        return
    db.session.add(
        PatientDocument(
            patient_id=patient.id,
            professional_id=pro.id,
            document_type="consent",
            title=title,
            description=(
                "DEMONSTRAÇÃO — metadado de consentimento fictício para portfólio. "
                "Não constitui documento jurídico real."
            ),
            status="registered",
            recorded_at=date(2026, 3, 10),
            notes=f"DEMONSTRAÇÃO {PORTFOLIO_MARKER}",
            created_at=_dt(date(2026, 3, 10)),
        )
    )


def _ensure_seed_history(pro: Professional, patient: Patient) -> None:
    existing = PatientHistoryEntry.query.filter_by(
        patient_id=patient.id, title=SEED_HISTORY_TITLE
    ).first()
    if existing:
        return
    db.session.add(
        PatientHistoryEntry(
            patient_id=patient.id,
            professional_id=pro.id,
            category="geral",
            title=SEED_HISTORY_TITLE,
            content=(
                "Marcador de seed idempotente PORTFOLIO_DEMO_V2. "
                "Indica que a jornada profissional demonstrativa completa "
                "(anamnese → avaliação → devolutiva → intervenção → evolução) "
                "foi garantida com dados fictícios para portfólio. "
                "Não corresponde a pessoa real nem a caso clínico."
            ),
            recorded_at=_dt(date(2026, 3, 12), 9, 0),
        )
    )


def _seed_demo001_journey(pro: Professional, patient: Patient) -> dict:
    """Preenche peças em falta da jornada DEMO-001. Retorna resumo."""
    summary: dict[str, str] = {}
    anamnesis = _ensure_anamnesis(pro, patient)
    summary["anamnesis"] = "ok" if anamnesis else "skipped"
    plan = _ensure_assessment_plan(pro, patient)
    summary["assessment_plan"] = "ok" if plan else "skipped"
    _ensure_assessment_sessions(pro, patient, plan)
    summary["assessment_sessions"] = "ok"
    assessment = _ensure_may_assessment(pro, patient)
    summary["assessment"] = "ok" if assessment else "skipped"
    feedback = _ensure_feedback(pro, patient, plan)
    summary["feedback"] = "ok" if feedback else "skipped"
    intervention = _ensure_intervention_plan(pro, patient, feedback)
    summary["intervention_plan"] = "ok" if intervention else "skipped"
    _ensure_intervention_sessions(pro, patient, intervention)
    summary["intervention_sessions"] = "ok"
    _ensure_progress_note(pro, patient, intervention)
    summary["progress_note"] = "ok"
    _ensure_referral_and_school(pro, patient)
    summary["referral_school"] = "ok"
    _ensure_document(pro, patient)
    summary["document"] = "ok"
    _ensure_seed_history(pro, patient)
    summary["history_marker"] = "ok"
    return summary


def _ensure_other_demo_patients(pro: Professional) -> list[str]:
    """Cria DEMO-002…DEMO-008 se em falta. Retorna códigos criados/atualizados."""
    touched: list[str] = []

    # DEMO-002 — anamnese draft
    p2, created = _get_or_create_patient(
        pro,
        code="DEMO-002",
        name="Rafael Okada",
        birth_date=date(2018, 6, 20),
        sex="masculino",
        education_level="3º ano",
    )
    _ensure_guardian(
        p2,
        name="Yuki Okada",
        phone="+351 910 000 002",
        email="yuki.okada@example.invalid",
    )
    if (
        PatientAnamnesis.query.filter_by(patient_id=p2.id).first() is None
    ):
        template = AnamnesisTemplate.query.filter_by(
            slug="anamnese-neuroeducacional-v2", is_active=True
        ).first() or AnamnesisTemplate.query.filter_by(is_active=True).first()
        if template:
            db.session.add(
                PatientAnamnesis(
                    patient_id=p2.id,
                    template_id=template.id,
                    professional_id=pro.id,
                    started_at=_dt(date(2026, 4, 2)),
                    status="draft",
                    notes="DEMONSTRAÇÃO — anamnese em rascunho (fictício).",
                )
            )
    touched.append("DEMO-002" + (" (novo)" if created else ""))

    # DEMO-003 — assessment draft
    p3, created = _get_or_create_patient(
        pro,
        code="DEMO-003",
        name="Sofia Albuquerque",
        birth_date=date(2012, 1, 8),
        sex="feminino",
        education_level="9º ano",
    )
    _ensure_guardian(
        p3,
        name="Marina Albuquerque",
        phone="+351 910 000 003",
        email="marina.albuquerque@example.invalid",
    )
    if Assessment.query.filter_by(patient_id=p3.id).first() is None:
        db.session.add(
            Assessment(
                patient_id=p3.id,
                professional_id=pro.id,
                assessment_date=date(2026, 5, 5),
                reason="Avaliação demonstrativa em rascunho — DEMO-003",
                status="draft",
                general_notes="DEMONSTRAÇÃO — rascunho fictício.",
            )
        )
    touched.append("DEMO-003" + (" (novo)" if created else ""))

    # DEMO-004 — one completed session
    p4, created = _get_or_create_patient(
        pro,
        code="DEMO-004",
        name="Miguel Torres",
        birth_date=date(2015, 9, 12),
        sex="masculino",
        education_level="6º ano",
    )
    _ensure_guardian(
        p4,
        name="Paula Torres",
        phone="+351 910 000 004",
        email="paula.torres@example.invalid",
    )
    if ProfessionalSession.query.filter_by(patient_id=p4.id).first() is None:
        db.session.add(
            ProfessionalSession(
                patient_id=p4.id,
                professional_id=pro.id,
                session_date=date(2026, 4, 15),
                session_type="initial",
                status="completed",
                objective="Sessão inicial demonstrativa — DEMO-004",
                summary=(
                    "DEMONSTRAÇÃO — primeiro contacto fictício. "
                    "Observaram-se potencialidades de participação e "
                    "dificuldades pontuais de organização."
                ),
                strengths_observed="Colaboração e curiosidade.",
                difficulties_observed="Organização de materiais.",
                professional_notes="DEMONSTRAÇÃO — notas fictícias.",
            )
        )
    touched.append("DEMO-004" + (" (novo)" if created else ""))

    # DEMO-005 — empty-ish
    p5, created = _get_or_create_patient(
        pro,
        code="DEMO-005",
        name="Beatriz Nogueira",
        birth_date=date(2019, 11, 3),
        sex="feminino",
        education_level="2º ano",
    )
    _ensure_guardian(
        p5,
        name="André Nogueira",
        relationship="pai",
        phone="+351 910 000 005",
        email="andre.nogueira@example.invalid",
    )
    touched.append("DEMO-005" + (" (novo)" if created else ""))

    # DEMO-006 — referral only
    p6, created = _get_or_create_patient(
        pro,
        code="DEMO-006",
        name="Thiago Vasconcelos",
        birth_date=date(2010, 4, 25),
        sex="masculino",
        education_level="Ensino médio",
        is_minor=True,
    )
    _ensure_guardian(
        p6,
        name="Lucia Vasconcelos",
        phone="+351 910 000 006",
        email="lucia.vasconcelos@example.invalid",
    )
    if Referral.query.filter_by(patient_id=p6.id).first() is None:
        db.session.add(
            Referral(
                patient_id=p6.id,
                professional_id=pro.id,
                referral_date=date(2026, 6, 1),
                specialty="Psicologia",
                reason="DEMONSTRAÇÃO — encaminhamento fictício apenas.",
                status="suggested",
                notes="DEMONSTRAÇÃO — dados fictícios.",
            )
        )
    touched.append("DEMO-006" + (" (novo)" if created else ""))

    # DEMO-007 — inactive
    p7, created = _get_or_create_patient(
        pro,
        code="DEMO-007",
        name="Camila Prado",
        birth_date=date(2017, 2, 14),
        sex="feminino",
        education_level="4º ano",
        status="inativo",
    )
    p7.status = "inativo"
    _ensure_guardian(
        p7,
        name="Renata Prado",
        phone="+351 910 000 007",
        email="renata.prado@example.invalid",
    )
    touched.append("DEMO-007" + (" (novo)" if created else ""))

    # DEMO-008 — assessment completed light
    p8, created = _get_or_create_patient(
        pro,
        code="DEMO-008",
        name="Enzo Barreto",
        birth_date=date(2014, 7, 30),
        sex="masculino",
        education_level="7º ano",
    )
    _ensure_guardian(
        p8,
        name="Fernanda Barreto",
        phone="+351 910 000 008",
        email="fernanda.barreto@example.invalid",
    )
    if (
        Assessment.query.filter_by(patient_id=p8.id, status="completed").first()
        is None
    ):
        completed_at = _dt(date(2026, 5, 28), 15, 0)
        assessment = Assessment(
            patient_id=p8.id,
            professional_id=pro.id,
            assessment_date=date(2026, 5, 28),
            reason="Avaliação leve demonstrativa — DEMO-008",
            status="completed",
            general_notes="DEMONSTRAÇÃO — avaliação completa leve e fictícia.",
            completed_at=completed_at,
        )
        db.session.add(assessment)
        db.session.flush()
        instrument = Instrument.query.filter_by(slug="stroop").first() or (
            Instrument.query.filter_by(is_active=True).first()
        )
        if instrument:
            ai = AssessmentInstrument(
                assessment_id=assessment.id,
                instrument_id=instrument.id,
                instrument_name=instrument.name,
                instrument_short_name=instrument.short_name,
                status="completed",
                professional_interpretation="DEMONSTRAÇÃO — interpretação fictícia.",
                completed_at=completed_at,
            )
            db.session.add(ai)
            db.session.flush()
            db.session.add(
                AssessmentResult(
                    assessment_instrument_id=ai.id,
                    metric_name="indicador demo",
                    raw_value="demo",
                    interpretation="DEMONSTRAÇÃO — valor fictício.",
                    source="professional",
                    sort_order=0,
                )
            )
    touched.append("DEMO-008" + (" (novo)" if created else ""))

    # Marcar P-0248 / P-0312 se existirem
    for code in ("P-0248", "P-0312"):
        legacy = Patient.query.filter_by(
            professional_id=pro.id, internal_code=code
        ).first()
        if legacy and "DEMONSTRAÇÃO" not in (legacy.notes or ""):
            legacy.notes = DEMO_NOTES

    return touched


def ensure_portfolio_demo() -> None:
    """Ensures demo professional journey data. Safe to call repeatedly."""
    pro = Professional.query.filter_by(email="demo@neurolearn.local").first()
    if pro is None:
        return

    # Alinhar preferências da conta demo sem resetar password.
    if not pro.preferred_subject_term:
        pro.preferred_subject_term = "learner"
    if pro.onboarding_completed is None or pro.onboarding_completed is False:
        # Manter True para conta demo de portfólio
        if pro.email == "demo@neurolearn.local":
            pro.onboarding_completed = True

    patient = _ensure_demo001_patient(pro)

    if _demo001_journey_complete(patient):
        _ensure_other_demo_patients(pro)
        db.session.commit()
        return

    _seed_demo001_journey(pro, patient)
    _ensure_other_demo_patients(pro)
    db.session.commit()
