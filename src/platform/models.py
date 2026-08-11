"""
Modelos da plataforma profissional (Versão estrutural inicial).

Camada clínica/profissional separada do pipeline de Data Science sintético.
Não implementa diagnóstico automático nem scoring clínico.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from src.platform.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Professional(UserMixin, db.Model):
    __tablename__ = "professionals"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # Valores: clinical_neuropsychopedagogue | institutional_neuropsychopedagogue | psychopedagogue
    professional_type = db.Column(
        db.String(80), nullable=False, default="clinical_neuropsychopedagogue"
    )
    registration_number = db.Column(db.String(80), nullable=True)
    education = db.Column(db.String(255), nullable=True)
    specialization = db.Column(db.String(255), nullable=True)
    workplace = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(40), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    state = db.Column(db.String(80), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    # patient | learner | evaluatee — só UI; model Patient permanece
    preferred_subject_term = db.Column(db.String(40), nullable=True)
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    patients = db.relationship("Patient", back_populates="professional", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def __repr__(self) -> str:
        return f"<Professional {self.email}>"


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    internal_code = db.Column(db.String(40), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    sex = db.Column(db.String(30), nullable=False, default="nao_informado")
    gender = db.Column(db.String(60), nullable=True)
    education_level = db.Column(db.String(80), nullable=True)
    occupation = db.Column(db.String(120), nullable=True)
    contact_phone = db.Column(db.String(40), nullable=True)
    contact_email = db.Column(db.String(255), nullable=True)
    is_minor = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(40), nullable=False, default="ativo")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    professional = db.relationship("Professional", back_populates="patients")
    guardians = db.relationship(
        "PatientGuardian",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    history_entries = db.relationship(
        "PatientHistoryEntry",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    anamneses = db.relationship(
        "PatientAnamnesis",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    assessments = db.relationship(
        "Assessment",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    cognitive_indicators = db.relationship(
        "CognitiveIndicator",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        db.UniqueConstraint(
            "professional_id", "internal_code", name="uq_patient_code_per_professional"
        ),
    )

    @property
    def age_years(self) -> int | None:
        if not self.birth_date:
            return None
        today = date.today()
        years = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return years

    def __repr__(self) -> str:
        return f"<Patient {self.internal_code}>"


class PatientGuardian(db.Model):
    __tablename__ = "patient_guardians"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    relationship = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    is_primary = db.Column(db.Boolean, nullable=False, default=True)

    patient = db.relationship("Patient", back_populates="guardians")


class PatientHistoryEntry(db.Model):
    __tablename__ = "patient_history_entries"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey("professionals.id"), nullable=False)
    category = db.Column(db.String(60), nullable=False, default="geral")
    title = db.Column(db.String(160), nullable=False)
    content = db.Column(db.Text, nullable=False)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    patient = db.relationship("Patient", back_populates="history_entries")


class AnamnesisTemplate(db.Model):
    __tablename__ = "anamnesis_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False, default="geral")
    target_population = db.Column(db.String(80), nullable=True)
    description = db.Column(db.Text, nullable=True)
    # JSON opcional: lista de professional_type; vazio = aplicável a todos
    applicable_professional_types = db.Column(db.Text, nullable=True)
    # clinical | institutional | psychopedagogical (opcional)
    practice_context = db.Column(db.String(40), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    fields = db.relationship(
        "AnamnesisField",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class AnamnesisField(db.Model):
    __tablename__ = "anamnesis_fields"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer, db.ForeignKey("anamnesis_templates.id"), nullable=False
    )
    section = db.Column(db.String(120), nullable=False, default="Geral")
    label = db.Column(db.String(255), nullable=False)
    help_text = db.Column(db.Text, nullable=True)
    field_type = db.Column(db.String(40), nullable=False, default="text")
    options_json = db.Column(db.Text, nullable=True)
    placeholder = db.Column(db.String(255), nullable=True)
    is_required = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    template = db.relationship("AnamnesisTemplate", back_populates="fields")


class PatientAnamnesis(db.Model):
    __tablename__ = "patient_anamneses"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True
    )
    template_id = db.Column(
        db.Integer, db.ForeignKey("anamnesis_templates.id"), nullable=False
    )
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="draft", index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    patient = db.relationship("Patient", back_populates="anamneses")
    template = db.relationship("AnamnesisTemplate")
    professional = db.relationship("Professional")
    responses = db.relationship(
        "PatientAnamnesisResponse",
        back_populates="patient_anamnesis",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class PatientAnamnesisResponse(db.Model):
    __tablename__ = "patient_anamnesis_responses"

    id = db.Column(db.Integer, primary_key=True)
    patient_anamnesis_id = db.Column(
        db.Integer, db.ForeignKey("patient_anamneses.id"), nullable=False
    )
    field_id = db.Column(db.Integer, db.ForeignKey("anamnesis_fields.id"), nullable=False)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    patient_anamnesis = db.relationship("PatientAnamnesis", back_populates="responses")
    field = db.relationship("AnamnesisField")

    def touch(self) -> None:
        self.updated_at = utcnow()


class Instrument(db.Model):
    __tablename__ = "instruments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    short_name = db.Column(db.String(40), nullable=True)
    slug = db.Column(db.String(160), unique=True, nullable=True, index=True)
    category = db.Column(db.String(80), nullable=False, default="Outros")
    description = db.Column(db.Text, nullable=True)
    target_population = db.Column(db.String(80), nullable=True)
    minimum_age = db.Column(db.Integer, nullable=True)
    maximum_age = db.Column(db.Integer, nullable=True)
    purpose = db.Column(db.String(255), nullable=True)
    license_status = db.Column(db.String(80), nullable=False, default="unknown")
    copyright_status = db.Column(db.String(80), nullable=False, default="unknown")
    digital_use_status = db.Column(db.String(80), nullable=False, default="verify")
    license_notes = db.Column(db.Text, nullable=True)
    official_source = db.Column(db.String(255), nullable=True)
    last_verified_at = db.Column(db.DateTime, nullable=True)
    reference = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    professional_scopes = db.relationship(
        "InstrumentProfessionalScope",
        back_populates="instrument",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class InstrumentProfessionalScope(db.Model):
    """Escopo de uso por tipo profissional — separado de licença/digitalização."""

    __tablename__ = "instrument_professional_scopes"

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(
        db.Integer, db.ForeignKey("instruments.id"), nullable=False, index=True
    )
    professional_type = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="verify")
    notes = db.Column(db.Text, nullable=True)
    source_reference = db.Column(db.String(255), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)

    instrument = db.relationship("Instrument", back_populates="professional_scopes")

    __table_args__ = (
        db.UniqueConstraint(
            "instrument_id",
            "professional_type",
            name="uq_instrument_professional_scope",
        ),
    )


class Assessment(db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(
        db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True
    )
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    assessment_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    reason = db.Column(db.String(255), nullable=True)
    # initial | follow_up | reevaluation
    assessment_type = db.Column(db.String(40), nullable=False, default="initial")
    status = db.Column(db.String(40), nullable=False, default="draft", index=True)
    general_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    patient = db.relationship("Patient", back_populates="assessments")
    professional = db.relationship("Professional")
    instruments = db.relationship(
        "AssessmentInstrument",
        back_populates="assessment",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class AssessmentInstrument(db.Model):
    __tablename__ = "assessment_instruments"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=False)
    instrument_id = db.Column(db.Integer, db.ForeignKey("instruments.id"), nullable=False)
    # Snapshot para preservar histórico se o catálogo mudar.
    instrument_name = db.Column(db.String(160), nullable=True)
    instrument_short_name = db.Column(db.String(40), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="pending")
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    raw_score = db.Column(db.Float, nullable=True)
    standard_score = db.Column(db.Float, nullable=True)
    classification = db.Column(db.String(120), nullable=True)
    professional_interpretation = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    assessment = db.relationship("Assessment", back_populates="instruments")
    instrument = db.relationship("Instrument")
    results = db.relationship(
        "AssessmentResult",
        back_populates="assessment_instrument",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()

    @property
    def display_name(self) -> str:
        return self.instrument_name or (
            self.instrument.name if self.instrument else "Instrumento"
        )

    @property
    def display_short_name(self) -> str | None:
        if self.instrument_short_name:
            return self.instrument_short_name
        return self.instrument.short_name if self.instrument else None


class AssessmentResult(db.Model):
    __tablename__ = "assessment_results"

    id = db.Column(db.Integer, primary_key=True)
    assessment_instrument_id = db.Column(
        db.Integer, db.ForeignKey("assessment_instruments.id"), nullable=False
    )
    metric_name = db.Column(db.String(120), nullable=False)
    raw_value = db.Column(db.String(120), nullable=True)
    normalized_value = db.Column(db.String(120), nullable=True)
    unit = db.Column(db.String(40), nullable=True)
    interpretation = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(80), nullable=False, default="professional")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    assessment_instrument = db.relationship(
        "AssessmentInstrument", back_populates="results"
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class CognitiveDomain(db.Model):
    __tablename__ = "cognitive_domains"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    skills = db.relationship(
        "CognitiveSkill",
        back_populates="domain",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class CognitiveSkill(db.Model):
    __tablename__ = "cognitive_skills"

    id = db.Column(db.Integer, primary_key=True)
    domain_id = db.Column(
        db.Integer, db.ForeignKey("cognitive_domains.id"), nullable=False, index=True
    )
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(160), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    domain = db.relationship("CognitiveDomain", back_populates="skills")

    __table_args__ = (
        db.UniqueConstraint("domain_id", "slug", name="uq_skill_slug_per_domain"),
    )


class InstrumentSkillMapping(db.Model):
    """Associação configurável instrumento → domínio/habilidade (catálogo)."""

    __tablename__ = "instrument_skill_mappings"

    id = db.Column(db.Integer, primary_key=True)
    instrument_id = db.Column(
        db.Integer, db.ForeignKey("instruments.id"), nullable=False, index=True
    )
    domain_id = db.Column(
        db.Integer, db.ForeignKey("cognitive_domains.id"), nullable=False
    )
    skill_id = db.Column(db.Integer, db.ForeignKey("cognitive_skills.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    instrument = db.relationship("Instrument")
    domain = db.relationship("CognitiveDomain")
    skill = db.relationship("CognitiveSkill")


class CognitiveIndicator(db.Model):
    """Indicador no perfil cognitivo — rastreável até avaliação/resultado."""

    __tablename__ = "cognitive_indicators"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=True)
    assessment_instrument_id = db.Column(
        db.Integer, db.ForeignKey("assessment_instruments.id"), nullable=True
    )
    assessment_result_id = db.Column(
        db.Integer, db.ForeignKey("assessment_results.id"), nullable=True
    )
    domain_id = db.Column(
        db.Integer, db.ForeignKey("cognitive_domains.id"), nullable=False, index=True
    )
    skill_id = db.Column(db.Integer, db.ForeignKey("cognitive_skills.id"), nullable=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    label = db.Column(db.String(160), nullable=False)
    value_numeric = db.Column(db.Float, nullable=True)
    value_text = db.Column(db.String(255), nullable=True)
    unit = db.Column(db.String(40), nullable=True)
    interpretation = db.Column(db.Text, nullable=True)
    source_type = db.Column(db.String(40), nullable=False, default="manual_entry")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    patient = db.relationship("Patient", back_populates="cognitive_indicators")
    professional = db.relationship("Professional")
    assessment = db.relationship("Assessment")
    assessment_instrument = db.relationship("AssessmentInstrument")
    assessment_result = db.relationship("AssessmentResult")
    domain = db.relationship("CognitiveDomain")
    skill = db.relationship("CognitiveSkill")

    def touch(self) -> None:
        self.updated_at = utcnow()


class AssessmentPlan(db.Model):
    __tablename__ = "assessment_plans"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    objectives = db.Column(db.Text, nullable=True)
    initial_hypotheses = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="draft")
    planned_start_date = db.Column(db.Date, nullable=True)
    planned_end_date = db.Column(db.Date, nullable=True)
    estimated_sessions = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")
    plan_objectives = db.relationship(
        "AssessmentPlanObjective",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class AssessmentPlanObjective(db.Model):
    __tablename__ = "assessment_plan_objectives"

    id = db.Column(db.Integer, primary_key=True)
    assessment_plan_id = db.Column(
        db.Integer, db.ForeignKey("assessment_plans.id"), nullable=False, index=True
    )
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    domain_id = db.Column(db.Integer, db.ForeignKey("cognitive_domains.id"), nullable=True)
    priority = db.Column(db.String(40), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="open")
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    plan = db.relationship("AssessmentPlan", back_populates="plan_objectives")
    domain = db.relationship("CognitiveDomain")


class ProfessionalSession(db.Model):
    __tablename__ = "professional_sessions"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    assessment_plan_id = db.Column(
        db.Integer, db.ForeignKey("assessment_plans.id"), nullable=True
    )
    intervention_plan_id = db.Column(
        db.Integer, db.ForeignKey("intervention_plans.id"), nullable=True, index=True
    )
    session_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    start_time = db.Column(db.String(10), nullable=True)
    end_time = db.Column(db.String(10), nullable=True)
    session_type = db.Column(db.String(40), nullable=False, default="assessment")
    status = db.Column(db.String(40), nullable=False, default="planned", index=True)
    objective = db.Column(db.Text, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    professional_notes = db.Column(db.Text, nullable=True)
    next_steps = db.Column(db.Text, nullable=True)
    participants = db.Column(db.Text, nullable=True)
    strengths_observed = db.Column(db.Text, nullable=True)
    facilitating_strategies = db.Column(db.Text, nullable=True)
    help_level = db.Column(db.String(80), nullable=True)
    difficulties_observed = db.Column(db.Text, nullable=True)
    response_notes = db.Column(db.Text, nullable=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), nullable=True)
    assessment_instrument_id = db.Column(
        db.Integer, db.ForeignKey("assessment_instruments.id"), nullable=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")
    assessment_plan = db.relationship("AssessmentPlan")
    intervention_plan = db.relationship(
        "InterventionPlan", back_populates="sessions", foreign_keys=[intervention_plan_id]
    )
    assessment = db.relationship("Assessment")
    assessment_instrument = db.relationship("AssessmentInstrument")
    observations = db.relationship(
        "SessionObservation",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    activities = db.relationship(
        "ActivityRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    intervention_goals = db.relationship(
        "SessionInterventionGoal",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class SessionInterventionGoal(db.Model):
    """N:N — uma sessão de intervenção pode trabalhar vários objetivos."""

    __tablename__ = "session_intervention_goals"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("professional_sessions.id"), nullable=False, index=True
    )
    intervention_goal_id = db.Column(
        db.Integer, db.ForeignKey("intervention_goals.id"), nullable=False, index=True
    )
    notes = db.Column(db.Text, nullable=True)

    session = db.relationship("ProfessionalSession", back_populates="intervention_goals")
    goal = db.relationship("InterventionGoal", back_populates="session_links")

    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "intervention_goal_id",
            name="uq_session_intervention_goal",
        ),
    )

class SessionObservation(db.Model):
    __tablename__ = "session_observations"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("professional_sessions.id"), nullable=False, index=True
    )
    category = db.Column(db.String(60), nullable=False, default="other")
    label = db.Column(db.String(200), nullable=False)
    value = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    session = db.relationship("ProfessionalSession", back_populates="observations")


class ActivityRecord(db.Model):
    """Atividade não padronizada (não confundir com teste padronizado)."""

    __tablename__ = "activity_records"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("professional_sessions.id"), nullable=False, index=True
    )
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(60), nullable=False, default="outro")
    objective = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    observed_response = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    session = db.relationship("ProfessionalSession", back_populates="activities")


class Referral(db.Model):
    __tablename__ = "referrals"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    session_id = db.Column(db.Integer, db.ForeignKey("professional_sessions.id"), nullable=True)
    assessment_plan_id = db.Column(
        db.Integer, db.ForeignKey("assessment_plans.id"), nullable=True
    )
    referral_date = db.Column(db.Date, nullable=False, default=date.today)
    specialty = db.Column(db.String(120), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="suggested")
    professional_or_service = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")

    def touch(self) -> None:
        self.updated_at = utcnow()


class SchoolContact(db.Model):
    __tablename__ = "school_contacts"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    contact_date = db.Column(db.Date, nullable=False, default=date.today)
    school_name = db.Column(db.String(200), nullable=True)
    contact_person = db.Column(db.String(160), nullable=True)
    role = db.Column(db.String(120), nullable=True)
    purpose = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")


class PatientDocument(db.Model):
    """Metadados de documentos — upload de ficheiros fica para fase posterior."""

    __tablename__ = "patient_documents"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    document_type = db.Column(db.String(60), nullable=False, default="other")
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="registered")
    recorded_at = db.Column(db.Date, nullable=False, default=date.today)
    notes = db.Column(db.Text, nullable=True)
    # Preparação futura: associar devolutiva ao documento
    feedback_report_id = db.Column(
        db.Integer, db.ForeignKey("feedback_reports.id"), nullable=True, index=True
    )
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")
    feedback_report = db.relationship("FeedbackReport")


class PatientConsent(db.Model):
    """Consentimento — texto jurídico apenas demonstrativo."""

    __tablename__ = "patient_consents"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    guardian_id = db.Column(db.Integer, db.ForeignKey("patient_guardians.id"), nullable=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    consent_type = db.Column(db.String(80), nullable=False, default="assessment")
    accepted = db.Column(db.Boolean, nullable=False, default=False)
    accepted_at = db.Column(db.DateTime, nullable=True)
    revoked_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")
    guardian = db.relationship("PatientGuardian")


# ---------- Devolutiva / Intervenção / Evolução ----------


class FeedbackReport(db.Model):
    """Devolutiva escrita pelo profissional — sem diagnóstico automático."""

    __tablename__ = "feedback_reports"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    assessment_plan_id = db.Column(
        db.Integer, db.ForeignKey("assessment_plans.id"), nullable=True
    )
    title = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="draft")
    feedback_date = db.Column(db.Date, nullable=False, default=date.today)
    summary = db.Column(db.Text, nullable=True)
    reason_for_assessment = db.Column(db.Text, nullable=True)
    history_summary = db.Column(db.Text, nullable=True)
    assessment_summary = db.Column(db.Text, nullable=True)
    strengths = db.Column(db.Text, nullable=True)
    difficulties = db.Column(db.Text, nullable=True)
    resources_and_strategies = db.Column(db.Text, nullable=True)
    preserved_areas = db.Column(db.Text, nullable=True)
    interests = db.Column(db.Text, nullable=True)
    professional_conclusion = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    family_guidance = db.Column(db.Text, nullable=True)
    school_guidance = db.Column(db.Text, nullable=True)
    learning_strategies = db.Column(db.Text, nullable=True)
    suggested_adaptations = db.Column(db.Text, nullable=True)
    referral_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")
    assessment_plan = db.relationship("AssessmentPlan")

    def touch(self) -> None:
        self.updated_at = utcnow()


class InterventionPlan(db.Model):
    __tablename__ = "intervention_plans"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    feedback_report_id = db.Column(
        db.Integer, db.ForeignKey("feedback_reports.id"), nullable=True
    )
    title = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="draft")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    review_date = db.Column(db.Date, nullable=True)
    general_goal = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")
    feedback_report = db.relationship("FeedbackReport")
    goals = db.relationship(
        "InterventionGoal",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="InterventionGoal.sort_order",
    )
    sessions = db.relationship(
        "ProfessionalSession",
        back_populates="intervention_plan",
        lazy="dynamic",
        foreign_keys="ProfessionalSession.intervention_plan_id",
    )
    reviews = db.relationship(
        "InterventionPlanReview",
        back_populates="plan",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class InterventionGoal(db.Model):
    __tablename__ = "intervention_goals"

    id = db.Column(db.Integer, primary_key=True)
    intervention_plan_id = db.Column(
        db.Integer, db.ForeignKey("intervention_plans.id"), nullable=False, index=True
    )
    domain_id = db.Column(db.Integer, db.ForeignKey("cognitive_domains.id"), nullable=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("cognitive_skills.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Orientação SMART (preenchida pelo profissional, sem gerador)
    develop_what = db.Column(db.Text, nullable=True)
    how_observed = db.Column(db.Text, nullable=True)
    context_notes = db.Column(db.Text, nullable=True)
    how_know_progress = db.Column(db.Text, nullable=True)
    review_deadline = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(40), nullable=True)
    baseline_notes = db.Column(db.Text, nullable=True)
    success_criteria = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="planned")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    plan = db.relationship("InterventionPlan", back_populates="goals")
    domain = db.relationship("CognitiveDomain")
    skill = db.relationship("CognitiveSkill")
    strategies = db.relationship(
        "InterventionStrategy",
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="InterventionStrategy.sort_order",
    )
    session_links = db.relationship(
        "SessionInterventionGoal",
        back_populates="goal",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class InterventionStrategy(db.Model):
    __tablename__ = "intervention_strategies"

    id = db.Column(db.Integer, primary_key=True)
    intervention_goal_id = db.Column(
        db.Integer, db.ForeignKey("intervention_goals.id"), nullable=False, index=True
    )
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    frequency = db.Column(db.String(120), nullable=True)
    materials = db.Column(db.Text, nullable=True)
    context = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    goal = db.relationship("InterventionGoal", back_populates="strategies")


class InterventionPlanReview(db.Model):
    __tablename__ = "intervention_plan_reviews"

    id = db.Column(db.Integer, primary_key=True)
    intervention_plan_id = db.Column(
        db.Integer, db.ForeignKey("intervention_plans.id"), nullable=False, index=True
    )
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    review_date = db.Column(db.Date, nullable=False, default=date.today)
    summary = db.Column(db.Text, nullable=True)
    goals_review = db.Column(db.Text, nullable=True)
    changes = db.Column(db.Text, nullable=True)
    decision = db.Column(db.String(40), nullable=False, default="continue")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    plan = db.relationship("InterventionPlan", back_populates="reviews")
    professional = db.relationship("Professional")


class ProgressNote(db.Model):
    """Evolução qualitativa — interpretação do profissional, sem score clínico."""

    __tablename__ = "progress_notes"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False, index=True)
    professional_id = db.Column(
        db.Integer, db.ForeignKey("professionals.id"), nullable=False, index=True
    )
    session_id = db.Column(
        db.Integer, db.ForeignKey("professional_sessions.id"), nullable=True
    )
    intervention_plan_id = db.Column(
        db.Integer, db.ForeignKey("intervention_plans.id"), nullable=True, index=True
    )
    intervention_goal_id = db.Column(
        db.Integer, db.ForeignKey("intervention_goals.id"), nullable=True, index=True
    )
    recorded_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    progress_status = db.Column(db.String(40), nullable=False, default="not_observed")
    summary = db.Column(db.Text, nullable=True)
    evidence = db.Column(db.Text, nullable=True)
    professional_interpretation = db.Column(db.Text, nullable=True)
    next_step = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    patient = db.relationship("Patient")
    professional = db.relationship("Professional")
    session = db.relationship("ProfessionalSession")
    intervention_plan = db.relationship("InterventionPlan")
    intervention_goal = db.relationship("InterventionGoal")
    measures = db.relationship(
        "ProgressMeasure",
        back_populates="progress_note",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def touch(self) -> None:
        self.updated_at = utcnow()


class ProgressMeasure(db.Model):
    """Medida opcional — só comparar se mesma label/unidade/escala."""

    __tablename__ = "progress_measures"

    id = db.Column(db.Integer, primary_key=True)
    progress_note_id = db.Column(
        db.Integer, db.ForeignKey("progress_notes.id"), nullable=False, index=True
    )
    label = db.Column(db.String(160), nullable=False)
    value_numeric = db.Column(db.Float, nullable=True)
    unit = db.Column(db.String(60), nullable=True)
    scale_reference = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    progress_note = db.relationship("ProgressNote", back_populates="measures")
