# Release notes — v1.0.0-portfolio

NeuroLearn Analytics — release de portfólio académico.

**Âmbito:** demonstração local / portfólio. Sem utilizadores reais, sem deploy
de produção e sem uso clínico.

## O que inclui

### Plataforma profissional

- Landing pública + autenticação (login/logout)
- Área profissional com dashboard acionável
- Gestão de pacientes/aprendentes (pesquisa, filtros, paginação)
- Prontuário longitudinal como eixo da experiência

### Percurso clínico/educacional (demo)

- Anamneses configuráveis (incluindo Neuroeducacional V2)
- Avaliações com resultados registados pelo profissional
- Perfil cognitivo (indicadores manuais / longitudinais)
- Timeline unificada com filtros
- Devolutiva, planos de intervenção e evolução
- Encaminhamentos, contactos escolares e documentos demonstrativos

### Segurança (baseline)

- Password hashing, CSRF, isolamento por `professional_id`
- Cookies HttpOnly + SameSite; mutações via POST
- Páginas de erro sem traceback ao utilizador
- Conta demo claramente marcada como **DEVELOPMENT ONLY**

### UX

- Breadcrumbs, badges, empty states, confirmações seletivas
- Tabs responsivas na ficha; seed demo idempotente

### Data Science (separado)

- Dataset sintético, EDA, Decision Tree e KMeans via `main.py`
- **O ML não lê a base de pacientes**

## Limitações explícitas

- Não é dispositivo médico; sem diagnóstico automático
- Sem scoring clínico automático / IA generativa clínica
- SQLite adequado a demo local, não a produção multi-utilizador
- Instrumentos: metadados apenas (sem itens proprietários)
- Licença do repositório: **Not yet defined**
- Sem deploy nesta release

## Conta demo

| Campo | Valor |
|-------|--------|
| Email | `demo@neurolearn.local` |
| Password | `Demo@12345` |
| Caso de referência | `DEMO-001` Lara Mendes (fictício) |

## Referências

- [README](../README.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DATA_SCIENCE.md](DATA_SCIENCE.md)
- [PORTFOLIO.md](PORTFOLIO.md)
- [DEPLOYMENT.md](DEPLOYMENT.md) — requisitos futuros (não configurados)
