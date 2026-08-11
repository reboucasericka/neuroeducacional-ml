# Guia de screenshots — NeuroLearn Analytics

Capturar **apenas** dados DEMO (conta `demo@neurolearn.local`).  
Nunca fotografar dados reais ou de terceiros.

Pasta destino: `docs/screenshots/`

## Inventário atual

| Ficheiro | Conteúdo capturado |
|----------|-------------------|
| `01-landing.png` | Hero da landing pública |
| `02-dashboard.png` | Dashboard “Hoje” (conta demo) |
| `03-patient-record.png` | Lista de aprendentes (pesquisa/filtros) |
| `04-anamnesis.png` | Modelos de anamnese (incl. V2) |
| `05-assessment.png` | Lista de avaliações |
| `06-cognitive-profile.png` | Formulário “Novo aprendente” |
| `07-timeline.png` | Perfil cognitivo + timeline longitudinal |
| `08-intervention.png` | Planos de intervenção (caso demo) |
| `09-mobile.png` | Landing em viewport mobile |

## Antes de (re)capturar

1. `python scripts/seed_demo.py`
2. `python app.py`
3. Login com a conta demo
4. Preferir **DEMO-001 · Lara Mendes** na ficha quando aplicável

Viewport desktop sugerido: **1440×900** (ou 1280×800).  
Mobile: **390×844**.

## Boas práticas

- Mostrar badge **Demonstração** quando visível
- Evitar overlays do browser (bookmarks, extensão)
- Tema claro padrão do painel
- Só códigos `DEMO-*` e nomes fictícios do seed

## Onde aparecem

- README: landing, dashboard, lista, anamnese, perfil/timeline
- [PORTFOLIO.md](PORTFOLIO.md): conjunto completo com legendas

## Privacidade

Somente dados DEMO. Se o ecrã mostrar outro profissional/paciente real, não usar.
