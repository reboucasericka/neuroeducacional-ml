# Projeto Acadêmico: Sinais Neuroeducacionais com Machine Learning

Este projeto é um protótipo simples para fins acadêmicos (MBA em Data Science & Analytics).  
O objetivo é simular dados educacionais e aplicar técnicas básicas de aprendizado de máquina para identificar padrões relacionados a sinais neuroeducacionais.

## Objetivo

- Gerar um dataset simulado com indicadores de desempenho e cognição;
- Criar uma variável alvo de risco educacional (`risco`);
- Treinar um classificador para prever risco;
- Aplicar clustering para segmentação de perfis.

## Tecnologias utilizadas

- Python
- NumPy
- Pandas
- Scikit-learn

## Estrutura

- `main.py`: geração dos dados, treinamento do modelo e clustering;
- `requirements.txt`: dependências do projeto;
- `README.md`: descrição do projeto.

## Como executar

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Execute o script principal:

```bash
python main.py
```

## Saídas esperadas

- Acurácia do modelo `DecisionTreeClassifier`;
- Primeiras linhas do dataset com a coluna `cluster`.

> Observação: este é um protótipo educacional simples, não um sistema de produção.
