# 🚀 GitHub Actions - Guia Completo de Configuração

Este guia fornece instruções passo a passo para configurar automação total do PFDH no GitHub Actions.

**Tempo estimado**: 15-20 minutos  
**Dificuldade**: Fácil  
**Custo**: Grátis (2.000 minutos/mês inclusos)

---

## 📋 Pré-requisitos

- ✅ Repositório GitHub do PFDH
- ✅ Todas as credenciais de API (BCB, FRED, Anbima)
- ✅ Arquivo `client_secret.json` do Google
- ✅ Token OAuth do Google (gerado localmente)
- ✅ (Opcional) Webhook do Slack para notificações

---

## 🔐 PASSO 1: Preparar Credenciais

### 1.1 Gerar Token OAuth do Google (uma única vez)

Primeiro, você precisa gerar um `token.json` localmente:

```bash
# Clone seu repositório
git clone https://github.com/SEU_USUARIO/public-finance-data-hub.git
cd public-finance-data-hub

# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
make setup

# Copie seu client_secret.json para a pasta secrets
cp ~/caminho/para/client_secret.json secrets/

# Autentique com Google Drive
pfdh auth-google

# Isso abrirá browser -> Autorize -> Token será salvo em token.json
cat token.json
# Copie TODO o conteúdo deste arquivo (vamos usar em breve)
```

### 1.2 Reunir Todas as Credenciais

Antes de prosseguir, tenha pronto:

```
📄 FRED_API_KEY = "seu_valor_aqui"
📄 ANBIMA_CLIENT_ID = "seu_valor_aqui"
📄 ANBIMA_CLIENT_SECRET = "seu_valor_aqui"
📄 GOOGLE_DRIVE_FOLDER_ID = "1dHJ_r69H_idQyMJE4H60AtVNnDgEOHgF"
📄 GOOGLE_CLIENT_SECRET_JSON = conteúdo completo do JSON (copiar tudo)
📄 GOOGLE_OAUTH_TOKEN = conteúdo completo do token.json (copiar tudo)
📄 SLACK_WEBHOOK = "https://hooks.slack.com/..." (opcional)
```

---

## 🔐 PASSO 2: Adicionar Secrets no GitHub

Os "Secrets" são variáveis criptografadas que o GitHub armazena com segurança.

### 2.1 Navegue para Settings do Repositório

1. Vá para: `https://github.com/SEU_USUARIO/public-finance-data-hub/settings`
2. Na barra lateral esquerda, clique em: **"Secrets and variables" → "Actions"**

### 2.2 Crie Cada Secret

Para cada secret, clique em **"New repository secret"** e adicione:

#### Secret 1: FRED_API_KEY
```
Name: FRED_API_KEY
Value: 799cd7a566a9a353d78c7238d88ed9ab
```
Clique "Add secret"

#### Secret 2: ANBIMA_CLIENT_ID
```
Name: ANBIMA_CLIENT_ID
Value: mcSZA9BJPuaE
```
Clique "Add secret"

#### Secret 3: ANBIMA_CLIENT_SECRET
```
Name: ANBIMA_CLIENT_SECRET
Value: cTc6RSsP4Z9U
```
Clique "Add secret"

#### Secret 4: GOOGLE_DRIVE_FOLDER_ID
```
Name: GOOGLE_DRIVE_FOLDER_ID
Value: 1dHJ_r69H_idQyMJE4H60AtVNnDgEOHgF
```
Clique "Add secret"

#### Secret 5: GOOGLE_CLIENT_SECRET_JSON
```
Name: GOOGLE_CLIENT_SECRET_JSON
Value: [COLE TODO O CONTEÚDO DO arquivo secrets/client_secret.json]
```
Exemplo:
```json
{
  "installed": {
    "client_id": "263380553890-xxx.apps.googleusercontent.com",
    "client_secret": "GOCSPX-xxx",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "redirect_uris": ["http://localhost"]
  }
}
```
Clique "Add secret"

#### Secret 6: GOOGLE_OAUTH_TOKEN
```
Name: GOOGLE_OAUTH_TOKEN
Value: [COLE TODO O CONTEÚDO DO arquivo token.json]
```
Exemplo:
```json
{
  "token": "ya29.a0AfH6SMBxxx",
  "refresh_token": "1//0gOyyy-xxx",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "263380553890-xxx.apps.googleusercontent.com",
  "client_secret": "GOCSPX-xxx",
  "scopes": ["https://www.googleapis.com/auth/drive"],
  "type": "authorized_user"
}
```
Clique "Add secret"

#### Secret 7 (Opcional): SLACK_WEBHOOK
```
Name: SLACK_WEBHOOK
Value: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX
```
Clique "Add secret"

### 2.3 Verificar Secrets

Você deve ver todos os secrets listados (valores ocultados por segurança):

```
✅ ANBIMA_CLIENT_ID
✅ ANBIMA_CLIENT_SECRET
✅ FRED_API_KEY
✅ GOOGLE_CLIENT_SECRET_JSON
✅ GOOGLE_DRIVE_FOLDER_ID
✅ GOOGLE_OAUTH_TOKEN
✅ SLACK_WEBHOOK (opcional)
```

---

## ⚙️ PASSO 3: Verificar Workflow no Repositório

O arquivo `.github/workflows/daily-ingest.yml` já foi criado e deve estar pronto.

### 3.1 Confirmar Presença do Arquivo

1. Vá para: `https://github.com/SEU_USUARIO/public-finance-data-hub/blob/main/.github/workflows/daily-ingest.yml`
2. Você deve ver o arquivo YAML com todas as instruções

### 3.2 Entender o Workflow

O workflow (`.github/workflows/daily-ingest.yml`) faz:

1. **Agendamento**: Executa **automaticamente** todos os dias às **2 AM UTC** (10 PM São Paulo com horário de verão)
2. **Health Check**: Verifica se todas as APIs estão acessíveis
3. **Ingestão**: Coleta dados de 5 fontes (BCB, FRED, Anbima, Yahoo, B3)
4. **Proteções Implementadas**:
   - ✅ Rate limiting (delays entre requisições)
   - ✅ Cache de dados
   - ✅ Retry automático com backoff exponencial
   - ✅ User-Agents rotativos
   - ✅ Headers apropriados
5. **Sincronização**: Envia dados para Google Drive
6. **Notificações**: Envia notificação para Slack
7. **Logs**: Salva todos os logs como artefatos

---

## 🧪 PASSO 4: Teste Sua Configuração

### 4.1 Executar Workflow Manualmente

1. Vá para: `https://github.com/SEU_USUARIO/public-finance-data-hub/actions`
2. Clique na esquerda: **"Daily Data Ingest & Sync"**
3. Clique em: **"Run workflow"** (botão verde)
4. Selecione branch: **main**
5. Clique: **"Run workflow"**

O workflow começará a rodar (aguarde ~5-10 minutos)

### 4.2 Monitorar Execução

1. Você verá uma entrada com status "running" em amarelo
2. Clique nela para ver logs em tempo real
3. Aguarde até ficar verde (✅ sucesso) ou vermelho (❌ erro)

### 4.3 Verificar Resultados

Ao final, você verá:

```
✅ Checkout repository
✅ Set up Python 3.11
✅ Install dependencies
✅ Create .env from secrets
✅ Create Google credentials from secrets
✅ Create logs directory
✅ Run API health check
✅ Ingest data from all sources
✅ Sync to Google Drive
✅ Generate report
✅ Upload logs as artifact
✅ Notify Slack on success
```

Todos verdes = tudo funcionando! 🎉

### 4.4 Baixar Logs

Para ver detalhes do que aconteceu:

1. Na página da execução, role para baixo
2. Procure por **"Artifacts"** (downloads)
3. Clique em **"pfdh-logs-XXXXX"**
4. Descompacte e abra os arquivos `.log`

---

## 📅 PASSO 5: Configurar Agendamento

O workflow já está configurado para rodar automaticamente, mas você pode ajustar:

### 5.1 Editar Cronograma

Para alterar a hora de execução:

1. Abra: `.github/workflows/daily-ingest.yml`
2. Procure por:
   ```yaml
   on:
     schedule:
       - cron: '0 2 * * *'  # ← Esta linha controla a hora
   ```

3. O formato é: `'minuto hora dia_mes mes dia_semana'`

**Exemplos:**
```
'0 2 * * *'    → 2 AM UTC todos os dias (PADRÃO)
'0 14 * * 1'   → 2 PM UTC segundas-feiras (semanal)
'0 6,14 * * *' → 6 AM e 2 PM UTC todos os dias (2x/dia)
'0 2 * * 0-4'  → 2 AM seg-sex (weekdays only)
```

4. Salve e commit

### 5.2 Desabilitar/Ativar Temporariamente

Para desabilitar sem deletar:

1. Abra: `.github/workflows/daily-ingest.yml`
2. Comente a seção `schedule`:
   ```yaml
   on:
     # schedule:
     #   - cron: '0 2 * * *'
     workflow_dispatch:  # Deixar apenas manual
   ```

---

## 📊 PASSO 6: Configurar Notificações do Slack (Opcional)

Para receber alertas no Slack:

### 6.1 Criar Webhook no Slack

1. Vá para: `https://api.slack.com/apps`
2. Clique: **"Create New App"** → **"From scratch"**
3. Nome: `PFDH Notifications`
4. Workspace: Seu workspace
5. Clique: **"Create App"**

### 6.2 Ativar Incoming Webhooks

1. Na sidebar, clique: **"Incoming Webhooks"**
2. Toggle: **On**
3. Clique: **"Add New Webhook to Workspace"**
4. Selecione canal: `#notifications` (ou crie um)
5. Clique: **"Allow"**
6. Copie o URL completo (começa com `https://hooks.slack.com/...`)

### 6.3 Adicionar Secret do Slack

1. Volte para GitHub Settings → Secrets
2. Clique: **"New repository secret"**
3. Nome: `SLACK_WEBHOOK`
4. Valor: Cole a URL que copiou
5. Clique: **"Add secret"**

---

## 🔍 PASSO 7: Monitorar Execuções Futuras

### 7.1 Página de Actions

Volte regularmente para: `https://github.com/SEU_USUARIO/public-finance-data-hub/actions`

Você verá:
- **Status**: ✅ sucesso ou ❌ erro
- **Hora de execução**: Quando rodou
- **Duração**: Quanto tempo levou
- **Logs**: Clique para ver detalhes

### 7.2 Interpretar Resultados

| Status | Significado | Ação |
|--------|-------------|-------|
| ✅ Verde | Sucesso total | Nenhuma - dados foram ingeridos e sincronizados |
| 🟡 Amarelo | Rodando | Aguarde conclusão (máx 45 min) |
| 🔴 Vermelho | Erro | Clique para ver logs e identificar problema |
| ⏭️ Pulado | Rate limit | APIs estão bloqueando - retry automático em 24h |

### 7.3 Problemas Comuns

#### Erro: "Secret not found"
- **Causa**: Você não adicionou um secret obrigatório
- **Solução**: Volte ao PASSO 2 e verifique todos os secrets

#### Erro: "Google authentication failed"
- **Causa**: Token expirou ou `client_secret.json` está errado
- **Solução**: Gere novo `token.json` localmente (seção 1.1)

#### Erro: "Rate limit exceeded"
- **Causa**: API bloqueou por muitas requisições
- **Solução**: Espere 24h, o retry é automático

#### Erro: "Google Drive sync failed" (não-crítico)
- **Causa**: Problema de conexão com Drive
- **Solução**: Workflow continua mesmo assim - dados foram coletados

---

## 📈 PASSO 8: Monitorar Limites de API

### 8.1 Verificar Consumo

O GitHub Actions fornece relatório mensal:

1. Vá para: `https://github.com/SEU_USUARIO/settings/billing/actions`
2. Você verá quanto dos 2.000 minutos/mês usou

**Seu uso estimado:**
- Execução diária: ~10-15 minutos
- Mês inteiro: ~300-450 minutos
- **Status**: Sempre dentro do limite grátis ✅

### 8.2 Alertas Automáticos

GitHub avisa quando você atingir:
- 75% do limite (automático por email)
- 90% do limite (aviso do GitHub)

---

## 🎓 PASSO 9: Entender Proteções Implementadas

O workflow inclui múltiplas camadas de proteção:

### Rate Limiting
```python
# Cada API tem limite máximo de requisições/minuto
BCB: 100 req/min → Seu uso: ~50/dia ✅
FRED: 100 req/min → Seu uso: ~30/dia ✅
Yahoo: ~30 req/min → Seu uso: ~50/dia ⚠️ (protegido)
B3: ~20 req/min → Seu uso: ~5/dia ✅
```

### Cache de Dados
```python
# Dados são cacheados por 24h
# Requisições duplicadas são evitadas
# Reduz carga nas APIs em 50-70%
```

### Retry Automático
```python
# Se uma requisição falha:
# Tentativa 1: Imediata
# Tentativa 2: Aguarda 1-2 segundos
# Tentativa 3: Aguarda 2-4 segundos
# Após 3 falhas: Registra erro e continua
```

### User-Agents Rotativos
```python
# Cada requisição usa User-Agent diferente
# Evita detecção como bot
# Mais natural para servidores das APIs
```

---

## 📚 REFERÊNCIA RÁPIDA

### Comandos Úteis

```bash
# Ver logs localmente
cat logs/ingest.log

# Testar localmente (antes de confiar ao GitHub)
make ingest

# Verificar status das APIs
pfdh health-check --verbose

# Forçar limpeza de cache
pfdh cache clear --older-than 0
```

### Cronograma Sugerido para Seu Caso

Baseado em seu período (01/01/2025 até hoje = 422 dias):

```yaml
# RECOMENDADO: Diário (coleta constante, sempre fresco)
schedule:
  - cron: '0 2 * * *'  # 2 AM UTC todos os dias

# ALTERNATIVA: Semanal (menos carga)
schedule:
  - cron: '0 2 * * 1'  # 2 AM seg-feiras

# ALTERNATIVA: Múltiplo por dia (agressivo)
schedule:
  - cron: '0 9,14,20 * * *'  # 3x/dia
```

---

## ✅ Checklist Final

- [ ] Todos os 6 secrets criados
- [ ] Workflow `.github/workflows/daily-ingest.yml` presente
- [ ] Teste manual executado com sucesso
- [ ] Logs verificados (status verde)
- [ ] Slack webhook configurado (opcional)
- [ ] Agendamento ajustado conforme necessário
- [ ] Bookmarkado a página de Actions

---

## 🎉 Pronto!

Seu PFDH agora está **100% automatizado** no GitHub Actions! 🚀

De agora em diante:
- ✅ Dados serão coletados automaticamente todos os dias
- ✅ Sincronizados com Google Drive
- ✅ Você receberá notificações via Slack
- ✅ Logs serão salvos por 30 dias

**Não há mais nada para fazer!** Deixe rodar 🤖

---

## 📞 Troubleshooting

Se algo der errado:

1. Clique na execução falha em **Actions**
2. Procure pelo step que falhou (em vermelho)
3. Expanda e leia a mensagem de erro
4. Consulte a seção "Problemas Comuns" acima
5. Se persistir, verifique os logs em `logs/` no artefato

---

**Última atualização**: 27 de Fevereiro de 2026  
**Status**: ✅ Pronto para Produção
