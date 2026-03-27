"""
Protótipo acadêmico simples para análise de sinais neuroeducacionais.

Este script:
1) Gera um dataset simulado
2) Treina um classificador de árvore de decisão
3) Aplica clustering com KMeans
4) Exibe resultados básicos
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier


def gerar_dataset(n_linhas: int = 500, seed: int = 42) -> pd.DataFrame:
    """Gera dataset simulado com variáveis educacionais e alvo de risco."""
    np.random.seed(seed)

    # Variáveis simuladas com faixas solicitadas
    leitura = np.random.uniform(0, 10, n_linhas).round(2)
    escrita = np.random.uniform(0, 10, n_linhas).round(2)
    atencao = np.random.randint(1, 6, n_linhas)
    memoria = np.random.randint(1, 6, n_linhas)

    df = pd.DataFrame(
        {
            "leitura": leitura,
            "escrita": escrita,
            "atencao": atencao,
            "memoria": memoria,
        }
    )

    # Regra simples para criar o alvo binário
    df["risco"] = ((df["leitura"] < 5) & (df["atencao"] < 3)).astype(int)
    return df


def treinar_modelo(df: pd.DataFrame, seed: int = 42) -> float:
    """Treina DecisionTreeClassifier e retorna acurácia no conjunto de teste."""
    X = df[["leitura", "escrita", "atencao", "memoria"]]
    y = df["risco"]

    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    modelo = DecisionTreeClassifier(random_state=seed)
    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict(X_teste)
    return accuracy_score(y_teste, previsoes)


def aplicar_clustering(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """Aplica KMeans com 3 clusters e adiciona coluna 'cluster'."""
    features = df[["leitura", "escrita", "atencao", "memoria"]]

    kmeans = KMeans(n_clusters=3, random_state=seed, n_init=10)
    df["cluster"] = kmeans.fit_predict(features)
    return df


def main() -> None:
    """Executa fluxo completo do protótipo."""
    df = gerar_dataset(n_linhas=500, seed=42)

    acuracia = treinar_modelo(df, seed=42)
    df = aplicar_clustering(df, seed=42)

    print(f"Acurácia do Decision Tree: {acuracia:.4f}")
    print("\nPrimeiras linhas do dataset com clusters:")
    print(df.head())


if __name__ == "__main__":
    main()
