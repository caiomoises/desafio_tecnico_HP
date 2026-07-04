"""
Configurações do Django para o projeto do Desafio Técnico Hubbi.

As configurações sensíveis e específicas de ambiente são lidas de variáveis de
ambiente (ver `.env.example`). Para desenvolvimento local usamos `python-dotenv`
para carregar um arquivo `.env` da raiz do projeto.
"""
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de um arquivo .env na raiz, se existir.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Segurança ---
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insecure-key-troque-em-producao")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

# --- Aplicações ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.marketplace",
    "apps.consultor",
    "apps.integracao",
    "apps.whatsapp",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Banco de dados (PostgreSQL) ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "desafio_tecnico"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# --- Validação de senha ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internacionalização ---
LANGUAGE_CODE = "pt-br"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

# --- Arquivos estáticos ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Django REST Framework ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
}

# --- JWT (SimpleJWT) ---
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "60"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", "7"))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --- drf-spectacular (OpenAPI) ---
SPECTACULAR_SETTINGS = {
    "TITLE": "Hubbi · Consultor de IA para Marketplace de Autopeças",
    "DESCRIPTION": "API RESTful com marketplace de autopeças, import assíncrono, "
    "consultor de IA (Gemini) e integração externa via API Key.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Celery ---
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Intervalo (em minutos) do cronjob de reposição de estoque.
RESTOCK_INTERVAL_MINUTES = int(os.getenv("RESTOCK_INTERVAL_MINUTES", "60"))

# --- Configurações da IA (Gemini) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Máximo de peças candidatas enviadas como contexto para o LLM.
CONSULTOR_MAX_CANDIDATOS = int(os.getenv("CONSULTOR_MAX_CANDIDATOS", "25"))

# --- Integração externa (API Key) ---
INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")
INTEGRATION_API_KEY_HEADER = os.getenv("INTEGRATION_API_KEY_HEADER", "X-API-KEY")

# --- Canal WhatsApp (Evolution API) ---
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "")
# Token validado no header do webhook para autenticar chamadas da Evolution.
WHATSAPP_WEBHOOK_TOKEN = os.getenv("WHATSAPP_WEBHOOK_TOKEN", "")
# Allowlist opcional de números (só os dígitos, ex.: "5511999998888").
# Vazia = responde a todos os contatos 1:1; preenchida = responde só a esses.
WHATSAPP_ALLOWLIST = [
    "".join(filter(str.isdigit, n))
    for n in os.getenv("WHATSAPP_ALLOWLIST", "").split(",")
    if n.strip()
]

# --- Uploads ---
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# Limite de tamanho do CSV de importação (bytes). Default: 5 MB.
IMPORT_MAX_FILE_SIZE = int(os.getenv("IMPORT_MAX_FILE_SIZE", str(5 * 1024 * 1024)))

# --- Logging ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
