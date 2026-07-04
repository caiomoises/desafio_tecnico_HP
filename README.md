# Hubbi · Consultor de IA para Marketplace de Autopeças

API RESTful em **Django + DRF** que vai além do CRUD: um marketplace de autopeças
com um **Consultor de IA** capaz de interpretar linguagem natural e sugerir peças
relevantes, tratando **sinônimos** do mercado automotivo — ex.: *"Filtro de Óleo"*,
*"Filtro do Motor"* e *"Elemento Filtrante de Óleo"* são a mesma peça física.

> Desafio técnico de backend. Consultor de IA implementado com **Gemini**.

---

## Sumário

- [Funcionalidades](#funcionalidades)
- [Stack](#stack)
- [Arquitetura](#arquitetura)
- [Como o Consultor de IA funciona](#como-o-consultor-de-ia-funciona)
- [Execução com Docker (recomendado)](#execução-com-docker-recomendado)
- [Execução local (sem Docker)](#execução-local-sem-docker)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Tarefas assíncronas e cronjob](#tarefas-assíncronas-e-cronjob)
- [Endpoints da API](#endpoints-da-api)
- [Exemplos de uso](#exemplos-de-uso)
- [Testes](#testes)

---

## Funcionalidades

- **Marketplace** — listar e detalhar peças; cadastro/edição/remoção só para admin.
- **Import assíncrono** — upload de catálogo `.csv` processado via **Celery** (admin).
- **Autenticação JWT** — todos os endpoints exigem token; permissões diferenciadas.
- **Consultor de IA** ★ — `POST /api/consultor/` interpreta a intenção do usuário e
  sugere peças do estoque, tratando sinônimos.
- **Integração externa** ★ — atualização de estoque em **lote** via **API Key**
  (sem JWT), para ERPs/WMS.
- **Canal WhatsApp** ✦ — conversar com o Consultor de IA pelo **WhatsApp** via
  **Evolution API** (webhook + resposta assíncrona).
- **Cronjob** — monitora estoque baixo e aplica reposições via **Celery Beat**.
- **Testes** — cobrindo CRUD, tasks, consultor (com mock do LLM) e integração.
- **Docs interativas** — Swagger em `/api/docs/` e OpenAPI em `/api/schema/`.

## Stack

| Camada | Tecnologia |
| --- | --- |
| Framework | Django 5 + Django REST Framework |
| Banco | PostgreSQL 17 (extensão `pg_trgm`) |
| Assíncrono | Celery + Redis |
| Autenticação | JWT (`djangorestframework-simplejwt`) |
| IA / LLM | Google **Gemini** (`gemini-2.5-flash`, SDK `google-genai`) |
| Testes | pytest, pytest-django, pytest-mock |
| Docs | drf-spectacular (Swagger/OpenAPI) |

## Arquitetura

```
config/                 # projeto Django: settings, urls, celery, wsgi/asgi
apps/
  marketplace/          # Peca, ImportacaoCatalogo, CRUD, upload CSV
    services.py         # regras puras: importar_catalogo(), repor_estoque()
    tasks.py            # tasks Celery (import assíncrono + cronjob reposição)
    management/commands/seed_catalogos.py
  consultor/            # Consultor de IA (pré-filtro trigram + Gemini)
  integracao/           # atualização de estoque em lote via API Key
catalogs/               # os 5 CSVs fornecidos
```

Decisão de modelagem: cada linha de um catálogo vira uma `Peca` com o campo
`fornecedor`. A mesma peça física aparece com nomes diferentes entre fornecedores;
o agrupamento de sinônimos é resolvido pelo **Consultor de IA**, não pela modelagem.

## Como o Consultor de IA funciona

Estratégia **híbrida (pré-filtro + LLM)**:

1. **Pré-filtro no Postgres** — `pg_trgm` (similaridade por trigramas) seleciona as
   peças candidatas mais próximas da mensagem, reduzindo o contexto enviado ao LLM
   (escala melhor que mandar o catálogo inteiro).
2. **LLM (Gemini)** — recebe as candidatas, interpreta a intenção (inclusive
   sintomas, ex.: *"barulho na roda"*), agrupa **sinônimos** e escolhe as peças.
3. **Hidratação pelo banco** — a resposta ao cliente usa **preço e quantidade do
   banco** (fonte da verdade); IDs "alucinados" pelo modelo são descartados.

Falhas do modelo (sem chave, rede, JSON inválido) resultam em **503** com mensagem
clara — nunca em erro 500.

---

## Execução com Docker (recomendado)

Pré-requisitos: Docker + Docker Compose.

```bash
# 1. Configure o ambiente
cp .env.example .env
#   edite .env e defina GEMINI_API_KEY e INTEGRATION_API_KEY

# 2. Suba tudo (db, redis, web, worker, beat)
docker compose up --build

# 3. Em outro terminal: crie um admin e popule os catálogos
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_catalogos
```

A API sobe em `http://localhost:8000` (as migrações rodam automaticamente).
Docs: `http://localhost:8000/api/docs/`.

## Execução local (sem Docker)

Pré-requisitos: Python 3.12, PostgreSQL 17, Redis.

```bash
# 1. Dependências
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Banco (o banco desafio_tecnico já deve existir)
cp .env.example .env         # ajuste credenciais do Postgres, Redis e chaves

# 3. Migrações + seed + admin
python manage.py migrate
python manage.py seed_catalogos
python manage.py createsuperuser

# 4. Servidor
python manage.py runserver

# 5. Em outros terminais: worker e beat (cronjob)
celery -A config worker -l info
celery -A config beat -l info
```

## Variáveis de ambiente

Ver `.env.example` (documentado). Principais:

| Variável | Descrição |
| --- | --- |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | Conexão com o PostgreSQL (`desafio_tecnico`). |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis do Celery. |
| `GEMINI_API_KEY` | Chave da IA. Grátis em https://aistudio.google.com/app/apikey |
| `GEMINI_MODEL` | Modelo (padrão `gemini-2.5-flash`). |
| `INTEGRATION_API_KEY` | API Key da integração externa (ERP/WMS). |
| `INTEGRATION_API_KEY_HEADER` | Header da API Key (padrão `X-API-KEY`). |
| `RESTOCK_INTERVAL_MINUTES` | Intervalo do cronjob de reposição (padrão 60). |

## Tarefas assíncronas e cronjob

- **Worker** (importação de CSV e reposições): `celery -A config worker -l info`
- **Beat** (cronjob de monitoramento): `celery -A config beat -l info`

### Fluxo de reposição de estoque

1. **Sinalização** — cada peça expõe `estoque_baixo` (calculado: `quantidade <
   estoque_minimo`). Liste as pendentes com `GET /api/pecas/?estoque_baixo=true`.
   O cronjob `monitorar_estoque_periodico` (Beat, a cada `RESTOCK_INTERVAL_MINUTES`)
   registra em log as peças com estoque baixo.
2. **Reposição controlada** — o admin define o campo `reposicao` da peça (ex.:
   `PATCH /api/pecas/{id}/ {"reposicao": 18}`). Isso dispara a task
   `aplicar_reposicao_peca`, que **soma** o valor ao estoque e **zera** o campo
   `reposicao`. O cronjob também aplica reposições pendentes como rede de segurança.

## Canal WhatsApp (Evolution API)

Permite conversar com o Consultor de IA pelo WhatsApp. O fluxo:

```
WhatsApp ⇄ Evolution API ──webhook──▶ /api/whatsapp/webhook/
                                          │ (enfileira task Celery)
                                          ▼
                                     consultar() ─▶ Gemini
                                          │
             Evolution sendText ◀────── resposta formatada
```

O webhook responde **200 imediatamente** e o processamento (consulta à IA +
resposta) roda de forma **assíncrona** no worker. A autenticidade do webhook é
validada por `WHATSAPP_WEBHOOK_TOKEN` (header `apikey`).

O bot responde apenas a **conversas 1:1** — mensagens de grupos (`@g.us`),
broadcast/status e newsletters são ignoradas. Opcionalmente, `WHATSAPP_ALLOWLIST`
(números separados por vírgula) restringe as respostas a números específicos;
vazia, responde a todos os contatos.

### Configuração

1. Suba a Evolution API (serviço opcional já incluído no compose):
   ```bash
   docker compose exec db createdb -U postgres evolution   # cria o banco da Evolution
   docker compose --profile whatsapp up -d evolution
   ```
2. Defina no `.env`: `EVOLUTION_API_URL` (ex.: `http://evolution:8080`),
   `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE` e `WHATSAPP_WEBHOOK_TOKEN`.
3. Crie a instância e conecte o WhatsApp (escaneie o QR code):
   ```bash
   curl -X POST http://localhost:8080/instance/create \
     -H "apikey: $EVOLUTION_API_KEY" -H "Content-Type: application/json" \
     -d '{"instanceName":"consultor","integration":"WHATSAPP-BAILEYS","qrcode":true}'
   # abra o QR retornado (ou GET /instance/connect/consultor) e escaneie no celular
   ```
4. Configure o webhook da instância apontando para o backend, enviando o token:
   ```bash
   curl -X POST http://localhost:8080/webhook/set/consultor \
     -H "apikey: $EVOLUTION_API_KEY" -H "Content-Type: application/json" \
     -d '{"webhook":{"enabled":true,"url":"http://web:8000/api/whatsapp/webhook/",
          "headers":{"apikey":"'"$WHATSAPP_WEBHOOK_TOKEN"'"},
          "events":["MESSAGES_UPSERT"]}}'
   ```
5. Pronto: mande uma mensagem para o número conectado (ex.: *"meu carro está
   fazendo barulho na roda"*) e receba as peças sugeridas pela IA.

> O worker do Celery precisa estar rodando para processar as mensagens.

## Endpoints da API

| Método | Rota | Auth | Descrição |
| --- | --- | --- | --- |
| POST | `/api/auth/token/` | — | Obtém par de tokens JWT. |
| POST | `/api/auth/token/refresh/` | — | Renova o access token. |
| GET | `/api/pecas/` | JWT | Lista peças (filtros: `fornecedor`, `disponivel`, `preco_min/max`, `search`). |
| GET | `/api/pecas/{id}/` | JWT | Detalhe da peça. |
| POST/PUT/PATCH/DELETE | `/api/pecas/{id}/` | JWT admin | Cadastra/edita/remove. |
| POST | `/api/pecas/importar/` | JWT admin | Upload de CSV (assíncrono). |
| GET | `/api/importacoes/` | JWT admin | Status das importações. |
| POST | `/api/consultor/` | JWT | Consultor de IA. |
| POST | `/api/integracao/estoque/` | API Key | Atualização de estoque em lote. |
| POST | `/api/whatsapp/webhook/` | Token | Webhook de mensagens do WhatsApp (Evolution API). |
| GET | `/api/docs/` | — | Swagger UI. |

## Exemplos de uso

```bash
# 1. Autenticar (JWT)
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"suasenha"}' | python -c "import sys,json;print(json.load(sys.stdin)['access'])")

# 2. Listar peças
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/pecas/

# 3. Consultor de IA
curl -X POST http://localhost:8000/api/consultor/ \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"mensagem":"meu carro está fazendo barulho na roda"}'

# 4. Integração externa (API Key, sem JWT) — atualização em lote
curl -X POST http://localhost:8000/api/integracao/estoque/ \
  -H "X-API-KEY: $INTEGRATION_API_KEY" -H "Content-Type: application/json" \
  -d '{"atualizacoes":[{"id":1,"quantidade":100},{"id":2,"quantidade":5,"operacao":"incrementar"}]}'
```

## Testes

```bash
pytest                 # todos os testes
pytest apps/consultor  # apenas o consultor
pytest -v              # verboso
```

Os testes cobrem: CRUD e permissões de peças, upload/import assíncrono, reposição
de estoque (cronjob), o consultor de IA (**com mock** da chamada ao Gemini) e a
integração externa (401/404, lote). Nenhum teste faz chamada real à API de IA.
