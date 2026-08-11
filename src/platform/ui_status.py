"""Labels e classes CSS centralizados para estados do prontuário."""

from __future__ import annotations

STATUS_LABELS: dict[str, str] = {
    # Gerais
    "draft": "Rascunho",
    "active": "Ativo",
    "ativo": "Ativo",
    "inativo": "Inativo",
    "inactive": "Inativo",
    "completed": "Concluído",
    "archived": "Arquivado",
    "paused": "Pausado",
    "cancelled": "Cancelado",
    "canceled": "Cancelado",
    "planned": "Planejado",
    "achieved": "Alcançado",
    "partially_achieved": "Parcialmente alcançado",
    "no_show": "Falta",
    "suggested": "Sugerido",
    "referred": "Encaminhado",
    "scheduled": "Agendado",
    "pending": "Pendente",
    "in_progress": "Em andamento",
    "done": "Concluído",
    "open": "Aberto",
    "closed": "Fechado",
}

# Classes tipográficas (não só cor)
STATUS_MODIFIERS: dict[str, str] = {
    "draft": "status-badge--draft",
    "active": "status-badge--active",
    "ativo": "status-badge--active",
    "inativo": "status-badge--archived",
    "inactive": "status-badge--archived",
    "completed": "status-badge--completed",
    "archived": "status-badge--archived",
    "paused": "status-badge--paused",
    "cancelled": "status-badge--cancelled",
    "canceled": "status-badge--cancelled",
    "planned": "status-badge--planned",
    "achieved": "status-badge--completed",
    "partially_achieved": "status-badge--partial",
    "no_show": "status-badge--warning",
    "suggested": "status-badge--info",
    "referred": "status-badge--info",
    "scheduled": "status-badge--planned",
    "pending": "status-badge--draft",
    "in_progress": "status-badge--active",
    "done": "status-badge--completed",
    "open": "status-badge--active",
    "closed": "status-badge--archived",
}


def status_label(value: str | None, fallback: str | None = None) -> str:
    if not value:
        return fallback or "—"
    key = str(value).strip().lower()
    return STATUS_LABELS.get(key) or STATUS_LABELS.get(value) or fallback or str(value)


def status_modifier(value: str | None) -> str:
    if not value:
        return "status-badge--neutral"
    key = str(value).strip().lower()
    return STATUS_MODIFIERS.get(key) or STATUS_MODIFIERS.get(value) or "status-badge--neutral"
