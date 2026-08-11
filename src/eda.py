"""
Funções de análise exploratória (EDA) — Versão 1.

Finalidade acadêmica e demonstrativa. As relações observadas refletem a
lógica de simulação e não devem ser interpretadas como evidência clínica,
diagnóstica ou epidemiológica.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import CONTEXT_FEATURES, DOMAIN_SCORE_COLUMNS, TARGET_COLUMN, TRANSVERSAL_FEATURES

DEFAULT_CORR_COLUMNS: list[str] = DOMAIN_SCORE_COLUMNS + [
    "controle_inibitorio",
    "planejamento",
    "span_verbal",
    "manipulacao_informacao",
    "consciencia_fonologica",
    "repeticao_pseudopalavras",
    "decodificacao_palavras",
    "precisao_leitura",
    "compreensao_leitora",
    "codificacao_fonema_grafema",
    "ortografia",
    "calculo",
    "taxa_erros",
    "tempo_resposta",
    "engajamento",
    "fadiga",
]

SCATTER_PAIRS: list[tuple[str, str]] = [
    ("consciencia_fonologica", "decodificacao_palavras"),
    ("repeticao_pseudopalavras", "decodificacao_pseudopalavras"),
    ("vocabulario_receptivo", "compreensao_leitora"),
    ("span_verbal", "calculo"),
    ("controle_inibitorio", "taxa_erros"),
    ("fadiga", "tempo_resposta"),
]

TARGET_LABEL_SHORT = "indicador"


def _ensure_parent(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def _save_figure(fig: plt.Figure, output_path: str | Path | None) -> None:
    if output_path is None:
        return
    path = _ensure_parent(output_path)
    fig.savefig(path, dpi=150, bbox_inches="tight")


def _target_tick(value: int) -> str:
    return f"{TARGET_LABEL_SHORT} = {int(value)}"


def summarize_dataset(df: pd.DataFrame) -> dict:
    """Resumo compacto de qualidade e estrutura do dataset."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df deve ser um pandas.DataFrame.")

    risk_counts = df[TARGET_COLUMN].value_counts().sort_index()
    risk_pct = df[TARGET_COLUMN].value_counts(normalize=True).sort_index()

    return {
        "shape": df.shape,
        "n_duplicates": int(df.duplicated().sum()),
        "n_missing_total": int(df.isna().sum().sum()),
        "missing_by_column": df.isna().sum().sort_values(ascending=False),
        "target_counts": risk_counts,
        "target_proportions": risk_pct,
        # aliases para notebooks antigos
        "risk_counts": risk_counts,
        "risk_proportions": risk_pct,
        "numeric_describe": df.describe().T,
    }


def get_top_risk_correlations(
    df: pd.DataFrame,
    top_n: int = 10,
    exclude: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Correlações de Pearson com o alvo, ordenadas por valor absoluto."""
    exclude_cols = set(exclude or [])
    exclude_cols.add(TARGET_COLUMN)

    numeric = df.select_dtypes(include=[np.number]).drop(
        columns=[c for c in exclude_cols if c in df.columns],
        errors="ignore",
    )
    corr = numeric.corrwith(df[TARGET_COLUMN]).dropna()
    ranked = corr.reindex(corr.abs().sort_values(ascending=False).index)

    return pd.DataFrame(
        {
            "feature": ranked.index,
            "correlation": ranked.values.round(4),
            "abs_correlation": ranked.abs().values.round(4),
        }
    ).head(top_n).reset_index(drop=True)


def find_high_correlations(
    df: pd.DataFrame,
    columns: Sequence[str] | None = None,
    threshold: float = 0.90,
) -> pd.DataFrame:
    """Lista pares de features com |correlação| acima do limiar."""
    cols = list(columns) if columns is not None else [
        c for c in df.select_dtypes(include=[np.number]).columns if c != TARGET_COLUMN
    ]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes para análise de correlação: {missing}")

    corr = df[cols].corr()
    pairs: list[dict] = []
    for i, a in enumerate(cols):
        for b in cols[i + 1 :]:
            value = float(corr.loc[a, b])
            if abs(value) > threshold:
                pairs.append(
                    {
                        "feature_a": a,
                        "feature_b": b,
                        "correlation": round(value, 4),
                        "abs_correlation": round(abs(value), 4),
                    }
                )

    if not pairs:
        return pd.DataFrame(
            columns=["feature_a", "feature_b", "correlation", "abs_correlation"]
        )

    return (
        pd.DataFrame(pairs)
        .sort_values("abs_correlation", ascending=False)
        .reset_index(drop=True)
    )


def count_iqr_outliers(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Conta potenciais outliers por IQR (apenas diagnóstico; não remove)."""
    rows = []
    for col in columns:
        series = df[col]
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (series < lower) | (series > upper)
        rows.append(
            {
                "feature": col,
                "n_outliers_iqr": int(mask.sum()),
                "pct_outliers_iqr": round(100 * mask.mean(), 2),
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
            }
        )
    return pd.DataFrame(rows)


def plot_risk_distribution(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Barras com contagem e percentagem do indicador de vulnerabilidade."""
    counts = df[TARGET_COLUMN].value_counts().sort_index()
    pct = df[TARGET_COLUMN].value_counts(normalize=True).sort_index() * 100

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    labels = [_target_tick(int(i)) for i in counts.index]
    bars = ax.bar(labels, counts.values, color=["#7f9e8f", "#c48b8b"], edgecolor="none")

    for bar, n, p in zip(bars, counts.values, pct.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{int(n)}\n({p:.1f}%)",
            ha="center",
            va="bottom",
            fontsize=10,
        )

    ax.set_title("Distribuição do indicador de vulnerabilidade da aprendizagem")
    ax.set_ylabel("Contagem")
    ax.set_ylim(0, max(counts.values) * 1.18)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save_figure(fig, output_path)
    return fig, ax


def plot_domain_score_distributions(
    df: pd.DataFrame,
    output_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> plt.Figure:
    """Histogramas dos seis scores de domínio."""
    cols = DOMAIN_SCORE_COLUMNS
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Scores ausentes: {missing}")

    fig, axes = plt.subplots(2, 3, figsize=(12.5, 7.0))
    axes_flat = axes.ravel()
    colors = ["#c48b8b", "#c090b8", "#7eb8d4", "#8fa99a", "#c4a574", "#9bb7a8"]

    for ax, col, color in zip(axes_flat, cols, colors):
        values = df[col]
        ax.hist(values, bins=20, color=color, edgecolor="white", alpha=0.9)
        mean_v, median_v, std_v = values.mean(), values.median(), values.std()
        ax.axvline(mean_v, color="#2c2a28", linestyle="--", linewidth=1.2)
        ax.axvline(median_v, color="#555555", linestyle=":", linewidth=1.2)
        ax.set_title(col.replace("score_", "").replace("_", " "), fontsize=10)
        ax.set_xlabel("Score (0–100)")
        ax.set_ylabel("Frequência")
        ax.grid(axis="y", alpha=0.2)
        ax.text(
            0.98,
            0.95,
            f"μ={mean_v:.1f}\nmed={median_v:.1f}\nσ={std_v:.1f}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "alpha": 0.75,
                "edgecolor": "none",
            },
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.suptitle("Distribuição dos scores por domínio (Versão 1)", fontsize=13, y=1.01)
    fig.tight_layout()

    if output_path is None and output_dir is not None:
        output_path = Path(output_dir) / "domain_scores_distribution.png"
    _save_figure(fig, output_path)
    return fig


def plot_domain_scores_by_risk(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Boxplots dos scores de domínio por classe do indicador."""
    cols = DOMAIN_SCORE_COLUMNS
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Scores ausentes: {missing}")

    fig, ax = plt.subplots(figsize=(12.0, 5.4))
    data = []
    positions = []
    colors = []
    labels = []
    pos = 1.0
    palette = {0: "#7f9e8f", 1: "#c48b8b"}

    for col in cols:
        for risk_value in (0, 1):
            subset = df.loc[df[TARGET_COLUMN] == risk_value, col]
            data.append(subset.values)
            positions.append(pos)
            colors.append(palette[risk_value])
            pos += 1.0
        labels.append(col.replace("score_", "").replace("_", "\n"))
        pos += 0.8

    bp = ax.boxplot(
        data,
        positions=positions,
        widths=0.55,
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#2c2a28"},
    )
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)

    centers = []
    cursor = 1.5
    for _ in cols:
        centers.append(cursor)
        cursor += 2.8

    ax.set_xticks(centers)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("Score (0–100)")
    ax.set_title("Scores por domínio e indicador de vulnerabilidade")
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    legend_handles = [
        mpatches.Patch(color=palette[0], label=_target_tick(0)),
        mpatches.Patch(color=palette[1], label=_target_tick(1)),
    ]
    ax.legend(handles=legend_handles, frameon=False, loc="upper right")
    fig.tight_layout()
    _save_figure(fig, output_path)
    return fig, ax


def plot_correlation_matrix(
    df: pd.DataFrame,
    columns: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Matriz de correlação Pearson legível para colunas selecionadas."""
    cols = (
        list(columns)
        if columns is not None
        else [c for c in DEFAULT_CORR_COLUMNS if c in df.columns]
    )
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")

    corr = df[cols].corr()
    fig, ax = plt.subplots(figsize=(11.5, 9.2))
    im = ax.imshow(corr, cmap="coolwarm", vmin=-1, vmax=1)

    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=75, ha="right", fontsize=7.5)
    ax.set_yticklabels(cols, fontsize=7.5)
    ax.set_title("Matriz de correlação (seleção relevante — Versão 1)")

    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.set_ylabel("Pearson", rotation=90)

    if len(cols) <= 22:
        for i in range(len(cols)):
            for j in range(len(cols)):
                value = corr.iloc[i, j]
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=5.8,
                    color="#1f1f1f" if abs(value) < 0.65 else "white",
                )

    fig.tight_layout()
    _save_figure(fig, output_path)
    return fig, ax


def plot_top_risk_correlations(
    df: pd.DataFrame,
    top_n: int = 10,
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Gráfico horizontal das top correlações absolutas com o alvo."""
    ranking = get_top_risk_correlations(df, top_n=top_n)
    fig, ax = plt.subplots(figsize=(8.8, 5.4))

    y = np.arange(len(ranking))[::-1]
    colors = ["#c48b8b" if v >= 0 else "#7f9e8f" for v in ranking["correlation"]]
    ax.barh(y, ranking["correlation"], color=colors, edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels(ranking["feature"])
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel("Correlação de Pearson com o indicador")
    ax.set_title(f"Top {top_n} associações com o indicador (não causal)")
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save_figure(fig, output_path)
    return fig, ax


def plot_feature_vs_risk(
    df: pd.DataFrame,
    feature: str,
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Boxplot de uma feature contínua por classe do indicador."""
    if feature not in df.columns:
        raise ValueError(f"Feature ausente: {feature}")

    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    data = [
        df.loc[df[TARGET_COLUMN] == 0, feature],
        df.loc[df[TARGET_COLUMN] == 1, feature],
    ]
    bp = ax.boxplot(
        data,
        tick_labels=[_target_tick(0), _target_tick(1)],
        patch_artist=True,
        showfliers=False,
        medianprops={"color": "#2c2a28"},
    )
    for patch, color in zip(bp["boxes"], ["#7f9e8f", "#c48b8b"]):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)

    ax.set_title(f"{feature} por classe do indicador")
    ax.set_ylabel(feature)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save_figure(fig, output_path)
    return fig, ax


def plot_scatter_relation(
    df: pd.DataFrame,
    x: str,
    y: str,
    output_path: str | Path | None = None,
) -> tuple[plt.Figure, plt.Axes]:
    """Scatterplot simples entre duas variáveis numéricas."""
    for col in (x, y):
        if col not in df.columns:
            raise ValueError(f"Feature ausente: {col}")

    fig, ax = plt.subplots(figsize=(5.8, 4.6))
    ax.scatter(df[x], df[y], s=14, alpha=0.45, c="#5d7f90", edgecolors="none")
    corr = df[x].corr(df[y])
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    ax.set_title(f"{x} × {y}")
    ax.text(
        0.03,
        0.97,
        f"r = {corr:.3f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "white",
            "alpha": 0.8,
            "edgecolor": "none",
        },
    )
    ax.grid(alpha=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    _save_figure(fig, output_path)
    return fig, ax


def plot_context_overview(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
) -> plt.Figure:
    """Histogramas de variáveis transversais e contextuais."""
    cols = [c for c in TRANSVERSAL_FEATURES + CONTEXT_FEATURES if c in df.columns]
    n = len(cols)
    nrows = 2
    ncols = 4
    fig, axes = plt.subplots(nrows, ncols, figsize=(12.5, 6.2))
    for ax, col in zip(axes.ravel(), cols):
        ax.hist(df[col], bins=18, color="#9bb7a8", edgecolor="white")
        ax.set_title(col, fontsize=10)
        ax.grid(axis="y", alpha=0.2)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    for ax in axes.ravel()[n:]:
        ax.axis("off")
    fig.suptitle("Variáveis transversais e contextuais", fontsize=13, y=1.01)
    fig.tight_layout()
    _save_figure(fig, output_path)
    return fig


def generate_eda_figures(
    df: pd.DataFrame,
    figures_dir: str | Path = "reports/figures",
) -> dict[str, Path]:
    """Gera e grava o conjunto padrão de figuras da EDA (Versão 1)."""
    out = Path(figures_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    fig, _ = plot_risk_distribution(df, out / "risk_distribution.png")
    plt.close(fig)
    paths["risk_distribution"] = out / "risk_distribution.png"

    fig = plot_domain_score_distributions(
        df, output_path=out / "domain_scores_distribution.png"
    )
    plt.close(fig)
    paths["domain_scores_distribution"] = out / "domain_scores_distribution.png"

    fig, _ = plot_domain_scores_by_risk(df, out / "domain_scores_by_risk.png")
    plt.close(fig)
    paths["domain_scores_by_risk"] = out / "domain_scores_by_risk.png"

    fig, _ = plot_correlation_matrix(df, output_path=out / "correlation_matrix.png")
    plt.close(fig)
    paths["correlation_matrix"] = out / "correlation_matrix.png"

    fig, _ = plot_top_risk_correlations(df, output_path=out / "top_risk_correlations.png")
    plt.close(fig)
    paths["top_risk_correlations"] = out / "top_risk_correlations.png"

    fig = plot_context_overview(df, out / "context_distributions.png")
    plt.close(fig)
    paths["context_distributions"] = out / "context_distributions.png"

    for x, y in SCATTER_PAIRS:
        name = f"scatter_{x}_vs_{y}.png"
        fig, _ = plot_scatter_relation(df, x, y, out / name)
        plt.close(fig)
        paths[f"scatter_{x}_vs_{y}"] = out / name

    return paths
