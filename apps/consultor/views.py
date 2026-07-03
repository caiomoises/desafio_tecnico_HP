"""View do Consultor de IA."""
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.marketplace.serializers import PecaSerializer

from .serializers import ConsultaSerializer, RespostaConsultaSerializer
from .services import ConsultorIndisponivel, consultar

logger = logging.getLogger(__name__)


class ConsultorView(APIView):
    """POST /api/consultor/ — recebe texto livre e sugere peças via IA."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ConsultaSerializer,
        responses={200: RespostaConsultaSerializer},
        description="Interpreta a mensagem do cliente com IA (Gemini) e retorna as "
        "peças mais relevantes do estoque, tratando sinônimos do mercado automotivo.",
    )
    def post(self, request):
        entrada = ConsultaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        mensagem = entrada.validated_data["mensagem"]

        try:
            resultado = consultar(mensagem)
        except ConsultorIndisponivel as exc:
            logger.warning("Consultor indisponível: %s", exc)
            return Response(
                {"detail": f"Consultor de IA indisponível no momento: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        corpo = {
            "mensagem": mensagem,
            "resposta": resultado["resposta"],
            "pecas": PecaSerializer(resultado["pecas"], many=True).data,
            "modelo": resultado["modelo"],
        }
        return Response(corpo, status=status.HTTP_200_OK)
