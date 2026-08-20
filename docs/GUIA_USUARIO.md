# Guia do usuário — vacation-is-coming

Como configurar o monitor de preços de passagens: do zero até o alerta no WhatsApp.

---

## Índice

1. [O que é este projeto](#1-o-que-é-este-projeto)
2. [O que você precisa](#2-o-que-você-precisa)
3. [Visão geral: como tudo se conecta](#3-visão-geral-como-tudo-se-conecta)
4. [Passo a passo — do zero ao alerta no WhatsApp](#4-passo-a-passo--do-zero-ao-alerta-no-whatsapp)
5. [Contas e chaves (SerpAPI + WhatsApp)](#5-contas-e-chaves-serpapi--whatsapp)
6. [Configurar a viagem (`config/travel.yaml`)](#6-configurar-a-viagem-configtravelyaml)
7. [Modos de busca de datas](#7-modos-de-busca-de-datas)
8. [Agendamento e economia de API](#8-agendamento-e-economia-de-api)
9. [GitHub Actions (execução automática na nuvem)](#9-github-actions-execução-automática-na-nuvem)
10. [Testes locais (opcional)](#10-testes-locais-opcional)
11. [Comandos úteis](#11-comandos-úteis)
12. [Custos e limites da SerpAPI](#12-custos-e-limites-da-serpapi)
13. [O que pode ir no Git — e o que NUNCA pode](#13-o-que-pode-ir-no-git--e-o-que-nunca-pode)
14. [Usar com agente de IA (Cursor, Claude, etc.)](#14-usar-com-agente-de-ia-cursor-claude-etc)
15. [Troubleshooting](#15-troubleshooting)
16. [Checklist](#16-checklist)
17. [Referência rápida de arquivos](#17-referência-rápida-de-arquivos)

---

## 1. O que é este projeto

**vacation-is-coming** é um monitor de preços de passagens aéreas que:

1. Lê rotas e datas em `config/travel.yaml`
2. Busca preços no **Google Flights** via **SerpAPI**
3. Envia um **resumo no WhatsApp** (via CallMeBot ou Twilio)
4. Salva um **histórico em Markdown** em `config/snapshots/`
5. Roda **automaticamente no GitHub Actions** (cron diário na nuvem — não precisa deixar o PC ligado)

**Não compra passagem.** Só monitora e avisa.

---

## 2. O que você precisa

| Item | Obrigatório? | Observação |
|------|--------------|------------|
| Conta **GitHub** | Sim | Para o repo, secrets e Actions |
| **Git** instalado | Sim (local) | `git --version` |
| **Python 3.12+** | Sim (testes locais) | Opcional se usar só Actions |
| Conta **SerpAPI** | Sim | Plano free: 250 buscas/mês |
| **WhatsApp** + **CallMeBot** | Sim (padrão) | Grátis; ativação em 2 min |
| Cartão de crédito | Não | Free tier basta para configs pequenas |
| PC ligado 24h | Não | GitHub Actions roda na nuvem |

### Dependências Python (automáticas)

Arquivo: `config/requirements.txt`

```
requests>=2.32.0
PyYAML>=6.0.1
python-dotenv>=1.0.1
tzdata>=2024.1
```

Instalação:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r config/requirements.txt
```

---

## 3. Visão geral: como tudo se conecta

```text
┌─────────────────────┐
│  config/travel.yaml │  ← rotas, datas, horário (SEM senhas)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌──────────────┐
│  GitHub Actions     │────▶│   SerpAPI    │  ← busca Google Flights
│  (cron diário)      │     └──────────────┘
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌───────────────┐
│WhatsApp │  │ config/       │  ← histórico commitado no repo
│ alerta  │  │ snapshots/    │
└─────────┘  └───────────────┘

Credenciais (API keys) ficam em:
  • GitHub Secrets (produção / Actions)  ← recomendado
  • config/.env (testes locais)          ← NUNCA commitar
```

---

## 4. Passo a passo — do zero ao alerta no WhatsApp

### 4.1 Obter o código

**Fork (recomendado)** — assim os Secrets e o Actions ficam na sua conta:

1. Abra [vacation-is-coming](https://github.com/henrique-bila/vacation-is-coming)
2. Clique em **Fork**
3. Clone o seu fork:

```bash
git clone https://github.com/SEU_USUARIO/vacation-is-coming.git
cd vacation-is-coming
```

Se for só explorar o código, um clone direto também funciona. Para alertas automáticos, use o fork (ou o seu próprio repositório) com Secrets.

---

### 4.2 Conferir o Git

```bash
git remote -v
git branch
```

O `origin` deve apontar para o **seu** repositório. Atualize `config/repo.yaml`:

```yaml
configured: true
remote_url: "https://github.com/SEU_USUARIO/vacation-is-coming.git"
branch: main
remote_name: origin
```

---

### 4.3 Criar contas e chaves

Siga a [seção 5](#5-contas-e-chaves-serpapi--whatsapp) antes de continuar.

---

### 4.4 Configurar a viagem

Edite `config/travel.yaml` (ou peça a um agente de IA — [seção 14](#14-usar-com-agente-de-ia-cursor-claude-etc)).

Mínimo necessário:

```yaml
configured: true
search_mode: fixed   # ou explore | range

message_title: "Alerta de passagens — Minha viagem"

schedule:
  timezone: America/Sao_Paulo
  hour: 8
  minute: 0
  interval_days: 3   # opcional — ver seção 8

routes:
  - name: "São Paulo → Salvador"
    origin: GRU
    destination: SSA
    departure_date: "2027-02-10"
    return_date: "2027-02-17"
    adults: 1
    currency: BRL
    max_results: 5
```

Códigos de aeroporto (IATA): [iata.org](https://www.iata.org/en/publications/directories/code-search)

Enquanto `configured` for `false`, buscas e o cron diário **não rodam** (o job termina em verde, sem gastar API).

---

### 4.5 Colocar secrets no GitHub

No seu repositório: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valor |
|--------|--------|
| `SERPAPI_API_KEY` | chave da SerpAPI |
| `FLIGHT_PROVIDER` | `serpapi` |
| `WHATSAPP_PROVIDER` | `callmebot` |
| `CALLMEBOT_PHONE` | telefone com DDI, só dígitos (ex.: `5543999999999`) |
| `CALLMEBOT_APIKEY` | chave que o CallMeBot enviou |

Opcional: `PRICE_ALERT_MAX` — só manda WhatsApp se algum preço for ≤ esse valor.

---

### 4.6 Sincronizar horário com o cron do Actions

O workflow usa horário **UTC**. O projeto converte automaticamente:

```bash
python -m src --sync-schedule
git add .github/workflows/check-prices.yml
git commit -m "Sync schedule cron"
git push
```

---

### 4.7 Primeiro teste

1. GitHub → **Actions**
2. Workflow: **Check flight prices and notify on WhatsApp**
3. **Run workflow** → branch `main`

O run manual **sempre usa `--force`** (ignora intervalo de dias). Deve chegar WhatsApp + snapshot novo em `config/snapshots/`.

---

## 5. Contas e chaves (SerpAPI + WhatsApp)

### 5.1 SerpAPI (busca de voos)

1. Cadastro: [serpapi.com/users/sign_up](https://serpapi.com/users/sign_up)
2. Dashboard → copiar **API Key**
3. Plano free: **250 buscas/mês**

Detalhes: [`docs/SETUP_SERPAPI.md`](SETUP_SERPAPI.md)

---

### 5.2 CallMeBot (WhatsApp grátis)

1. Salvar contato **+34 621 062 163** (CallMeBot)
2. No WhatsApp, enviar **exatamente**:
   ```text
   I allow callmebot to send me messages
   ```
3. Aguardar resposta com **APIKEY** (alguns minutos)
4. Telefone = o mesmo que ativou, com DDI, **sem espaços**

Teste local (opcional):

```bash
cp config/.env.example config/.env
# preencher CALLMEBOT_PHONE e CALLMEBOT_APIKEY
python -m src --test-whatsapp
```

Detalhes: [`docs/SETUP_WHATSAPP.md`](SETUP_WHATSAPP.md)

**Limites CallMeBot free:** ~16 mensagens a cada 4 horas. Alertas longos podem ser divididos em partes.

---

## 6. Configurar a viagem (`config/travel.yaml`)

Este é o **arquivo principal**. Pode commitar no Git (não tem senhas).

| Campo | Descrição |
|-------|-----------|
| `configured` | `true` só quando rotas/datas estiverem prontas |
| `search_mode` | `fixed`, `explore` ou `range` |
| `message_title` | Título no WhatsApp |
| `schedule` | Fuso, hora, minuto, `interval_days` opcional |
| `routes` | Lista de rotas (origem, destino, datas, moeda) |

Cada rota:

```yaml
  - name: "São Paulo → Salvador"   # nome legível
    origin: GRU                     # aeroporto origem (IATA)
    destination: SSA                # aeroporto destino
    departure_date: "2027-02-05"    # usado em fixed; fallback nos outros modos
    return_date: "2027-02-12"
    adults: 1
    currency: BRL
    max_results: 5
```

Espelhe preferências em linguagem natural em `config/preferences.md` (para agentes de IA).

---

## 7. Modos de busca de datas

### `fixed` — datas exatas

Sempre busca a mesma ida e volta configuradas na rota.

**Quando usar:** você já sabe o dia exato.

**Custo:** 1 busca SerpAPI × rota × execução.

---

### `explore` — semana mais barata no mês

Usa calendário SerpAPI (`google_travel_explore`). Acha a **melhor semana** de um mês.

```yaml
search_mode: explore
explore:
  month: 2              # fevereiro
  travel_duration: 2    # 1=weekend, 2=1 semana, 3=2 semanas
  deepen: true          # depois busca ofertas detalhadas nessa semana
```

**Limitação:** horizonte ~**6 meses** à frente. Ex.: em agosto, fevereiro do ano seguinte pode falhar.

**Custo:** ~1–2 buscas × rota × execução (mais se `deepen: true`).

---

### `range` — melhores dias dentro de uma janela

Testa **cada dia de ida** num intervalo e traz os **N mais baratos**. Cia, escalas e duração ficam no snapshot; o WhatsApp é um resumo.

```yaml
search_mode: range
range:
  departure_window_start: "2027-02-05"
  departure_window_end: "2027-02-14"   # máximo 10 dias de janela
  trip_duration_days: 7                 # volta = ida + 7 dias
  top_combinations: 3                   # quantos melhores dias mostrar
```

**Custo:** `(dias na janela) × (número de rotas)` buscas por execução.

Ex.: 10 dias × 2 rotas = **20 buscas/run**.

---

## 8. Agendamento e economia de API

```yaml
schedule:
  timezone: America/Sao_Paulo
  hour: 8
  minute: 0
  interval_days: 3
```

| Comportamento | Detalhe |
|---------------|---------|
| Cron GitHub | Dispara **todo dia** no horário (convertido para UTC) |
| `interval_days: 3` | Só **busca de verdade** a cada 3 dias; nos outros dias o job termina rápido sem gastar API |
| Run workflow manual | **Sempre força** busca (`--force`), mesmo antes dos 3 dias |
| `--dry-run` local | Ignora intervalo; busca sem mandar WhatsApp |

Depois de mudar horário ou fuso:

```bash
python -m src --sync-schedule
git add .github/workflows/check-prices.yml
git commit -m "Sync schedule"
git push
```

**Horário de verão:** após mudança de DST, rode `--sync-schedule` de novo.

---

## 9. GitHub Actions (execução automática na nuvem)

Workflow: `.github/workflows/check-prices.yml`

| Trigger | Comportamento |
|---------|---------------|
| Cron diário | Respeita `interval_days`; se `configured: false`, sai sem buscar |
| Run workflow | Busca imediata com `--force` (também exige `configured: true`) |

O job:

1. Instala Python e dependências
2. Roda `python -m src` (ou `--force` se manual)
3. Commita snapshot em `config/snapshots/` se houver busca nova

**Permissões:** o workflow precisa de `contents: write` para commitar snapshots (já configurado).

**Ver logs:** Actions → clique no run → step "Search and send WhatsApp".

---

## 10. Testes locais (opcional)

```bash
cp config/.env.example config/.env
# Preencher SERPAPI_API_KEY, CALLMEBOT_*, etc.

python -m src --test-whatsapp    # só WhatsApp, sem buscar voos
python -m src --dry-run          # busca e imprime, não manda WhatsApp
python -m src --dry-run --force  # busca mesmo dentro do interval_days
python -m src                    # busca + WhatsApp (respeita intervalo)
python -m src --force            # busca + WhatsApp forçado
python -m src --sync-schedule    # atualiza cron no workflow
```

Testes unitários:

```bash
pip install pytest
python -m pytest dev/tests -q
```

---

## 11. Comandos úteis

| Comando | O que faz |
|---------|-----------|
| `python -m src --test-whatsapp` | Testa CallMeBot/Twilio |
| `python -m src --dry-run` | Busca voos, não envia WhatsApp |
| `python -m src --force` | Ignora `interval_days` |
| `python -m src --sync-schedule` | Atualiza cron UTC no workflow |
| `python -m pytest dev/tests -q` | Roda testes |

---

## 12. Custos e limites da SerpAPI

### Plano free: 250 buscas/mês

Fórmula:

```text
buscas por execução = dias_janela × rotas   (modo range)
                    = rotas                 (modo fixed)
                    = ~2 × rotas            (modo explore com deepen)

buscas por mês ≈ buscas_por_execução × execuções_por_mês
```

### Exemplo (range, 10 dias, 2 rotas)

| Item | Valor |
|------|-------|
| Janela | 10 dias |
| Rotas | 2 |
| Por execução | 20 buscas |
| Intervalo 3 dias | ~10 execuções/mês |
| **Total/mês** | **~200 buscas** ✓ cabe no free |

### Se estourar a cota

- Aumentar `interval_days` (ex.: 5 ou 7)
- Reduzir janela ou número de rotas
- Plano pago SerpAPI (~US$ 25 / 1.000 buscas)

---

## 13. O que pode ir no Git — e o que NUNCA pode

### Pode commitar ✓

- `config/travel.yaml` — rotas e datas
- `config/preferences.md` — preferências em texto
- `config/repo.yaml` — URL do repo (sem tokens)
- `config/snapshots/*.md` — histórico de preços
- `.github/workflows/` — automação
- Código em `src/`, `agents/`, `docs/`

### NUNCA commitar ✗

- `config/.env` — chaves locais
- API keys SerpAPI, CallMeBot, Twilio
- Senhas ou tokens de qualquer tipo

Secrets de produção → **GitHub Secrets** apenas.

---

## 14. Usar com agente de IA (Cursor, Claude, etc.)

1. Abrir o repo no Cursor (ou similar)
2. O agente lê `AGENTS.md` e `agents/onboarding.md`
3. Exemplos do que pedir no chat:

   - "Monitora GRU → SSA em março, todo dia às 7h"
   - "Modo range: ida entre 5 e 14 fev, viagem 7 dias, top 3"
   - "Só avisa se passagem for abaixo de R$ 1.200"
   - "Publica no git" / "Faz push"

4. O agente edita `config/travel.yaml` + `config/preferences.md`
5. Você confirma secrets no GitHub e dá push

Playbooks:

- [`agents/onboarding.md`](../agents/onboarding.md)
- [`agents/monitor-flights.md`](../agents/monitor-flights.md)
- [`agents/git.md`](../agents/git.md)

---

## 15. Troubleshooting

| Problema | Causa provável | Solução |
|----------|----------------|---------|
| Job verde sem busca | `configured: false` | Preencher rotas e setar `configured: true` |
| Actions falha na busca | SerpAPI 400, explore fora de 6 meses | Usar `fixed` ou `range`; corrigir datas |
| Sem WhatsApp | Secrets errados | Conferir `CALLMEBOT_PHONE` e `CALLMEBOT_APIKEY` |
| WhatsApp não chega | Telefone ≠ número que ativou CallMeBot | Reativar ou `Recover APIKey` no WhatsApp |
| Job rápido, sem alerta | `interval_days` — dia de skip | Normal; ou Run workflow manual |
| `SERPAPI_API_KEY missing` | Secret não criado | Adicionar no GitHub Secrets |
| Cota SerpAPI esgotada | Muitas buscas | Aumentar intervalo, menos rotas, plano pago |
| Horário errado após DST | Cron UTC desatualizado | `python -m src --sync-schedule` + push |
| Preço "vs last" estranho | Snapshot antigo de outra config | Normal após mudar rotas/datas; estabiliza em alguns runs |

Logs: GitHub → **Actions** → run com ❌ → expandir step **Search and send WhatsApp**.

---

## 16. Checklist

- [ ] Fork (ou clone) do repositório
- [ ] Conta SerpAPI criada + API key
- [ ] CallMeBot ativado no WhatsApp
- [ ] Secrets configurados no GitHub
- [ ] `config/travel.yaml` com suas rotas/datas + `configured: true`
- [ ] `config/repo.yaml` com a URL do seu repositório
- [ ] `python -m src --sync-schedule` + push do workflow
- [ ] Run workflow manual → WhatsApp recebido
- [ ] Snapshot apareceu em `config/snapshots/`
- [ ] Entendeu `interval_days` e o custo SerpAPI
- [ ] Sabe que `config/.env` **nunca** vai pro Git

---

## 17. Referência rápida de arquivos

```text
vacation-is-coming/
├── config/
│   ├── travel.yaml          ← CONFIG PRINCIPAL (rotas, modo, horário)
│   ├── preferences.md       ← preferências em texto (para IA)
│   ├── repo.yaml            ← para onde fazer push
│   ├── .env.example         ← modelo de credenciais locais
│   ├── .env                 ← credenciais locais (NÃO COMMITAR)
│   ├── requirements.txt     ← dependências Python
│   └── snapshots/           ← histórico de preços (Markdown)
├── .github/workflows/
│   └── check-prices.yml     ← automação diária
├── src/                     ← código Python
├── agents/                  ← guias para agentes de IA
├── docs/
│   ├── GUIA_USUARIO.md      ← este arquivo
│   ├── SETUP_SERPAPI.md
│   └── SETUP_WHATSAPP.md
├── AGENTS.md                ← contrato para IAs
└── README.md                ← visão geral (inglês)
```

---

## Documentação relacionada

| Arquivo | Conteúdo |
|---------|----------|
| [`README.md`](../README.md) | Visão geral do projeto |
| [`docs/SETUP_SERPAPI.md`](SETUP_SERPAPI.md) | SerpAPI em detalhe |
| [`docs/SETUP_WHATSAPP.md`](SETUP_WHATSAPP.md) | WhatsApp / CallMeBot |
| [`docs/FLIGHT_PROVIDERS.md`](FLIGHT_PROVIDERS.md) | Provedores de voo |
| [`agents/onboarding.md`](../agents/onboarding.md) | Onboarding para agentes |
