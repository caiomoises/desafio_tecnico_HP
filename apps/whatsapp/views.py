"""Webhook do canal WhatsApp (Evolution API)."""
import hmac
import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import extrair_mensagem
from .tasks import processar_mensagem_whatsapp

logger = logging.getLogger(__name__)


class WhatsAppWebhookView(APIView):
    """POST /api/whatsapp/webhook/ — recebe mensagens da Evolution API.

    Não usa JWT (é chamado por um sistema externo). A autenticidade é validada
    por um token compartilhado (`WHATSAPP_WEBHOOK_TOKEN`) enviado no header
    `apikey`. O processamento é assíncrono: o webhook enfileira a task e responde
    200 imediatamente, evitando reentregas por timeout.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses={200: None, 401: None},
        description="Webhook de mensagens recebidas do WhatsApp via Evolution API.",
    )
    def post(self, request):
        token = settings.WHATSAPP_WEBHOOK_TOKEN
        if token:
            recebido = request.headers.get("apikey") or request.headers.get(
                "X-Webhook-Token", ""
            )
            if not hmac.compare_digest(recebido or "", token):
                logger.warning("Webhook WhatsApp com token inválido.")
                return Response(
                    {"detail": "Token inválido."}, status=status.HTTP_401_UNAUTHORIZED
                )

        info = extrair_mensagem(request.data if isinstance(request.data, dict) else {})
        if info:
            processar_mensagem_whatsapp.delay(info["numero"], info["texto"])
            logger.info("Mensagem WhatsApp de %s enfileirada.", info["numero"])

        # Sempre 200: eventos ignorados (fromMe, sem texto) não são erro.
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
