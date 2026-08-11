# Deployment — requisitos futuros

**Esta fase não configura produção real.**  
O documento lista o que seria necessário antes de um deploy público.

## Não fazer agora

- Não publicar a app com a conta demo ativa
- Não usar o servidor de desenvolvimento do Flask (`python app.py`) em produção
- Não commitir `.env` com secrets reais
- Não ativar `NEUROLEARN_SEED_DEMO` em ambiente público

## Requisitos recomendados

### Infraestrutura

- **PostgreSQL** (ou equivalente) em vez de SQLite partilhado
- Servidor **WSGI/ASGI** (ex.: Gunicorn + reverse proxy)
- **HTTPS** terminado no proxy (TLS válido)
- Separação de ambientes (staging vs production)

### Segredos e configuração

- `FLASK_ENV=production`
- `SECRET_KEY` (ou `NEUROLEARN_SECRET_KEY`) forte, única, fora do repositório
- `SESSION_COOKIE_SECURE=1`
- Variáveis via secret manager / ambiente — nunca no Git

### Dados e demo

- **Desativar** seed demo (`NEUROLEARN_SEED_DEMO=0`)
- Remover ou isolar credenciais `demo@neurolearn.local`
- Política clara de retenção e apagamento de dados
- Backups regulares com teste de restauro

### Segurança de aplicação

- Content-Security-Policy (CSP) adequada
- Rate limiting em login e endpoints sensíveis
- Headers de segurança (HSTS, X-Content-Type-Options, etc.)
- Logs sem PII desnecessária e sem secrets
- Monitorização de erros sem expor stack traces ao cliente

### Operação

- Migrações de schema versionadas
- Healthcheck e processo de restart
- Plano de incidentes (credenciais comprometidas, leak de dados)
- Revisão jurídica/ética se houver dados reais (LGPD)

## Checklist mínimo pré-produção

- [ ] PostgreSQL + backups
- [ ] HTTPS
- [ ] Secret real (não `change-me-dev-only`)
- [ ] WSGI atrás de proxy
- [ ] Seed demo desligado
- [ ] CSP + rate limiting
- [ ] Logs e rotação
- [ ] Política de gestão de dados documentada
- [ ] Suite `pytest` verde no ambiente de staging

## Referências

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [RELEASE_NOTES_V1.md](RELEASE_NOTES_V1.md)
- [README — Segurança](../README.md#segurança)
