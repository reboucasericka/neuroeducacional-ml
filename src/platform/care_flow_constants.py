"""Constantes e utilitários do fluxo profissional (sessões / plano)."""

from __future__ import annotations

SESSION_TYPES = [
    ("initial", "Inicial"),
    ("assessment", "Avaliação"),
    ("observation", "Observação"),
    ("intervention", "Intervenção"),
    ("feedback", "Devolutiva"),
    ("family", "Familiar"),
    ("school", "Escolar"),
    ("follow_up", "Seguimento"),
    ("other", "Outro"),
]

SESSION_STATUSES = [
    ("planned", "Planeada"),
    ("completed", "Concluída"),
    ("cancelled", "Cancelada"),
    ("no_show", "Falta"),
]

PLAN_STATUSES = [
    ("draft", "Rascunho"),
    ("active", "Ativo"),
    ("completed", "Concluído"),
    ("cancelled", "Cancelado"),
]

PARTICIPANT_OPTIONS = [
    "paciente",
    "mãe",
    "pai",
    "responsável",
    "professor",
    "outro profissional",
    "outro",
]

# Roteiro de observação — redação original (não copiar EOCA).
OBSERVATION_CHECKLIST = [
    ("attention", "Mantém o foco na tarefa"),
    ("attention", "Distrai-se com estímulos do ambiente"),
    ("attention", "Necessita de redirecionamento"),
    ("attention", "Alterna entre tarefas com facilidade aparente"),
    ("instruction_comprehension", "Compreende instruções"),
    ("instruction_comprehension", "Solicita repetição das instruções"),
    ("instruction_comprehension", "Necessita de instrução segmentada"),
    ("language", "Expressão verbal compreensível"),
    ("language", "Organização da fala adequada ao contexto"),
    ("language", "Compreensão oral aparente"),
    ("task_persistence", "Mantém-se na tarefa"),
    ("task_persistence", "Abandona diante de dificuldade"),
    ("task_persistence", "Solicita ajuda"),
    ("task_persistence", "Tenta novas estratégias"),
    ("behavior", "Iniciativa observada"),
    ("behavior", "Impulsividade observada"),
    ("behavior", "Organização aparente"),
    ("behavior", "Tolerância à frustração"),
    ("emotional", "Tranquilidade aparente"),
    ("emotional", "Ansiedade observada"),
    ("emotional", "Frustração observada"),
    ("emotional", "Motivação aparente"),
]

ACTIVITY_CATEGORIES = [
    ("triagem", "Triagem"),
    ("jogo", "Jogo"),
    ("atividade pedagógica", "Atividade pedagógica"),
    ("observação", "Observação"),
    ("leitura", "Leitura"),
    ("escrita", "Escrita"),
    ("matemática", "Matemática"),
    ("memória", "Memória"),
    ("atenção", "Atenção"),
    ("outro", "Outro"),
]

REFERRAL_SPECIALTIES = [
    "Psicologia",
    "Fonoaudiologia",
    "Neurologia / Neuropediatria",
    "Terapia Ocupacional",
    "Psiquiatria",
    "Pediatria",
    "Audiologia",
    "Oftalmologia",
    "Outros",
]

REFERRAL_STATUSES = [
    ("suggested", "Sugerido"),
    ("referred", "Encaminhado"),
    ("scheduled", "Agendado"),
    ("completed", "Concluído"),
    ("cancelled", "Cancelado"),
]

DOCUMENT_TYPES = [
    ("consent", "Consentimento"),
    ("contract", "Contrato"),
    ("school_authorization", "Autorização escolar"),
    ("report", "Relatório"),
    ("external_report", "Relatório externo"),
    ("exam", "Exame"),
    ("other", "Outro"),
]

CONSENT_TYPES = [
    ("assessment", "Avaliação"),
    ("intervention", "Intervenção"),
    ("school_contact", "Contacto escolar"),
    ("data_processing", "Tratamento de dados (demo)"),
    ("other", "Outro"),
]

FEEDBACK_STATUSES = [
    ("draft", "Rascunho"),
    ("completed", "Concluída"),
    ("archived", "Arquivada"),
]

INTERVENTION_PLAN_STATUSES = [
    ("draft", "Rascunho"),
    ("active", "Ativo"),
    ("paused", "Pausado"),
    ("completed", "Concluído"),
    ("cancelled", "Cancelado"),
]

INTERVENTION_GOAL_STATUSES = [
    ("planned", "Planeado"),
    ("active", "Ativo"),
    ("achieved", "Atingido"),
    ("partially_achieved", "Parcialmente atingido"),
    ("paused", "Pausado"),
    ("cancelled", "Cancelado"),
]

INTERVENTION_REVIEW_DECISIONS = [
    ("continue", "Continuar"),
    ("modify", "Modificar"),
    ("pause", "Pausar"),
    ("complete", "Concluir"),
    ("refer", "Encaminhar"),
]

PROGRESS_STATUSES = [
    ("not_observed", "Não observado"),
    ("stable", "Estável"),
    ("progress", "Progresso"),
    ("significant_progress", "Progresso significativo"),
    ("difficulty", "Dificuldade"),
    ("regression", "Regressão"),
]

ASSESSMENT_TYPES = [
    ("initial", "Inicial"),
    ("follow_up", "Seguimento"),
    ("reevaluation", "Reavaliação"),
]

GOAL_PRIORITIES = [
    ("high", "Alta"),
    ("medium", "Média"),
    ("low", "Baixa"),
]

# Exemplos demonstrativos de estratégias (não materiais protegidos)
STRATEGY_EXAMPLES = [
    "Atividade de consciência fonológica (demo)",
    "Treino de planeamento (demo)",
    "Estratégias de organização (demo)",
    "Atividade de leitura (demo)",
    "Treino de memória de trabalho (demo)",
    "Jogos matemáticos (demo)",
]

HELP_LEVELS = [
    ("independent", "Independente"),
    ("minimal", "Ajuda mínima"),
    ("moderate", "Ajuda moderada"),
    ("substantial", "Ajuda substancial"),
    ("full", "Mediação total"),
]


def participants_to_storage(selected: list[str]) -> str | None:
    cleaned = [p.strip() for p in selected if p and p.strip()]
    return "|".join(cleaned) if cleaned else None


def participants_from_storage(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p for p in raw.split("|") if p]
