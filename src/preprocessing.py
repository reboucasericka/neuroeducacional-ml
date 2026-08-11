"""
Pré-processamento descritivo do dataset sintético (Versão 1).

Os scores são médias simples das features observáveis de cada domínio:

- não representam normas clínicas;
- não são percentis nem escores padronizados;
- não possuem validade diagnóstica;
- destinam-se exclusivamente a este dataset sintético académico.
"""

from __future__ import annotations

import pandas as pd

from src.config import DOMAIN_FEATURES, DOMAIN_SCORE_COLUMNS


def add_domain_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona os 6 scores agregados por domínio da Versão 1.

    Cada score é uma agregação descritiva em escala 0–100. Não constitui
    escala clínica, percentil, escore padronizado nem indicador diagnóstico.

    Parameters
    ----------
    df:
        DataFrame com as features cognitivas observáveis de cada domínio.

    Returns
    -------
    pd.DataFrame
        Cópia do input com ``DOMAIN_SCORE_COLUMNS`` no final.

    Raises
    ------
    TypeError
        Se ``df`` não for um ``pandas.DataFrame``.
    ValueError
        Se faltarem features obrigatórias.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df deve ser um pandas.DataFrame.")

    required = [
        feature for features in DOMAIN_FEATURES.values() for feature in features
    ]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            "Colunas obrigatórias ausentes para calcular scores de domínio: "
            f"{missing}"
        )

    result = df.copy()
    for score_name, features in DOMAIN_FEATURES.items():
        result[score_name] = result[features].mean(axis=1).round(2)

    other_cols = [col for col in result.columns if col not in DOMAIN_SCORE_COLUMNS]
    return result[other_cols + DOMAIN_SCORE_COLUMNS]
