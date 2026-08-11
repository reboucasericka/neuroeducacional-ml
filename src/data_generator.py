"""
Gerador de dados sintéticos — NeuroLearn Analytics (Versão 1).

Produz indicadores abstratos alinhados a construtos gerais de:
atenção/funções executivas, memória de trabalho, linguagem oral/fonologia,
leitura, escrita e aritmética.

Avisos importantes:
- Dataset 100% sintético; relações são simuladas.
- Não reproduz itens, estímulos, folhas, normas ou critérios de testes.
- Stroop e Torre de Londres fundamentam apenas construtos (inibição; planeamento).
- Não constitui diagnóstico clínico, psicológico ou neuropsicológico.
- Cognição social e provas piagetianas estão fora do núcleo da Versão 1.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

from src.config import (
    ARITHMETIC_FEATURES,
    ATTENTION_EXECUTIVE_FEATURES,
    COGNITIVE_FEATURES,
    CONTEXT_FEATURES,
    DATASET_COLUMNS,
    MODEL_FEATURES,
    N_SAMPLES,
    ORAL_LANGUAGE_FEATURES,
    RANDOM_STATE,
    READING_FEATURES,
    TARGET_COLUMN,
    TRANSVERSAL_FEATURES,
    WORKING_MEMORY_FEATURES,
    WRITING_FEATURES,
)

# Latentes exportados apenas internamente (não vão para o DataFrame).
_LATENT_NAMES: Final[tuple[str, ...]] = (
    "geral",
    "executivo",
    "memoria_trabalho",
    "fonologico",
    "linguagem",
    "leitura",
    "escrita",
    "aritmetica",
)

# Correlações moderadas entre fatores (SPD).
_LATENT_CORR: Final[np.ndarray] = np.array(
    [
        # g    fe   mt   fon  ling leit escr arit
        [1.00, 0.42, 0.48, 0.40, 0.45, 0.42, 0.40, 0.38],
        [0.42, 1.00, 0.40, 0.22, 0.25, 0.30, 0.28, 0.32],
        [0.48, 0.40, 1.00, 0.35, 0.38, 0.40, 0.32, 0.42],
        [0.40, 0.22, 0.35, 1.00, 0.55, 0.58, 0.52, 0.20],
        [0.45, 0.25, 0.38, 0.55, 1.00, 0.48, 0.45, 0.22],
        [0.42, 0.30, 0.40, 0.58, 0.48, 1.00, 0.50, 0.28],
        [0.40, 0.28, 0.32, 0.52, 0.45, 0.50, 1.00, 0.25],
        [0.38, 0.32, 0.42, 0.20, 0.22, 0.28, 0.25, 1.00],
    ],
    dtype=float,
)

_PROFILE_SHIFTS: Final[np.ndarray] = np.array(
    [
        # estável
        [0.30, 0.25, 0.25, 0.20, 0.20, 0.25, 0.20, 0.20],
        # fragilidade leitura/fonologia
        [0.05, 0.05, -0.10, -0.95, -0.25, -0.90, -0.45, -0.05],
        # fragilidade executiva
        [0.00, -1.00, -0.25, 0.05, 0.05, -0.15, -0.10, -0.20],
        # fragilidade memória de trabalho
        [0.05, -0.15, -1.00, -0.10, -0.05, -0.25, -0.15, -0.35],
        # dificuldades combinadas académicas
        [-0.35, -0.40, -0.45, -0.55, -0.35, -0.70, -0.65, -0.70],
    ],
    dtype=float,
)

_PROFILE_PROBS: Final[np.ndarray] = np.array(
    [0.34, 0.18, 0.18, 0.15, 0.15], dtype=float
)


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40.0, 40.0)))


def _to_score_0_100(values: np.ndarray, noise: np.ndarray) -> np.ndarray:
    raw = 50.0 + 13.5 * values + noise
    return np.clip(raw, 0.0, 100.0).round(2)


def _compose(
    weights: dict[str, float],
    latents: dict[str, np.ndarray],
    noise: np.ndarray,
) -> np.ndarray:
    signal = np.zeros_like(noise)
    for name, weight in weights.items():
        signal = signal + weight * latents[name]
    return _to_score_0_100(signal, noise)


def _validate_dataset(df: pd.DataFrame, n_samples: int) -> None:
    if len(df) != n_samples:
        raise ValueError(f"Esperado {n_samples} linhas, obtido {len(df)}.")

    missing = [col for col in DATASET_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Colunas em falta: {missing}")

    if df.isna().any().any():
        raise ValueError("Dataset contém valores NaN.")

    numeric = df.select_dtypes(include=[np.number])
    if not np.isfinite(numeric.to_numpy()).all():
        raise ValueError("Dataset contém valores infinitos.")

    if not set(df[TARGET_COLUMN].unique()).issubset({0, 1}):
        raise ValueError(
            f"A coluna {TARGET_COLUMN} deve ser binária (0/1)."
        )

    if df["idade"].min() < 7 or df["idade"].max() > 15:
        raise ValueError("Idade fora da faixa [7, 15].")

    if df["escolaridade"].min() < 1 or df["escolaridade"].max() > 9:
        raise ValueError("Escolaridade fora da faixa [1, 9].")

    for col in COGNITIVE_FEATURES + [
        "taxa_erros",
        "engajamento",
        "fadiga",
        "frequencia_escolar",
    ]:
        col_min, col_max = float(df[col].min()), float(df[col].max())
        if col_min < 0 or col_max > 100:
            raise ValueError(f"{col} fora de [0, 100]: [{col_min}, {col_max}]")

    tempo = df["tempo_resposta"]
    if float(tempo.min()) < 1.0 or float(tempo.max()) > 10.0:
        raise ValueError(
            f"tempo_resposta fora da faixa esperada: [{tempo.min()}, {tempo.max()}]"
        )


def generate_synthetic_dataset(
    n_samples: int = N_SAMPLES,
    random_state: int = RANDOM_STATE,
) -> pd.DataFrame:
    """
    Gera dataset sintético da Versão 1 (sem scores de domínio).

    Fatores latentes, vulnerabilidade interna e probabilidade do alvo
    existem apenas durante a geração (evitam leakage explícito).

    Returns
    -------
    pd.DataFrame
        ``MODEL_FEATURES`` + ``indicador_vulnerabilidade_aprendizagem``.
    """
    if not isinstance(n_samples, int) or n_samples < 50:
        raise ValueError("n_samples deve ser um inteiro >= 50.")

    rng = np.random.default_rng(random_state)

    profile_idx = rng.choice(len(_PROFILE_PROBS), size=n_samples, p=_PROFILE_PROBS)
    profile_shift = _PROFILE_SHIFTS[profile_idx]

    base = rng.multivariate_normal(
        mean=np.zeros(len(_LATENT_NAMES)),
        cov=_LATENT_CORR,
        size=n_samples,
    )
    latents_arr = base + profile_shift
    latents = {name: latents_arr[:, i] for i, name in enumerate(_LATENT_NAMES)}

    # Executivo central: apenas latente interno (não exportado).
    executivo_central = (
        0.55 * latents["executivo"]
        + 0.45 * latents["memoria_trabalho"]
        + rng.normal(0, 0.25, n_samples)
    )

    noise_map = {
        name: rng.normal(0.0, 7.2, n_samples)
        for name in COGNITIVE_FEATURES + TRANSVERSAL_FEATURES + CONTEXT_FEATURES
    }

    data: dict[str, np.ndarray] = {}

    # --- A. Atenção e Funções Executivas ---
    # controle_inibitorio: inspirado conceptualmente no construto Stroop (não no teste).
    # planejamento: inspirado conceptualmente na Torre de Londres (não no teste).
    data["atencao_seletiva"] = _compose(
        {"executivo": 0.60, "geral": 0.25, "memoria_trabalho": 0.15},
        latents,
        noise_map["atencao_seletiva"],
    )
    data["atencao_sustentada"] = _compose(
        {"executivo": 0.65, "geral": 0.25, "memoria_trabalho": 0.10},
        latents,
        noise_map["atencao_sustentada"],
    )
    data["controle_inibitorio"] = _compose(
        {"executivo": 0.70, "geral": 0.20, "memoria_trabalho": 0.10},
        latents,
        noise_map["controle_inibitorio"],
    )
    data["flexibilidade_cognitiva"] = _compose(
        {"executivo": 0.60, "geral": 0.25, "linguagem": 0.15},
        latents,
        noise_map["flexibilidade_cognitiva"],
    )
    data["planejamento"] = _to_score_0_100(
        0.55 * latents["executivo"]
        + 0.20 * latents["geral"]
        + 0.25 * executivo_central,
        noise_map["planejamento"],
    )
    data["monitoramento"] = _compose(
        {"executivo": 0.55, "geral": 0.25, "memoria_trabalho": 0.20},
        latents,
        noise_map["monitoramento"],
    )

    # --- B. Memória de Trabalho ---
    data["span_verbal"] = _compose(
        {"memoria_trabalho": 0.65, "fonologico": 0.20, "geral": 0.15},
        latents,
        noise_map["span_verbal"],
    )
    data["manutencao_verbal"] = _compose(
        {"memoria_trabalho": 0.60, "fonologico": 0.20, "geral": 0.20},
        latents,
        noise_map["manutencao_verbal"],
    )
    data["memoria_visuoespacial"] = _compose(
        {"memoria_trabalho": 0.70, "geral": 0.15, "executivo": 0.15},
        latents,
        noise_map["memoria_visuoespacial"],
    )
    data["manipulacao_informacao"] = _to_score_0_100(
        0.45 * latents["memoria_trabalho"]
        + 0.30 * executivo_central
        + 0.15 * latents["executivo"]
        + 0.10 * latents["geral"],
        noise_map["manipulacao_informacao"],
    )

    # --- C. Linguagem oral / processamento fonológico ---
    data["discriminacao_fonologica"] = _compose(
        {"fonologico": 0.70, "linguagem": 0.15, "geral": 0.15},
        latents,
        noise_map["discriminacao_fonologica"],
    )
    data["consciencia_fonologica"] = _compose(
        {"fonologico": 0.65, "linguagem": 0.20, "geral": 0.15},
        latents,
        noise_map["consciencia_fonologica"],
    )
    data["consciencia_sintatica"] = _compose(
        {"linguagem": 0.65, "geral": 0.20, "memoria_trabalho": 0.15},
        latents,
        noise_map["consciencia_sintatica"],
    )
    data["vocabulario_receptivo"] = _compose(
        {"linguagem": 0.70, "geral": 0.30},
        latents,
        noise_map["vocabulario_receptivo"],
    )
    data["nomeacao"] = _compose(
        {"linguagem": 0.55, "fonologico": 0.25, "geral": 0.20},
        latents,
        noise_map["nomeacao"],
    )
    data["repeticao_palavras"] = _compose(
        {"fonologico": 0.45, "linguagem": 0.30, "memoria_trabalho": 0.15, "geral": 0.10},
        latents,
        noise_map["repeticao_palavras"],
    )
    data["repeticao_pseudopalavras"] = _compose(
        {"fonologico": 0.70, "memoria_trabalho": 0.15, "geral": 0.15},
        latents,
        noise_map["repeticao_pseudopalavras"],
    )
    data["compreensao_oral"] = _compose(
        {"linguagem": 0.65, "memoria_trabalho": 0.20, "geral": 0.15},
        latents,
        noise_map["compreensao_oral"],
    )

    # --- D. Leitura (fonologia → decodificação/precisão; linguagem/MT → compreensão) ---
    data["decodificacao_palavras"] = _compose(
        {"leitura": 0.35, "fonologico": 0.40, "geral": 0.15, "linguagem": 0.10},
        latents,
        noise_map["decodificacao_palavras"],
    )
    data["decodificacao_pseudopalavras"] = _compose(
        {"leitura": 0.25, "fonologico": 0.50, "geral": 0.15, "memoria_trabalho": 0.10},
        latents,
        noise_map["decodificacao_pseudopalavras"],
    )
    data["precisao_leitura"] = _compose(
        {"leitura": 0.40, "fonologico": 0.30, "geral": 0.15, "executivo": 0.15},
        latents,
        noise_map["precisao_leitura"],
    )
    data["fluencia_leitura"] = _compose(
        {"leitura": 0.35, "executivo": 0.30, "fonologico": 0.20, "geral": 0.15},
        latents,
        noise_map["fluencia_leitura"],
    )
    data["compreensao_leitora"] = _compose(
        {
            "leitura": 0.25,
            "linguagem": 0.30,
            "memoria_trabalho": 0.25,
            "geral": 0.10,
            "fonologico": 0.10,
        },
        latents,
        noise_map["compreensao_leitora"],
    )

    # --- E. Escrita ---
    data["codificacao_fonema_grafema"] = _compose(
        {"escrita": 0.30, "fonologico": 0.45, "geral": 0.15, "linguagem": 0.10},
        latents,
        noise_map["codificacao_fonema_grafema"],
    )
    data["ortografia"] = _compose(
        {"escrita": 0.40, "fonologico": 0.35, "geral": 0.15, "memoria_trabalho": 0.10},
        latents,
        noise_map["ortografia"],
    )
    data["precisao_escrita"] = _compose(
        {"escrita": 0.45, "fonologico": 0.25, "executivo": 0.15, "geral": 0.15},
        latents,
        noise_map["precisao_escrita"],
    )
    data["producao_textual"] = _compose(
        {
            "escrita": 0.30,
            "linguagem": 0.30,
            "executivo": 0.20,
            "memoria_trabalho": 0.10,
            "geral": 0.10,
        },
        latents,
        noise_map["producao_textual"],
    )

    # --- F. Aritmética ---
    data["processamento_numerico"] = _compose(
        {"aritmetica": 0.65, "geral": 0.20, "memoria_trabalho": 0.15},
        latents,
        noise_map["processamento_numerico"],
    )
    data["calculo"] = _compose(
        {"aritmetica": 0.45, "memoria_trabalho": 0.25, "executivo": 0.20, "geral": 0.10},
        latents,
        noise_map["calculo"],
    )
    data["fatos_aritmeticos"] = _compose(
        {"aritmetica": 0.50, "memoria_trabalho": 0.30, "geral": 0.20},
        latents,
        noise_map["fatos_aritmeticos"],
    )
    data["precisao_calculo"] = _compose(
        {"aritmetica": 0.45, "executivo": 0.25, "memoria_trabalho": 0.15, "geral": 0.15},
        latents,
        noise_map["precisao_calculo"],
    )

    # --- G. Transversais: idade e escolaridade correlacionadas, não perfeitas ---
    idade = rng.uniform(7.0, 15.0, n_samples)
    # Escolaridade ~ idade com ruído (aprox. idade-6, clip 1–9); não perfeita.
    escolaridade_cont = (
        (idade - 6.0)
        + rng.normal(0, 1.25, n_samples)
        + rng.choice([-1.0, 0.0, 1.0], size=n_samples, p=[0.18, 0.64, 0.18])
    )
    escolaridade = np.clip(np.rint(escolaridade_cont), 1, 9).astype(float)

    age_z = (idade - 11.0) / 4.0
    school_z = (escolaridade - 5.0) / 4.0
    develop = 0.55 * age_z + 0.45 * school_z

    # Efeito moderado de desenvolvimento (não determinante).
    for col in (
        ORAL_LANGUAGE_FEATURES
        + READING_FEATURES
        + WRITING_FEATURES
        + ARITHMETIC_FEATURES
        + WORKING_MEMORY_FEATURES
    ):
        data[col] = np.clip(
            data[col] + 2.4 * develop + rng.normal(0, 1.0, n_samples),
            0,
            100,
        ).round(2)

    # --- H. Contextuais (efeitos fracos) ---
    engajamento = _to_score_0_100(
        0.30 * latents["executivo"]
        + 0.20 * latents["geral"]
        + rng.normal(0, 0.60, n_samples),
        noise_map["engajamento"],
    )
    fadiga = _to_score_0_100(
        -0.28 * latents["executivo"]
        - 0.12 * latents["geral"]
        + rng.normal(0, 0.70, n_samples),
        noise_map["fadiga"],
    )
    frequencia_escolar = _to_score_0_100(
        0.20 * latents["geral"]
        + 0.15 * school_z
        + 0.10 * ((engajamento - 50.0) / 20.0)
        + rng.normal(0, 0.65, n_samples),
        noise_map["frequencia_escolar"],
    )

    # Feedback fraco: fadiga/engajamento → atenção e erros.
    atencao_adj = 0.045 * (engajamento - 50.0) - 0.055 * (fadiga - 50.0)
    data["atencao_sustentada"] = np.clip(
        data["atencao_sustentada"] + atencao_adj, 0, 100
    ).round(2)
    data["atencao_seletiva"] = np.clip(
        data["atencao_seletiva"] + 0.75 * atencao_adj, 0, 100
    ).round(2)

    freq_gap = (frequencia_escolar - 50.0) / 50.0
    for col in READING_FEATURES + WRITING_FEATURES + ARITHMETIC_FEATURES:
        data[col] = np.clip(data[col] + 1.6 * freq_gap, 0, 100).round(2)

    taxa_erros = _to_score_0_100(
        -0.28 * latents["executivo"]
        - 0.18 * latents["leitura"]
        - 0.15 * latents["escrita"]
        - 0.12 * latents["aritmetica"]
        - 0.12 * latents["memoria_trabalho"]
        + 0.20 * ((fadiga - 50.0) / 20.0)
        - 0.12 * ((engajamento - 50.0) / 20.0)
        + rng.normal(0, 0.55, n_samples),
        noise_map["taxa_erros"],
    )

    tempo_resposta = np.clip(
        4.2
        + 0.030 * (fadiga - 50.0)
        - 0.016 * (data["atencao_sustentada"] - 50.0)
        - 0.012 * (data["controle_inibitorio"] - 50.0)
        - 0.10 * age_z
        + rng.normal(0, 0.55, n_samples),
        1.5,
        8.0,
    ).round(2)

    data["idade"] = idade.round(2)
    data["escolaridade"] = escolaridade
    data["tempo_resposta"] = tempo_resposta
    data["taxa_erros"] = taxa_erros
    data["fadiga"] = fadiga
    data["engajamento"] = engajamento
    data["frequencia_escolar"] = frequencia_escolar

    # --- Target probabilístico (vulnerabilidade interna não exportada) ---
    fe_mean = np.mean([data[c] for c in ATTENTION_EXECUTIVE_FEATURES], axis=0)
    mt_mean = np.mean([data[c] for c in WORKING_MEMORY_FEATURES], axis=0)
    lang_mean = np.mean([data[c] for c in ORAL_LANGUAGE_FEATURES], axis=0)
    read_mean = np.mean([data[c] for c in READING_FEATURES], axis=0)
    write_mean = np.mean([data[c] for c in WRITING_FEATURES], axis=0)
    arith_mean = np.mean([data[c] for c in ARITHMETIC_FEATURES], axis=0)

    vulnerabilidade = (
        0.18 * ((50.0 - fe_mean) / 20.0)
        + 0.16 * ((50.0 - mt_mean) / 20.0)
        + 0.14 * ((50.0 - lang_mean) / 20.0)
        + 0.16 * ((50.0 - read_mean) / 20.0)
        + 0.14 * ((50.0 - write_mean) / 20.0)
        + 0.12 * ((50.0 - arith_mean) / 20.0)
        + 0.14 * ((taxa_erros - 50.0) / 20.0)
        + 0.04 * ((fadiga - 50.0) / 20.0)
        + 0.04 * ((50.0 - engajamento) / 20.0)
        + 0.03 * ((50.0 - frequencia_escolar) / 20.0)
    )
    vulnerabilidade = (vulnerabilidade - vulnerabilidade.mean()) / (
        vulnerabilidade.std() + 1e-8
    )
    # Calibração ~20–35% classe positiva.
    prob = _sigmoid(1.20 * vulnerabilidade - 1.00)
    target = rng.binomial(1, prob).astype(int)

    df = pd.DataFrame(data)
    df[TARGET_COLUMN] = target
    df = df[DATASET_COLUMNS]
    _validate_dataset(df, n_samples)
    return df


__all__ = ["generate_synthetic_dataset", "MODEL_FEATURES"]
