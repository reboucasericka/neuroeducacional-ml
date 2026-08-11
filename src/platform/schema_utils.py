"""Migração leve de schema SQLite (sem Alembic nesta fase)."""

from __future__ import annotations

from sqlalchemy import inspect, text

from src.platform.extensions import db


def _existing_columns(table: str) -> set[str]:
    inspector = inspect(db.engine)
    if table not in inspector.get_table_names():
        return set()
    return {col["name"] for col in inspector.get_columns(table)}


def _add_column(table: str, column_sql: str) -> None:
    db.session.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_sql}"))


def _ensure_indexes(indexes: list[tuple[str, str, str]]) -> None:
    """CREATE INDEX IF NOT EXISTS — seguro em SQLite, sem perda de dados.

    Cada item: (index_name, table_name, column_name).
    Útil porque SQLAlchemy index=True em modelos existentes não cria índices
    retroativamente em bases já provisionadas.
    """
    for index_name, table_name, column_name in indexes:
        db.session.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON {table_name} ({column_name})"
            )
        )


def ensure_schema() -> None:
    """Cria tabelas e adiciona colunas novas sem apagar dados."""
    db.create_all()

    # Invalidar cache do inspector após create_all / ALTER.
    inspector = inspect(db.engine)
    inspector.clear_cache()

    template_cols = _existing_columns("anamnesis_templates")
    if template_cols:
        if "slug" not in template_cols:
            _add_column("anamnesis_templates", "slug VARCHAR(160)")
        if "created_at" not in template_cols:
            _add_column("anamnesis_templates", "created_at DATETIME")
        if "updated_at" not in template_cols:
            _add_column("anamnesis_templates", "updated_at DATETIME")

    field_cols = _existing_columns("anamnesis_fields")
    if field_cols:
        if "help_text" not in field_cols:
            _add_column("anamnesis_fields", "help_text TEXT")
        if "placeholder" not in field_cols:
            _add_column("anamnesis_fields", "placeholder VARCHAR(255)")
        if "is_active" not in field_cols:
            _add_column("anamnesis_fields", "is_active BOOLEAN DEFAULT 1")

    anam_cols = _existing_columns("patient_anamneses")
    if anam_cols:
        if "created_at" not in anam_cols:
            _add_column("patient_anamneses", "created_at DATETIME")
        if "updated_at" not in anam_cols:
            _add_column("patient_anamneses", "updated_at DATETIME")

    resp_cols = _existing_columns("patient_anamnesis_responses")
    if resp_cols:
        if "created_at" not in resp_cols:
            _add_column("patient_anamnesis_responses", "created_at DATETIME")
        if "updated_at" not in resp_cols:
            _add_column("patient_anamnesis_responses", "updated_at DATETIME")

    db.session.commit()
    inspector.clear_cache()

    # Normalizar status antigos e slugs nulos.
    db.session.execute(
        text(
            "UPDATE patient_anamneses SET status='draft' "
            "WHERE status IN ('em_andamento', 'rascunho')"
        )
    )
    db.session.execute(
        text(
            "UPDATE patient_anamneses SET status='completed' "
            "WHERE status IN ('concluida', 'concluída')"
        )
    )
    db.session.commit()

    inspector.clear_cache()
    instrument_cols = _existing_columns("instruments")
    if instrument_cols:
        for col, sql in [
            ("slug", "slug VARCHAR(160)"),
            ("notes", "notes TEXT"),
            ("created_at", "created_at DATETIME"),
            ("updated_at", "updated_at DATETIME"),
        ]:
            if col not in instrument_cols:
                _add_column("instruments", sql)

    assessment_cols = _existing_columns("assessments")
    if assessment_cols:
        for col, sql in [
            ("updated_at", "updated_at DATETIME"),
            ("completed_at", "completed_at DATETIME"),
        ]:
            if col not in assessment_cols:
                _add_column("assessments", sql)

    ai_cols = _existing_columns("assessment_instruments")
    if ai_cols:
        for col, sql in [
            ("instrument_name", "instrument_name VARCHAR(160)"),
            ("instrument_short_name", "instrument_short_name VARCHAR(40)"),
            ("status", "status VARCHAR(40) DEFAULT 'pending'"),
            ("created_at", "created_at DATETIME"),
            ("updated_at", "updated_at DATETIME"),
        ]:
            if col not in ai_cols:
                _add_column("assessment_instruments", sql)

    db.session.commit()

    db.session.execute(
        text(
            "UPDATE assessments SET status='draft' "
            "WHERE status IN ('planejada', 'em_andamento', 'rascunho')"
        )
    )
    db.session.execute(
        text(
            "UPDATE assessments SET status='completed' "
            "WHERE status IN ('concluida', 'concluída')"
        )
    )
    db.session.execute(
        text(
            "UPDATE instruments SET license_status='unknown' "
            "WHERE license_status IN ('a_verificar', '') OR license_status IS NULL"
        )
    )
    db.session.commit()
    inspector.clear_cache()

    # --- Especialização BR: profissionais, instrumentos, templates ---
    pro_cols = _existing_columns("professionals")
    if pro_cols:
        added_onboarding_col = False
        for col, sql in [
            ("education", "education VARCHAR(255)"),
            ("specialization", "specialization VARCHAR(255)"),
            ("workplace", "workplace VARCHAR(255)"),
            ("phone", "phone VARCHAR(40)"),
            ("city", "city VARCHAR(120)"),
            ("state", "state VARCHAR(80)"),
            ("bio", "bio TEXT"),
            ("preferred_subject_term", "preferred_subject_term VARCHAR(40)"),
            ("onboarding_completed", "onboarding_completed BOOLEAN DEFAULT 0"),
        ]:
            if col not in pro_cols:
                _add_column("professionals", sql)
                if col == "onboarding_completed":
                    added_onboarding_col = True
        db.session.commit()
        inspector.clear_cache()

        # Migração: tipos legados → clinical_neuropsychopedagogue (demo/compatibilidade)
        db.session.execute(
            text(
                "UPDATE professionals SET professional_type='clinical_neuropsychopedagogue' "
                "WHERE professional_type IS NULL OR professional_type = '' "
                "OR professional_type NOT IN ("
                "'clinical_neuropsychopedagogue',"
                "'institutional_neuropsychopedagogue',"
                "'psychopedagogue')"
            )
        )
        # Contas já existentes quando a coluna nasce: não forçar ecrã de onboarding
        if added_onboarding_col:
            db.session.execute(
                text("UPDATE professionals SET onboarding_completed=1")
            )
        db.session.execute(
            text(
                "UPDATE professionals SET preferred_subject_term='patient' "
                "WHERE (preferred_subject_term IS NULL OR preferred_subject_term='') "
                "AND professional_type='clinical_neuropsychopedagogue'"
            )
        )
        db.session.execute(
            text(
                "UPDATE professionals SET preferred_subject_term='learner' "
                "WHERE (preferred_subject_term IS NULL OR preferred_subject_term='') "
                "AND professional_type IN ("
                "'institutional_neuropsychopedagogue','psychopedagogue')"
            )
        )
        db.session.commit()

    instrument_cols = _existing_columns("instruments")
    if instrument_cols:
        for col, sql in [
            ("copyright_status", "copyright_status VARCHAR(80) DEFAULT 'unknown'"),
            ("digital_use_status", "digital_use_status VARCHAR(80) DEFAULT 'verify'"),
            ("license_notes", "license_notes TEXT"),
            ("official_source", "official_source VARCHAR(255)"),
            ("last_verified_at", "last_verified_at DATETIME"),
        ]:
            if col not in instrument_cols:
                _add_column("instruments", sql)
        db.session.commit()
        inspector.clear_cache()
        db.session.execute(
            text(
                "UPDATE instruments SET digital_use_status='verify' "
                "WHERE digital_use_status IS NULL OR digital_use_status=''"
            )
        )
        db.session.execute(
            text(
                "UPDATE instruments SET copyright_status='unknown' "
                "WHERE copyright_status IS NULL OR copyright_status=''"
            )
        )
        db.session.commit()

    template_cols = _existing_columns("anamnesis_templates")
    if template_cols:
        for col, sql in [
            ("applicable_professional_types", "applicable_professional_types TEXT"),
            ("practice_context", "practice_context VARCHAR(40)"),
        ]:
            if col not in template_cols:
                _add_column("anamnesis_templates", sql)
        db.session.commit()

    inspector.clear_cache()
    # Garante tabela N:N (create_all) e linhas default status=verify
    from src.platform.instruments_seed import ensure_instrument_professional_scopes

    ensure_instrument_professional_scopes()

    # --- Devolutiva / Intervenção / Evolução ---
    inspector.clear_cache()
    assessment_cols = _existing_columns("assessments")
    if assessment_cols and "assessment_type" not in assessment_cols:
        _add_column("assessments", "assessment_type VARCHAR(40) DEFAULT 'initial'")
        db.session.commit()
        db.session.execute(
            text(
                "UPDATE assessments SET assessment_type='initial' "
                "WHERE assessment_type IS NULL OR assessment_type=''"
            )
        )
        db.session.commit()

    session_cols = _existing_columns("professional_sessions")
    if session_cols:
        for col, sql in [
            ("intervention_plan_id", "intervention_plan_id INTEGER"),
            ("help_level", "help_level VARCHAR(80)"),
            ("difficulties_observed", "difficulties_observed TEXT"),
            ("response_notes", "response_notes TEXT"),
        ]:
            if col not in session_cols:
                _add_column("professional_sessions", sql)
        db.session.commit()

    doc_cols = _existing_columns("patient_documents")
    if doc_cols and "feedback_report_id" not in doc_cols:
        _add_column("patient_documents", "feedback_report_id INTEGER")
        db.session.commit()

    # create_all já criou as tabelas novas; limpar cache
    inspector.clear_cache()

    # Índices de listagem (CREATE INDEX IF NOT EXISTS; sem perda de dados).
    _ensure_indexes(
        [
            ("ix_assessments_patient_id", "assessments", "patient_id"),
            ("ix_assessments_professional_id", "assessments", "professional_id"),
            ("ix_assessments_status", "assessments", "status"),
            ("ix_assessments_assessment_date", "assessments", "assessment_date"),
            ("ix_patient_anamneses_patient_id", "patient_anamneses", "patient_id"),
            ("ix_patient_anamneses_professional_id", "patient_anamneses", "professional_id"),
            ("ix_patient_anamneses_status", "patient_anamneses", "status"),
            ("ix_patient_anamneses_started_at", "patient_anamneses", "started_at"),
            ("ix_professional_sessions_status", "professional_sessions", "status"),
            ("ix_professional_sessions_session_date", "professional_sessions", "session_date"),
        ]
    )
    db.session.commit()
