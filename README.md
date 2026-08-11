# NeuroLearn Analytics

NeuroLearn Analytics é uma plataforma experimental de gestão de avaliação e acompanhamento voltada à:

- Neuropsicopedagogia Clínica;
- Neuropsicopedagogia Institucional;
- Psicopedagogia.

A plataforma organiza:

- prontuário longitudinal;
- anamneses;
- planeamento;
- sessões;
- avaliações;
- instrumentos;
- perfil cognitivo;
- encaminhamentos;
- futuras intervenções/evolução.

O escopo funcional e a investigação regulatória do projeto estão direcionados ao **contexto brasileiro**. A arquitetura foi desenvolvida considerando princípios de privacidade e segurança aplicáveis a esse contexto — sem afirmar certificação LGPD ou conformidade total.

> **IMPORTANTE — projeto académico/portfólio**  
> - Não substitui julgamento profissional.  
> - Não realiza diagnóstico automático.  
> - Não realiza scoring clínico não autorizado.  
> - Não reproduz instrumentos proprietários sem licença.  
> - O ML atual utiliza exclusivamente dados sintéticos.  
> - Dados sintéticos não constituem evidência clínica.  
> - Não é um dispositivo médico.

## Público-alvo (utilizadores da plataforma)

Apenas:

1. Neuropsicopedagogo Clínico  
2. Neuropsicopedagogo Institucional  
3. Psicopedagogo  

Outras profissões (psicologia, medicina, fonoaudiologia, etc.) podem aparecer apenas como **destinos de encaminhamento**, não como utilizadores da aplicação.

Terminologia na interface (Paciente / Aprendente / Avaliando) é configurável por profissional; internamente o model permanece `Patient` (legado de schema). Em inglês o termo da área é **learner** (Aprendente), não patient.

## 1. Visão geral

**Plataforma para Neuropsicopedagogia e Psicopedagogia** — organização de anamneses, avaliações, sessões, perfis cognitivos e acompanhamento longitudinal.

O **prontuário** é o coração do sistema — não o sujeito isolado e nem o Machine Learning. Tudo deve aparecer **temporalmente** dentro do prontuário.

O ML existe no projeto, mas só entra **depois** do percurso profissional estar organizado:

```
Professional → [interno: Patient] → Prontuário
  UI: Aprendente / Paciente / Avaliando (conforme preferência)
  Anamnese → Instrumentos → Avaliação → Perfil → Plano → Evolução
→ Inteligência analítica (apoio, não centro; só sintético)
```

### Compatibilidade de migração

Profissionais existentes sem `professional_type` válido (ex.: legado `psicologo`) são migrados temporariamente para `clinical_neuropsychopedagogue` apenas como default de demo/compatibilidade. A conta demo não é perdida.

## 2. Motivação

Profissionais precisam de organizar informação sensível ao longo do tempo, sem dispersão entre ficheiros e sem confundir apoio analítico com diagnóstico automático.

## 3. Problema

Falta de uma estrutura única, longitudinal e ética para:

- anamneses configuráveis;
- avaliações e instrumentos (com respeito a licenças);
- resultados introduzidos pelo profissional;
- evolução do percurso;
- análise de dados preparada e, no futuro, pseudonimizada.

## 4. Solução proposta

Uma aplicação Flask com:

- área autenticada para profissionais;
- pacientes e responsáveis legais;
- **prontuário longitudinal** como eixo temporal;
- anamneses dinâmicas e, a seguir, **catálogo de instrumentos**;
- camada de Data Science sintético preservada e separada.

## 5. Funcionalidades (estado atual)

- Landing reposicionada para Neuropsicopedagogia / Psicopedagogia (BR)
- Login / logout com password hash + onboarding leve de área de atuação
- Perfil profissional editável (`professional_type`, formação, preferência de termo)
- Dashboard profissional (`/panel`) com terminologia Paciente/Aprendente/Avaliando
- CRUD mínimo de pacientes + ficha com tabs (prontuário) — model `Patient` preservado
- Responsável legal para menores
- Modelos e preenchimento de anamneses (V2 preservada)
- **Catálogo de instrumentos** (metadados + escopo profissional + licença/digitalização)
- **Avaliações profissionais** com resultados manuais e histórico
- **Perfil Cognitivo** longitudinal com rastreabilidade (domínios V1)
- **Plano de avaliação**, sessões, observações e encaminhamentos
- **Devolutiva** (FeedbackReport) com painel de evidências — texto do profissional
- **Plano de intervenção**, objetivos, estratégias, revisões
- **Evolução longitudinal** (ProgressNote) qualitativa + medidas opcionais compatíveis
- Placeholders: relatórios avançados / PDF certificado
- Seed demonstrativo fictício (inclui DEMO-001)
- Pipeline ML sintético + EDA (preservados)

## 6. Arquitetura

```
Landing (pública)
   └── Área profissional (/panel) [autenticada]
          └── Pacientes / Prontuário  ← coração do sistema
                 └── Anamnese → Instrumentos → Avaliação → Perfil → Plano → Evolução
                        └── Data Science (datasets analíticos, não PII)  ← só depois
```

Persistência: **SQLite + Flask-SQLAlchemy** (adequado a portfólio local).  
Autenticação: **Flask-Login** + hashing Werkzeug.

## 7. Fluxo profissional (sequência ideal)

```
Anamnese
→ Planeamento (plano de avaliação)
→ Sessões
→ Avaliação
→ Perfil Cognitivo
→ Devolutiva
→ Intervenção
→ Evolução
→ Reavaliação
→ Inteligência analítica (só depois; apenas sintético)
```

A plataforma representa um **percurso longitudinal**, não apenas testes isolados.  
O profissional decide hipóteses, instrumentos, observações e encaminhamentos — sem automatismos clínicos.

Próximo passo de produto: **Devolutiva / Intervenção** (ainda placeholders).

## 8. Domínios cognitivos (Versão 1)

1. Atenção e Funções Executivas  
2. Memória de Trabalho  
3. Linguagem Oral / Processamento Fonológico  
4. Leitura  
5. Escrita  
6. Aritmética  

## 9. Data Science

O laboratório sintético (`main.py`, `src/data_generator.py`, `src/eda.py`, notebook) permanece ativo para EDA, classificação e clustering experimentais.

Dados identificáveis de pacientes **não** entram nesse pipeline nesta fase.

## 10. Tecnologias

- Python, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF
- Jinja2, HTML/CSS/JS
- NumPy, Pandas, Scikit-learn, Matplotlib

## 11. Estrutura de diretórios

```
app.py
main.py
src/
  config.py
  data_generator.py
  preprocessing.py
  eda.py
  platform/          # autenticação, modelos, painel, anamneses, instrumentos, avaliações
templates/
  index.html         # landing
  auth/
  panel/
static/
notebooks/
reports/figures/
data/processed/      # SQLite da plataforma
```

## 12. Como iniciar

### Pré-requisitos

- Python 3.10+
- Confirmar: `python --version` e `pip --version`

### Variáveis de ambiente (recomendado)

Copiar `.env.example` para `.env` (não versionado):

```bash
cp .env.example .env
```

Principais chaves:

| Variável | Notas |
|----------|--------|
| `SECRET_KEY` | Obrigatória em qualquer ambiente partilhado. Fallback local = **DEVELOPMENT ONLY**. |
| `NEUROLEARN_DATABASE_URL` / `DATABASE_URL` | Opcional; default SQLite em `data/processed/` |
| `SESSION_COOKIE_SECURE` | `1` só com HTTPS em produção |
| `NEUROLEARN_SEED_DEMO` | `0` desativa criação automática da conta demo |
| `FLASK_DEBUG` | `0` em produção (`debug=False`) |

### Instalar e ligar

```bash
pip install -r requirements.txt
python app.py
```

Abrir: [http://127.0.0.1:8080](http://127.0.0.1:8080)

> No Windows a porta 5000 costuma estar ocupada pelo sistema — a app usa **8080**.  
> Em produção: `debug=False`, HTTPS, `SESSION_COOKIE_SECURE=1`, servidor WSGI.

### Conta demo (DEVELOPMENT / DEMO ONLY)

| Campo | Valor |
|-------|--------|
| Email | `demo@neurolearn.local` |
| Password | `Demo@12345` |

> **DEMO ONLY — desenvolvimento local.**  
> Estas credenciais existem só para experimentar a área profissional no teu ambiente.  
> **Nunca uses esta conta (nem estas passwords) num deploy público.**  
> Em produção: `NEUROLEARN_SEED_DEMO=0`, cria credenciais próprias e define `SECRET_KEY`.

Pipeline ML (opcional):

```bash
python main.py
```

EDA: `notebooks/01_eda_neuroeducacional.ipynb`

Testes de segurança (CSRF):

```bash
python -m pytest tests/test_csrf_security.py -q
```

## 13. Segurança e privacidade

### Implementado

- password hashing (Werkzeug)
- autenticação Flask-Login
- proteção de `/panel`
- isolamento por `professional_id` (paciente / anamnese / avaliação cruzados → 404)
- **CSRF transversal** (Flask-WTF / `CSRFProtect`) em todos os formulários POST
- logout mutável via **POST** (não GET)
- cookies de sessão: `HttpOnly`, `SameSite=Lax` (`Secure` opcional via env em HTTPS)
- headers básicos: `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`
- proteção de open redirect no parâmetro `next` (só caminhos internos)
- whitelisting explícito de campos nos formulários (sem mass assignment)
- mensagem amigável em falha CSRF (sem stack trace ao utilizador)
- `SECRET_KEY` / DB via variáveis de ambiente (`.env` não versionado)

### Planeado

- audit log completo
- criptografia de campos sensíveis
- MFA
- recuperação segura de password
- consent management
- backups e políticas de retenção
- exportação de dados
- HTTPS obrigatório em produção
- Content Security Policy (CSP)
- gestão avançada de sessões
- RBAC complexo

> Este projeto **não** afirma conformidade RGPD certificada nem uso clínico homologado.

## 14. Catálogo de instrumentos

Os instrumentos no sistema são **metadados de catálogo**, não questionários digitais:

- nome, sigla, categoria, população, faixa etária, objetivo, licença/status;
- **conteúdos protegidos não são reproduzidos** (sem itens, normas, figuras ou folhas);
- `license_status` controla o estado de utilização (`unknown`, `public`, `restricted`, `proprietary`, `permission_required`);
- se não houver informação de licença, o default é **`unknown`** — não se assume autorização;
- a disponibilidade efetiva depende de autorização e de decisão profissional;
- instrumentos inativos **não** entram em novas avaliações.

Rotas: `/panel/instruments` (listar, criar, editar, visualizar, ativar/desativar).

## 15. Avaliações

Fluxo de entidades:

```
Patient → Assessment → AssessmentInstrument → AssessmentResult
```

- **Instrument** = entrada do catálogo  
- **AssessmentInstrument** = instrumento aplicado naquela avaliação (com snapshot de nome/sigla)  
- **AssessmentResult** = métricas manuais opcionais (ex.: tempo, erros)  

O profissional:

Paciente → Nova avaliação → Motivo → Selecionar instrumentos → Registar resultados → Guardar rascunho → Concluir → Histórico / readonly

Importante:

- resultados (`raw_score`, `standard_score`, `classification`, métricas) são **registados pelo profissional**;
- **não há scoring clínico automático**;
- **não há diagnóstico automático**;
- avaliação concluída fica readonly; reabrir como rascunho é explícito (como nas anamneses).

## 16. Perfil Cognitivo

Organiza resultados profissionais em domínios e habilidades, com **rastreabilidade completa**:

```
Assessment → AssessmentInstrument → AssessmentResult
  → CognitiveIndicator → CognitiveDomain / CognitiveSkill
```

- O profissional associa manualmente um resultado ao perfil (domínio/habilidade).
- **Não** há conversão automática entre escalas diferentes (raw ≠ percentil ≠ 0–100).
- **Não** há score agregado de domínio inventado pelo sistema.
- Anamnese **não** gera indicadores cognitivos automaticamente.
- `InstrumentSkillMapping` é configurável (catálogo → domínio/habilidade).
- Timeline longitudinal reúne **eventos** (anamneses, avaliações, indicadores, histórico), não scores misturados.
- Evolução numérica de uma habilidade só aparece quando há **mesma etiqueta + mesma unidade**.

Separação importante:

| Perfil clínico/profissional (prontuário) | Dataset sintético (Data Science / ML) |
|------------------------------------------|----------------------------------------|
| Indicadores registados pelo profissional | Scores gerados sinteticamente em `main.py` |
| Rastreável a avaliações reais do painel | Laboratório experimental, sem PII |
| Sem diagnóstico automático | Sem ligação a pacientes |

`CognitiveDomainSummary` (síntese histórica por domínio) fica **planeado** — não implementado nesta fase.

Rotas: `/panel/patients/<id>/cognitive-profile`, detalhe por domínio, indicador manual, mappings.

## 17. Fluxo profissional

Plano de avaliação, sessões, observações, encaminhamentos e contactos escolares — ver módulo `care_flow`.

## 17b. Devolutiva

A devolutiva (`FeedbackReport`) é um texto **escrito pelo profissional**.

- Pode consultar evidências (anamnese, plano, sessões, instrumentos, resultados, perfil, encaminhamentos) em painel somente leitura.
- **Não** gera diagnóstico, hipóteses clínicas automáticas nem rótulos (TDAH, dislexia, TEA, etc.).
- Rascunho → concluir (readonly) → reabrir (POST + CSRF).
- Vista preparada para impressão (`?print=1`).
- Campos separados: potencialidades, família, escola, recomendações.

## 17c. Plano de Intervenção

`InterventionPlan` + `InterventionGoal` + `InterventionStrategy` + `InterventionPlanReview`.

- Objetivos podem ligar-se a domínio/skill do perfil cognitivo.
- Critérios de sucesso e campos SMART são **manuais**.
- Estratégias são exemplificativas (demo) — sem materiais protegidos.
- Sessões reutilizam `ProfessionalSession` (`session_type=intervention`) com N:N `SessionInterventionGoal`.

## 17d. Evolução Longitudinal

`ProgressNote` (+ `ProgressMeasure` opcional):

- Estado qualitativo (estável, progresso, dificuldade, …).
- Sem percentagem arbitrária nem score clínico.
- Medidas numéricas só comparáveis com mesmo rótulo/unidade/escala (mesmo princípio do perfil cognitivo).
- Vista `/panel/patients/<id>/evolution`.

Em todos estes módulos: decisão e interpretação continuam humanas; sem IA; sem ML em dados reais de aprendentes.

## 18. Limitações

A plataforma organiza evidências ao longo do tempo. Distinguir:

| Conceito | O que é |
|----------|---------|
| Anamnese | Informação contextual e história relatada |
| Observação profissional | Registo do que o profissional observa na sessão |
| Instrumento | Entrada de catálogo (metadados); aplicação sem itens protegidos |
| Avaliação | Conjunto de instrumentos aplicados numa data |
| Indicador cognitivo | Resultado associado manualmente a domínio/habilidade |
| Hipótese profissional | Texto no plano de avaliação — **não** é diagnóstico |
| Encaminhamento | Decisão profissional documentada — **não** automática |

Upload de ficheiros em documentos e assinatura digital ficam para fases posteriores. Consentimentos são **MODELO DEMONSTRATIVO — REVISÃO JURÍDICA NECESSÁRIA**.

## 18. Limitações

- Projeto académico / experimental
- Sem diagnóstico automático / hipótese automática / IA generativa
- Sem devolutiva, plano ou recomendações gerados automaticamente
- Sem itens reais de instrumentos / scoring clínico / normas / percentis
- Sem radar enganoso com escalas incompatíveis
- Sem ML sobre dados reais de pacientes/aprendentes
- Sem CSP ainda (melhoria futura documentada)
- Sem compliance formal alegada / assinatura digital certificada

## 19. Roadmap

1. Landing + arquitetura inicial  
2. Autenticação profissional  
3. Pacientes e responsáveis  
4. Prontuário longitudinal (eixo temporal)  
5. Anamneses configuráveis  
6. Catálogo de instrumentos ✓  
7. Avaliações e resultados manuais ✓  
8. Segurança transversal (CSRF + hardening básico) ✓  
9. Perfil cognitivo + rastreabilidade ✓  
10. Fluxo profissional (plano, sessões, observações, encaminhamentos) ✓  
11. Especialização BR (tipos profissionais, terminologia, escopo de instrumentos) ✓  
12. Devolutiva + Intervenção + Evolução longitudinal ✓  
13. Modo institucional completo (Institution / ClassGroup / EducationalContext — roadmap; não criado)  
14. Data Science e análise longitudinal (só depois do percurso clínico)  
15. Segurança avançada (CSP, auditoria, MFA, …)  
16. PDF / assinatura digital (futuro)

## 20. Referências conceituais

Estrutura inicial (sem bibliografia inventada):

- Avaliação Neuropsicológica Cognitiva — Atenção e Funções Executivas  
- Avaliação Neuropsicológica Cognitiva — Linguagem Oral  
- Avaliação Neuropsicológica Cognitiva — Leitura, Escrita e Aritmética  
- Materiais de Memória de Trabalho  
- Protocolo de Avaliação de Habilidades Cognitivo-Linguísticas  

Estes materiais fundamentam **construtos**. O projeto não reproduz itens, figuras, folhas de aplicação nem tabelas normativas.
