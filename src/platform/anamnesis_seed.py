"""
Seeds de modelos de anamnese demonstrativos (conteúdo original).

Não reproduz instrumentos ou formulários proprietários.
"""

from __future__ import annotations

from sqlalchemy import or_

from src.platform.anamnesis_utils import dump_options, slugify
from src.platform.extensions import db
from src.platform.models import AnamnesisField, AnamnesisTemplate, utcnow


YES_NO = ["Sim", "Não", "Não sei / Não aplicável"]
FREQ = ["Nunca", "Raramente", "Às vezes", "Frequentemente", "Quase sempre"]


def _field(
    section: str,
    label: str,
    field_type: str = "textarea",
    *,
    required: bool = False,
    options: list[str] | None = None,
    help_text: str | None = None,
    placeholder: str | None = None,
    order: int = 0,
) -> dict:
    return {
        "section": section,
        "label": label,
        "field_type": field_type,
        "is_required": required,
        "options_json": dump_options(options),
        "help_text": help_text,
        "placeholder": placeholder,
        "sort_order": order,
        "is_active": True,
    }


def _neuro_fields() -> list[dict]:
    specs: list[tuple] = [
        ("Queixa", "Motivo principal da avaliação", "textarea", True, None),
        ("Queixa", "Quando as dificuldades foram percebidas?", "text", True, None),
        ("Queixa", "Em que contextos aparecem?", "textarea", False, None),
        ("Queixa", "Quem realizou o encaminhamento?", "text", False, None),
        ("Desenvolvimento", "Houve intercorrências relevantes no desenvolvimento?", "select", False, YES_NO),
        ("Desenvolvimento", "Idade aproximada de início da fala", "text", False, None),
        ("Desenvolvimento", "Houve dificuldades de linguagem relatadas?", "select", False, YES_NO),
        ("Desenvolvimento", "Desenvolvimento motor percebido como esperado?", "select", False, YES_NO),
        ("Histórico escolar", "Ano de escolaridade atual (relatado)", "text", False, None),
        ("Histórico escolar", "Já houve retenção/repetência?", "select", False, YES_NO),
        ("Histórico escolar", "Mudanças frequentes de escola?", "select", False, YES_NO),
        ("Histórico escolar", "Recebe apoio pedagógico?", "select", False, YES_NO),
        ("Histórico escolar", "Principais dificuldades relatadas pela escola", "textarea", False, None),
        ("Aprendizagem", "Dificuldades referidas em leitura", "select", False, FREQ),
        ("Aprendizagem", "Dificuldades referidas em escrita", "select", False, FREQ),
        ("Aprendizagem", "Dificuldades referidas em matemática", "select", False, FREQ),
        ("Aprendizagem", "Dificuldade para compreender instruções", "select", False, FREQ),
        ("Aprendizagem", "Dificuldade para concluir tarefas", "select", False, FREQ),
        ("Atenção e organização", "Dificuldade para manter atenção", "select", False, FREQ),
        ("Atenção e organização", "Dificuldade para organizar tarefas", "select", False, FREQ),
        ("Atenção e organização", "Dificuldade para seguir sequências", "select", False, FREQ),
        ("Atenção e organização", "Impulsividade percebida", "select", False, FREQ),
        ("Linguagem", "Dificuldade de compreensão oral relatada", "select", False, YES_NO),
        ("Linguagem", "Dificuldade de expressão verbal relatada", "select", False, YES_NO),
        ("Linguagem", "Histórico de intervenção fonoaudiológica", "select", False, YES_NO),
        ("Sono e rotina", "Horas aproximadas de sono", "number", False, None),
        ("Sono e rotina", "Dificuldades de sono relatadas", "select", False, YES_NO),
        ("Sono e rotina", "Rotina de estudos", "textarea", False, None),
        ("Sono e rotina", "Tempo aproximado diário de ecrã", "text", False, None),
        ("Intervenções", "Apoio escolar anterior", "boolean", False, None),
        ("Intervenções", "Psicologia", "boolean", False, None),
        ("Intervenções", "Psicopedagogia", "boolean", False, None),
        ("Intervenções", "Terapia da fala / fonoaudiologia", "boolean", False, None),
        ("Intervenções", "Terapia ocupacional", "boolean", False, None),
        ("Intervenções", "Outra intervenção", "text", False, None),
        ("Observações", "Observações adicionais da família", "textarea", False, None),
        ("Observações", "Observações profissionais", "textarea", False, None),
    ]
    return [
        _field(sec, label, ftype, required=req, options=opts, order=i)
        for i, (sec, label, ftype, req, opts) in enumerate(specs, start=1)
    ]


def _child_fields() -> list[dict]:
    specs = [
        ("Queixa", "Motivo da consulta", "textarea", True),
        ("Desenvolvimento", "Marcos do desenvolvimento relatados", "textarea", False),
        ("Saúde geral", "Saúde geral relatada pela família", "textarea", False),
        ("Rotina", "Rotina diária", "textarea", False),
        ("Escola", "Adaptação e desempenho escolar relatados", "textarea", False),
        ("Comportamento", "Comportamentos observados em casa/escola", "textarea", False),
        ("Relações familiares", "Dinâmica familiar relevante relatada", "textarea", False),
        ("Intervenções anteriores", "Acompanhamentos anteriores", "textarea", False),
        ("Observações", "Observações profissionais", "textarea", False),
    ]
    return [
        _field(sec, label, ftype, required=req, order=i)
        for i, (sec, label, ftype, req) in enumerate(specs, start=1)
    ]


def _adult_fields() -> list[dict]:
    specs = [
        ("Motivo da consulta", "Motivo principal da consulta", "textarea", True),
        ("Contexto atual", "Contexto de vida atual", "textarea", False),
        ("Histórico educacional/profissional", "Percurso educacional e profissional", "textarea", False),
        ("Rotina", "Rotina semanal", "textarea", False),
        ("Sono", "Qualidade e duração do sono relatadas", "textarea", False),
        ("Relações", "Relações significativas relatadas", "textarea", False),
        ("Intervenções anteriores", "Acompanhamentos ou tratamentos anteriores", "textarea", False),
        ("Medicação relatada", "Medicação atualmente referida (apenas registo)", "textarea", False),
        ("Observações", "Observações profissionais", "textarea", False),
    ]
    return [
        _field(
            sec,
            label,
            ftype,
            required=req,
            order=i,
            help_text=(
                "Informação registada pelo profissional; não entra em ML."
                if "Medicação" in label
                else None
            ),
        )
        for i, (sec, label, ftype, req) in enumerate(specs, start=1)
    ]


def _neuro_fields_v2() -> list[dict]:
    """Anamnese Neuroeducacional V2 — campos originais; sem duplicar ID do Patient."""
    order = 0

    def add(section, label, ftype="textarea", required=False, options=None, help_text=None):
        nonlocal order
        order += 1
        return _field(
            section,
            label,
            ftype,
            required=required,
            options=options,
            help_text=help_text,
            order=order,
        )

    fields: list[dict] = []
    # 1 Identificação contextual (sem nome/nascimento/sexo/escolaridade do Patient)
    fields += [
        add("Identificação contextual", "Quem prestou as informações?", "text"),
        add("Identificação contextual", "Relação com o paciente", "text"),
        add("Identificação contextual", "Contexto atual relevante (casa/escola)", "textarea"),
    ]
    fields += [
        add("Queixa principal", "Motivo principal da avaliação", "textarea", True),
        add("Queixa principal", "Principais preocupações relatadas", "textarea", True),
        add("Queixa principal", "Potencialidades reconhecidas no paciente", "textarea"),
    ]
    fields += [
        add("História da dificuldade atual", "Quando as dificuldades foram percebidas?", "text", True),
        add("História da dificuldade atual", "Em que contextos aparecem?", "textarea"),
        add("História da dificuldade atual", "Evolução desde o início (relatada)", "textarea"),
        add("História da dificuldade atual", "O que já foi tentado para ajudar?", "textarea"),
    ]
    fields += [
        add("Gestação e parto", "Gestação foi planejada?", "select", False, YES_NO),
        add("Gestação e parto", "Houve intercorrências relevantes durante a gestação?", "select", False, YES_NO),
        add("Gestação e parto", "Houve uso de medicamentos relatado na gestação?", "select", False, YES_NO),
        add("Gestação e parto", "Houve exposição a álcool/tabaco relatada?", "select", False, YES_NO),
        add("Gestação e parto", "Tipo de parto", "text"),
        add("Gestação e parto", "Prematuridade relatada?", "select", False, YES_NO),
        add("Gestação e parto", "Houve intercorrências no parto?", "select", False, YES_NO),
        add("Gestação e parto", "Necessidade de internação neonatal?", "select", False, YES_NO),
        add("Gestação e parto", "Observações (gestação e parto)", "textarea"),
    ]
    fields += [
        add("Desenvolvimento neuropsicomotor", "Idade aproximada em que sustentou a cabeça", "text"),
        add("Desenvolvimento neuropsicomotor", "Idade aproximada em que sentou sem apoio", "text"),
        add("Desenvolvimento neuropsicomotor", "Idade aproximada em que engatinhou", "text"),
        add("Desenvolvimento neuropsicomotor", "Idade aproximada em que ficou em pé", "text"),
        add("Desenvolvimento neuropsicomotor", "Idade aproximada em que começou a andar", "text"),
        add("Desenvolvimento neuropsicomotor", "Controle esfincteriano (relatado)", "text"),
        add("Desenvolvimento neuropsicomotor", "Dificuldades motoras relatadas", "select", False, YES_NO),
        add("Desenvolvimento neuropsicomotor", "Observações do desenvolvimento", "textarea",
            help_text="Registo descritivo — sem classificação automática de atraso."),
    ]
    fields += [
        add("Desenvolvimento da linguagem", "Idade aproximada das primeiras palavras", "text"),
        add("Desenvolvimento da linguagem", "Início de frases (idade aproximada)", "text"),
        add("Desenvolvimento da linguagem", "Dificuldades de fala relatadas", "select", False, YES_NO),
        add("Desenvolvimento da linguagem", "Compreensão oral percebida", "textarea"),
        add("Desenvolvimento da linguagem", "Histórico de terapia da fala/fonoaudiologia", "select", False, YES_NO),
        add("Desenvolvimento da linguagem", "Dificuldades atuais de linguagem", "textarea"),
        add("Desenvolvimento da linguagem", "Observações (linguagem)", "textarea"),
    ]
    fields += [
        add("Histórico de saúde", "Condições de saúde relatadas", "textarea",
            help_text="Registo profissional; não é predictor automático de ML."),
        add("Histórico de saúde", "Hospitalizações", "textarea"),
        add("Histórico de saúde", "Cirurgias", "textarea"),
        add("Histórico de saúde", "Acidentes/TCE relatados", "select", False, YES_NO),
        add("Histórico de saúde", "Convulsões relatadas", "select", False, YES_NO),
        add("Histórico de saúde", "Audição (relatada/avaliada)", "text"),
        add("Histórico de saúde", "Visão (relatada/avaliada)", "text"),
        add("Histórico de saúde", "Avaliações médicas anteriores", "textarea"),
        add("Histórico de saúde", "Observações de saúde", "textarea"),
    ]
    fields += [
        add("Tratamentos e acompanhamentos anteriores", "Tratamentos atuais/anteriores", "textarea"),
        add("Tratamentos e acompanhamentos anteriores", "Acompanhamentos profissionais anteriores", "textarea"),
    ]
    fields += [
        add("Medicação relatada", "Medicação atualmente referida (apenas registo)", "textarea",
            help_text="Informação registada pelo profissional; não entra em ML."),
    ]
    fields += [
        add("Histórico familiar", "Dificuldades de aprendizagem na família (relatadas)", "select", False, YES_NO),
        add("Histórico familiar", "Dificuldades de linguagem na família (relatadas)", "select", False, YES_NO),
        add("Histórico familiar", "Dificuldades de atenção na família (relatadas)", "select", False, YES_NO),
        add("Histórico familiar", "Questões de desenvolvimento na família (relatadas)", "select", False, YES_NO),
        add("Histórico familiar", "Saúde mental na família (relatada)", "textarea"),
        add("Histórico familiar", "Outras condições relevantes na família", "textarea"),
        add("Histórico familiar", "Observações (histórico familiar)", "textarea",
            help_text="Não transformar histórico familiar em diagnóstico."),
    ]
    fields += [
        add("Histórico escolar", "Escola atual", "text"),
        add("Histórico escolar", "Tipo de escola", "text"),
        add("Histórico escolar", "Ano/série (relatado)", "text"),
        add("Histórico escolar", "Turno", "text"),
        add("Histórico escolar", "Mudanças de escola", "textarea"),
        add("Histórico escolar", "Retenções/reprovações", "select", False, YES_NO),
        add("Histórico escolar", "Apoio pedagógico", "select", False, YES_NO),
        add("Histórico escolar", "Educação especial/apoios", "textarea"),
        add("Histórico escolar", "Dificuldades relatadas pela escola", "textarea"),
        add("Histórico escolar", "Comportamento escolar relatado", "textarea"),
        add("Histórico escolar", "Relação com professores", "textarea"),
        add("Histórico escolar", "Relação com pares", "textarea"),
        add("Histórico escolar", "Bullying relatado", "select", False, YES_NO),
        add("Histórico escolar", "Absentismo/frequência", "text"),
        add("Histórico escolar", "Disciplinas com maior facilidade", "textarea"),
        add("Histórico escolar", "Disciplinas com maior dificuldade", "textarea"),
        add("Histórico escolar", "Observações escolares", "textarea"),
    ]
    fields += [
        add("Aprendizagem", "Dificuldades referidas em leitura", "select", False, FREQ),
        add("Aprendizagem", "Dificuldades referidas em escrita", "select", False, FREQ),
        add("Aprendizagem", "Dificuldades referidas em matemática", "select", False, FREQ),
        add("Aprendizagem", "Dificuldade para compreender instruções", "select", False, FREQ),
        add("Aprendizagem", "Dificuldade para concluir tarefas", "select", False, FREQ),
        add("Aprendizagem", "Observações de aprendizagem", "textarea"),
    ]
    fields += [
        add("Atenção e organização", "Dificuldade para manter atenção", "select", False, FREQ),
        add("Atenção e organização", "Dificuldade para organizar tarefas", "select", False, FREQ),
        add("Atenção e organização", "Dificuldade para seguir sequências", "select", False, FREQ),
        add("Atenção e organização", "Impulsividade percebida", "select", False, FREQ),
        add("Atenção e organização", "Observações (atenção/organização)", "textarea"),
    ]
    fields += [
        add("Comportamento", "Comportamentos observados em casa/escola", "textarea"),
        add("Comportamento", "Observações de comportamento", "textarea"),
    ]
    fields += [
        add("Aspectos emocionais relatados", "Aspectos emocionais relatados pela família/paciente", "textarea"),
    ]
    fields += [
        add("Sono", "Horas aproximadas de sono", "number"),
        add("Sono", "Dificuldades de sono relatadas", "select", False, YES_NO),
        add("Sono", "Observações de sono", "textarea"),
    ]
    fields += [
        add("Alimentação e rotina", "Rotina diária", "textarea"),
        add("Alimentação e rotina", "Alimentação (aspectos relevantes relatados)", "textarea"),
        add("Alimentação e rotina", "Tempo aproximado diário de ecrã", "text"),
    ]
    fields += [
        add("Relações familiares e sociais", "Dinâmica familiar relevante relatada", "textarea"),
        add("Relações familiares e sociais", "Relações sociais / amigos", "textarea"),
    ]
    fields += [
        add("Expectativas da família/paciente", "O que motivou a procura pelo atendimento?", "textarea", True),
        add("Expectativas da família/paciente", "Quem realizou o encaminhamento?", "text"),
        add("Expectativas da família/paciente", "O que a família espera compreender?", "textarea"),
        add("Expectativas da família/paciente", "O que espera do processo?", "textarea"),
        add("Expectativas da família/paciente", "Quais são as principais preocupações?", "textarea"),
        add("Expectativas da família/paciente", "Quais potencialidades reconhecem no paciente?", "textarea"),
    ]
    fields += [
        add("Observações profissionais", "Observações profissionais", "textarea"),
    ]
    return fields


TEMPLATES_SPEC = [
    {
        "name": "Anamnese Neuroeducacional (legado)",
        "slug": "anamnese-neuroeducacional",
        "category": "neuroeducacional",
        "target_population": "crianca_adolescente",
        "description": "Modelo legado — respostas históricas preservadas. Preferir V2 para novos casos.",
        "fields": _neuro_fields(),
        "is_active": True,
    },
    {
        "name": "Anamnese Neuroeducacional V2",
        "slug": "anamnese-neuroeducacional-v2",
        "category": "neuroeducacional",
        "target_population": "crianca_adolescente",
        "description": (
            "Modelo enriquecido V2. Identificação do paciente vem do cabeçalho "
            "(Patient), sem duplicar nome/nascimento/sexo/escolaridade nas respostas."
        ),
        "fields": _neuro_fields_v2(),
        "is_active": True,
    },
    {
        "name": "Anamnese Infantil Geral",
        "slug": "anamnese-infantil-geral",
        "category": "infantil",
        "target_population": "crianca",
        "description": "Modelo demonstrativo breve para crianças.",
        "fields": _child_fields(),
        "is_active": True,
    },
    {
        "name": "Anamnese Adulto Geral",
        "slug": "anamnese-adulto-geral",
        "category": "adulto",
        "target_population": "adulto",
        "description": "Modelo demonstrativo breve para adultos.",
        "fields": _adult_fields(),
        "is_active": True,
    },
]


def ensure_anamnesis_templates() -> None:
    """Cria/atualiza templates demo sem apagar respostas de pacientes."""
    now = utcnow()
    for spec in TEMPLATES_SPEC:
        template = AnamnesisTemplate.query.filter_by(slug=spec["slug"]).first()
        if template is None:
            template = AnamnesisTemplate.query.filter_by(name=spec["name"]).first()
        if template is None:
            # Compat: antigo "Anamnese Neuroeducacional" sem V2 no nome
            if spec["slug"] == "anamnese-neuroeducacional":
                template = AnamnesisTemplate.query.filter_by(
                    name="Anamnese Neuroeducacional"
                ).first()
            if template is None:
                template = AnamnesisTemplate(
                    name=spec["name"],
                    slug=spec["slug"],
                    category=spec["category"],
                    target_population=spec["target_population"],
                    description=spec["description"],
                    is_active=spec.get("is_active", True),
                    created_at=now,
                    updated_at=now,
                )
                db.session.add(template)
                db.session.flush()
        if template is not None:
            template.name = spec["name"]
            template.slug = spec["slug"]
            template.category = spec["category"]
            template.target_population = spec["target_population"]
            template.description = spec["description"]
            if "is_active" in spec:
                template.is_active = spec["is_active"]
            template.touch()

        existing_labels = {
            (f.section, f.label): f for f in template.fields.order_by(AnamnesisField.id).all()
        }
        for field_spec in spec["fields"]:
            key = (field_spec["section"], field_spec["label"])
            field = existing_labels.get(key)
            if field is None:
                db.session.add(
                    AnamnesisField(
                        template_id=template.id,
                        section=field_spec["section"],
                        label=field_spec["label"],
                        help_text=field_spec.get("help_text"),
                        field_type=field_spec["field_type"],
                        options_json=field_spec.get("options_json"),
                        placeholder=field_spec.get("placeholder"),
                        is_required=field_spec["is_required"],
                        sort_order=field_spec["sort_order"],
                        is_active=True,
                    )
                )
            else:
                field.help_text = field_spec.get("help_text")
                field.field_type = field_spec["field_type"]
                field.options_json = field_spec.get("options_json")
                field.placeholder = field_spec.get("placeholder")
                field.is_required = field_spec["is_required"]
                field.sort_order = field_spec["sort_order"]
                field.is_active = True

    for template in AnamnesisTemplate.query.filter(
        or_(AnamnesisTemplate.slug.is_(None), AnamnesisTemplate.slug == "")
    ).all():
        base = slugify(template.name)
        candidate = base
        n = 2
        while AnamnesisTemplate.query.filter(
            AnamnesisTemplate.slug == candidate, AnamnesisTemplate.id != template.id
        ).first():
            candidate = f"{base}-{n}"
            n += 1
        template.slug = candidate

    db.session.commit()
