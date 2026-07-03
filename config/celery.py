"""Configuração da aplicação Celery."""
import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("desafio_tecnico")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.on_after_finalize.connect
def configurar_cronjobs(sender, **kwargs):
    """Registra o cronjob de reposição de estoque (Celery Beat)."""
    app.conf.beat_schedule = {
        "monitorar-estoque-periodico": {
            "task": "apps.marketplace.tasks.monitorar_estoque_periodico",
            # Executa a cada RESTOCK_INTERVAL_MINUTES minutos (padrão: 60).
            "schedule": settings.RESTOCK_INTERVAL_MINUTES * 60.0,
        }
    }


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
