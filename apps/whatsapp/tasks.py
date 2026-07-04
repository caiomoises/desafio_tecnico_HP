"""Tasks do canal WhatsApp."""
import logging

from celery import shared_task

from apps.consultor.services import ConsultorIndisponivel, consultar

from . import services

logger = logging.getLogger(__name__)

MSG_INDISPONIVEL = (
    "Desculpe, nosso consultor está indisponível no momento. "
    "Tente novamente em instantes. 🙏"
)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def processar_mensagem_whatsapp(self, numero: str, texto: str):
    """Consulta a IA para a mensagem recebida e responde pelo WhatsApp."""
    try:
        resultado = consultar(texto)
        resposta = services.formatar_resposta(resultado)
    except ConsultorIndisponivel as exc:
        logger.warning("Consultor indisponível para WhatsApp: %s", exc)
        resposta = MSG_INDISPONIVEL

    try:
        services.enviar_texto(numero, resposta)
    except services.EvolutionError as exc:
        logger.exception("Falha ao responder no WhatsApp")
        raise self.retry(exc=exc)

    return {"numero": numero, "ok": True}
