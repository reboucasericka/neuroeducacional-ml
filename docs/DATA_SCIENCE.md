# Data Science experimental — NeuroLearn Analytics

Documentação do laboratório sintético (MBA / portfólio).  
**Separado** da plataforma de prontuário.

## Objetivo académico original

Explorar como features neuroeducacionais sintéticas podem ser:

1. geradas de forma controlada;
2. agregadas em scores descritivos por domínio;
3. analisadas (EDA);
4. usadas em classificação e clustering **exploratórios**.

Não é um produto de diagnóstico. Não usa pacientes reais.

## Pipeline

```
Synthetic Data (data_generator.py)
        ↓
Preprocessing / domain scores (preprocessing.py)
        ↓
EDA (eda.py, notebooks/, reports/figures/)
        ↓
Classification (DecisionTree) + Clustering (KMeans) — main.py
```

Execução:

```bash
python main.py
```

## Dataset sintético

| Aspeto | Valor |
|--------|--------|
| Fonte | Geração procedural (`src/data_generator.py`) |
| Amostras (default) | 1000 (`N_SAMPLES`) |
| Features cognitivas | Domínios V1 (atenção/FE, memória, linguagem, leitura, escrita, aritmética) |
| Contexto | Variáveis contextuais sintéticas |
| Target | Coluna sintética de risco / classe (`TARGET_COLUMN`) |

Nomes de features são **abstrações**. Não representam itens, normas ou materiais de instrumentos clínicos.

Ver `src/config.py` para a lista canónica.

## Scores por domínio

`add_domain_scores` calcula agregações **descritivas** (médias/composições) sobre features sintéticas.

- Úteis para EDA e visualização.
- **Não** são normas clínicas nem percentis reais.

## EDA

Figuras geradas em `reports/figures/` (exemplos):

| Ficheiro | Uso sugerido |
|----------|----------------|
| `risk_distribution.png` | Distribuição do target sintético |
| `domain_scores_by_risk.png` | Scores por domínio vs risco sintético |
| `correlation_matrix.png` | Correlações entre features |
| `scatter_*.png` | Relações exploratórias pontuais |

Não incluir dezenas de gráficos no README — selecionar 3–4.

## Classificação

- Modelo: `DecisionTreeClassifier` (`main.py`)
- Métrica reportada: accuracy no hold-out estratificado

### Como interpretar

> O experimento avalia a capacidade de modelos supervisionados de recuperar padrões presentes no **conjunto sintético**.

**Não** escrever: “O modelo deteta dificuldades de aprendizagem.”

A accuracy **não** é desempenho clínico.

## Clustering

- `KMeans` (3 clusters) sobre features cognitivas sintéticas
- Exploratório; scaling completo fica como melhoria futura (nota no código)

## Limitações

- Dados sintéticos ≠ evidência clínica
- Sem validação externa
- Sem ligação ao SQLite de pacientes
- Sem scoring automático no prontuário
- Instrumentos reais não são digitalizados nem aplicados pelo ML

## Relação com a plataforma

```
Prontuário (Flask + SQLite)
        ✕  sem partilha de PII
Laboratório sintético (Pandas / sklearn)
```

A plataforma profissional regista resultados **manuais** introduzidos pelo profissional.  
O laboratório ML permanece académico/experimental.
