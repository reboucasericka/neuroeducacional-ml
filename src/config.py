"""
Configurações centralizadas — NeuroLearn Analytics (Versão 1).

Schema alinhado a construtos gerais de avaliação neuropsicológica cognitiva
(atenção/FE, memória de trabalho, linguagem oral/fonologia, leitura, escrita
e aritmética).

Os nomes das features são abstrações sintéticas. Não representam itens,
materiais, normas ou critérios de instrumentos clínicos.
A Cognição Social e as Provas Operatórias Piagetianas ficam fora do núcleo
da Versão 1 (módulos futuros possíveis).
"""

RANDOM_STATE = 42
N_SAMPLES = 1000
N_CLUSTERS = 3

ATTENTION_EXECUTIVE_FEATURES = [
    "atencao_seletiva",
    "atencao_sustentada",
    "controle_inibitorio",
    "flexibilidade_cognitiva",
    "planejamento",
    "monitoramento",
]

WORKING_MEMORY_FEATURES = [
    "span_verbal",
    "manutencao_verbal",
    "memoria_visuoespacial",
    "manipulacao_informacao",
]

ORAL_LANGUAGE_FEATURES = [
    "discriminacao_fonologica",
    "consciencia_fonologica",
    "consciencia_sintatica",
    "vocabulario_receptivo",
    "nomeacao",
    "repeticao_palavras",
    "repeticao_pseudopalavras",
    "compreensao_oral",
]

READING_FEATURES = [
    "decodificacao_palavras",
    "decodificacao_pseudopalavras",
    "precisao_leitura",
    "fluencia_leitura",
    "compreensao_leitora",
]

WRITING_FEATURES = [
    "codificacao_fonema_grafema",
    "ortografia",
    "precisao_escrita",
    "producao_textual",
]

ARITHMETIC_FEATURES = [
    "processamento_numerico",
    "calculo",
    "fatos_aritmeticos",
    "precisao_calculo",
]

TRANSVERSAL_FEATURES = [
    "idade",
    "escolaridade",
    "tempo_resposta",
    "taxa_erros",
]

CONTEXT_FEATURES = [
    "fadiga",
    "engajamento",
    "frequencia_escolar",
]

COGNITIVE_FEATURES = (
    ATTENTION_EXECUTIVE_FEATURES
    + WORKING_MEMORY_FEATURES
    + ORAL_LANGUAGE_FEATURES
    + READING_FEATURES
    + WRITING_FEATURES
    + ARITHMETIC_FEATURES
)

# Features observáveis individuais para ML (sem scores, sem alvo).
MODEL_FEATURES = COGNITIVE_FEATURES + TRANSVERSAL_FEATURES + CONTEXT_FEATURES

DOMAIN_FEATURES = {
    "score_atencao_funcoes_executivas": ATTENTION_EXECUTIVE_FEATURES,
    "score_memoria_trabalho": WORKING_MEMORY_FEATURES,
    "score_linguagem_oral": ORAL_LANGUAGE_FEATURES,
    "score_leitura": READING_FEATURES,
    "score_escrita": WRITING_FEATURES,
    "score_aritmetica": ARITHMETIC_FEATURES,
}

DOMAIN_SCORE_COLUMNS = list(DOMAIN_FEATURES.keys())

TARGET_COLUMN = "indicador_vulnerabilidade_aprendizagem"

DATASET_COLUMNS = MODEL_FEATURES + [TARGET_COLUMN]

# Compatibilidade / documentação da Versão 1
SCHEMA_VERSION = "1.0"
