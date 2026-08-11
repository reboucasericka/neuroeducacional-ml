"""
Seed demonstrativo (dados 100% fictícios).
"""

from __future__ import annotations

from datetime import date, timedelta

from src.platform.anamnesis_seed import ensure_anamnesis_templates
from src.platform.cognitive_seed import (
    ensure_cognitive_catalog,
    ensure_demo_cognitive_patient,
)
from src.platform.extensions import db
from src.platform.instruments_seed import ensure_instrument_catalog
from src.platform.models import (
    Patient,
    PatientGuardian,
    PatientHistoryEntry,
    Professional,
)


def seed_demo_data() -> None:
    """Cria profissional/pacientes se necessário e garante catálogos.

    Conta demo: DEVELOPMENT / DEMO ONLY. Pode ser desativada via
    NEUROLEARN_SEED_DEMO=0 (a app chama ensure_* em alternativa).

    Migração de tipo: contas antigas com ``psicologo`` são normalizadas
    para ``clinical_neuropsychopedagogue`` em ``ensure_schema``.
    """
    pro = Professional.query.filter_by(email="demo@neurolearn.local").first()
    if pro is not None:
        # Compatibilidade: não perder conta demo; alinhar tipo se legado
        from src.platform.terminology import normalize_professional_type

        normalized = normalize_professional_type(pro.professional_type)
        if pro.professional_type != normalized:
            pro.professional_type = normalized
        if not pro.preferred_subject_term:
            pro.preferred_subject_term = "patient"
        if pro.onboarding_completed is None:
            pro.onboarding_completed = True
        # Corrigir nomes demo legados "Paciente Demonstração *"
        for p in Patient.query.filter_by(professional_id=pro.id).all():
            if p.name == "Paciente Demonstração A":
                p.name = "Aprendente Demonstração A"
            elif p.name == "Paciente Demonstração B":
                p.name = "Aprendente Demonstração B"
        db.session.commit()

    if pro is None:
        pro = Professional(
            name="Dra. Ana Demonstração",
            email="demo@neurolearn.local",
            professional_type="clinical_neuropsychopedagogue",
            registration_number="REG-DEMO-000",
            education="Neuropsicopedagogia",
            specialization="Neuropsicopedagogia Clínica",
            workplace="Consultório Demonstração",
            city="São Paulo",
            state="SP",
            preferred_subject_term="patient",
            onboarding_completed=True,
            is_active=True,
        )
        pro.set_password("Demo@12345")
        db.session.add(pro)
        db.session.flush()

        minor = Patient(
            professional_id=pro.id,
            internal_code="P-0248",
            name="Aprendente Demonstração A",
            birth_date=date.today() - timedelta(days=365 * 12 + 40),
            sex="feminino",
            gender=None,
            education_level="6º ano",
            is_minor=True,
            status="ativo",
            notes="DEMONSTRAÇÃO — dados fictícios.",
        )
        adult = Patient(
            professional_id=pro.id,
            internal_code="P-0312",
            name="Aprendente Demonstração B",
            birth_date=date.today() - timedelta(days=365 * 28 + 10),
            sex="masculino",
            education_level="Ensino superior",
            occupation="Estudante",
            contact_email="demo.paciente.b@example.invalid",
            is_minor=False,
            status="ativo",
            notes="DEMONSTRAÇÃO — dados fictícios.",
        )
        db.session.add_all([minor, adult])
        db.session.flush()

        db.session.add(
            PatientGuardian(
                patient_id=minor.id,
                name="Responsável Demonstração",
                relationship="mãe",
                phone="+351 900 000 000",
                email="responsavel.demo@example.invalid",
                is_primary=True,
            )
        )
        db.session.add(
            PatientHistoryEntry(
                patient_id=minor.id,
                professional_id=pro.id,
                category="escolar",
                title="Entrada demonstrativa de histórico",
                content="Registo fictício para ilustrar o prontuário longitudinal.",
            )
        )
        db.session.commit()

    ensure_anamnesis_templates()
    ensure_instrument_catalog()
    ensure_cognitive_catalog()
    ensure_demo_cognitive_patient()
