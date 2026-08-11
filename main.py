"""
Protótipo académico — NeuroLearn Analytics (Versão 1).

Fluxo:
1) Gera dataset sintético alinhado aos 6 domínios
2) Calcula scores descritivos por domínio
3) Treina DecisionTreeClassifier
4) Aplica clustering KMeans
5) Exibe resultados básicos
"""

from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from src.config import (
    COGNITIVE_FEATURES,
    MODEL_FEATURES,
    N_SAMPLES,
    RANDOM_STATE,
    TARGET_COLUMN,
)
from src.data_generator import generate_synthetic_dataset
from src.preprocessing import add_domain_scores


def treinar_modelo(df, seed: int = RANDOM_STATE) -> float:
    """Treina DecisionTreeClassifier e retorna acurácia no conjunto de teste."""
    X = df[MODEL_FEATURES]
    y = df[TARGET_COLUMN]

    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    modelo = DecisionTreeClassifier(random_state=seed)
    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict(X_teste)
    return accuracy_score(y_teste, previsoes)


def aplicar_clustering(df, seed: int = RANDOM_STATE):
    """Aplica KMeans com 3 clusters e adiciona coluna 'cluster'."""
    # Usa apenas features cognitivas (0–100) para reduzir distorção de escala.
    # TODO: aplicar scaling e refatorar clustering no PASSO 7.
    features = df[COGNITIVE_FEATURES]

    kmeans = KMeans(n_clusters=3, random_state=seed, n_init=10)
    df = df.copy()
    df["cluster"] = kmeans.fit_predict(features)
    return df


def main() -> None:
    """Executa fluxo completo do protótipo."""
    df = generate_synthetic_dataset(n_samples=N_SAMPLES, random_state=RANDOM_STATE)
    df = add_domain_scores(df)

    acuracia = treinar_modelo(df, seed=RANDOM_STATE)
    df = aplicar_clustering(df, seed=RANDOM_STATE)

    print(f"Acurácia do Decision Tree: {acuracia:.4f}")
    print("\nPrimeiras linhas do dataset com clusters:")
    print(df.head())


if __name__ == "__main__":
    main()
