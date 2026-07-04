# CLAUDE.md

Orientações para agentes (Claude Code) trabalharem neste repositório.

## O que é o projeto

API RESTful (desafio técnico Hubbi) — um marketplace de autopeças com um
**Consultor de IA** que interpreta linguagem natural e sugere peças, tratando
sinônimos do mercado automotivo (ex.: "Filtro de Óleo" ≡ "Filtro do Motor" ≡
"Elemento Filtrante de Óleo").

## Stack

- **Django 5 + Django REST Framework**
- **PostgreSQL** (banco `desafio_tecnico`) — usa a extensão `pg_trgm`
- **Celery + Redis** — import de CSV assíncrono e cronjob de reposição de estoque
- **JWT** via `djangorestframework-simplejwt`
- **Gemini** (`google-genai`, modelo `gemini-2.5-flash`) para o consultor
- **Evolution API** (`httpx`) — canal WhatsApp para o consultor
- **pytest** (`pytest-django`, `pytest-mock`) para testes

## Arquitetura / organização

```
config/                 # projeto Django (settings, urls, celery, wsgi/asgi)
apps/
  marketplace/          # Peca, ImportacaoCatalogo, CRUD, upload CSV, tasks
    services.py         # regras puras: importar_catalogo(), aplicar_reposicoes()
    tasks.py            # tasks Celery (import assíncrono, cronjob reposição)
    management/commands/seed_catalogos.py
  consultor/            # Consultor de IA (requisito principal)
    services.py         # pré-filtro trigram + chamada ao Gemini (mockável)
  integracao/           # atualização de estoque em lote via API Key (sem JWT)
    authentication.py   # APIKeyAuthentication
  whatsapp/             # canal WhatsApp via Evolution API (webhook + Celery)
    services.py         # cliente Evolution (enviar_texto), parse/format
catalogs/               # os 5 CSVs fornecidos
```

## Convenções

- **Idioma:** domínio, modelos, mensagens e docstrings em **português**. Código
  segue o estilo do entorno (nomes de campo em pt: `nome`, `preco`, `quantidade`).
- **Regras de negócio** ficam em `services.py` (funções puras, testáveis), não nas
  views nem nas tasks. Tasks e views apenas orquestram.
- **Permissões:** leitura = qualquer autenticado; escrita = admin (`is_staff`).
  Ver `apps/marketplace/permissions.py::IsAdminOrReadOnly`.
- **Consultor:** o preço/quantidade retornados ao cliente vêm SEMPRE do banco,
  nunca do texto do LLM. A chamada ao Gemini está isolada em
  `apps.consultor.services._chamar_gemini` — mocke essa função nos testes.
- **Integração externa:** autenticação por API Key em header (`X-API-KEY`),
  configurável por env. 401 para chave ausente/inválida; 404 quando nenhuma peça
  do lote existe.

## Comandos

```bash
# ambiente
source /home/caiio/ativ-tecnica/venv/bin/activate

# migrations / seed
python manage.py migrate
python manage.py seed_catalogos          # popula com os 5 catálogos
python manage.py createsuperuser

# rodar
python manage.py runserver
celery -A config worker -l info          # worker
celery -A config beat -l info            # cronjob (reposição)

# testes
pytest                                   # todos
pytest apps/consultor                    # de um app
```

## Ao alterar

- Mexeu em modelo? Rode `makemigrations` e inclua a migration.
- Novo endpoint? Mantenha o padrão DRF (serializer + status codes corretos) e
  adicione teste correspondente.
- A extensão `pg_trgm` é habilitada por `marketplace/migrations/0002_pg_trgm.py`;
  não remova — o consultor depende dela.
