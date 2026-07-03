"""Endpoint de integração externa: atualização de estoque em lote via API Key."""
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.marketplace.models import Peca

from .authentication import APIKeyAuthentication
from .serializers import AtualizacaoEstoqueLoteSerializer


class AtualizacaoEstoqueView(APIView):
    """POST /api/integracao/estoque/ — atualiza estoque em lote (ERP/WMS).

    Autenticação exclusiva por API Key (sem JWT). Suporta múltiplas peças numa
    única chamada. Cada item pode definir, incrementar ou decrementar o estoque.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=AtualizacaoEstoqueLoteSerializer,
        responses={200: None, 401: None, 404: None},
        description="Atualiza o estoque de várias peças em lote. Requer o header de "
        "API Key. Retorna 404 quando nenhuma peça informada existe; 200 (com detalhes "
        "por item) quando pelo menos uma foi atualizada.",
    )
    def post(self, request):
        entrada = AtualizacaoEstoqueLoteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        itens = entrada.validated_data["atualizacoes"]

        atualizadas, nao_encontradas = [], []

        with transaction.atomic():
            for item in itens:
                peca = (
                    Peca.objects.select_for_update()
                    .filter(pk=item["id"])
                    .first()
                )
                if peca is None:
                    nao_encontradas.append(item["id"])
                    continue

                anterior = peca.quantidade
                operacao = item["operacao"]
                if operacao == "definir":
                    nova = item["quantidade"]
                elif operacao == "incrementar":
                    nova = anterior + item["quantidade"]
                else:  # decrementar
                    nova = max(0, anterior - item["quantidade"])

                peca.quantidade = nova
                peca.save(update_fields=["quantidade", "atualizado_em"])
                atualizadas.append(
                    {
                        "id": peca.id,
                        "nome": peca.nome,
                        "operacao": operacao,
                        "quantidade_anterior": anterior,
                        "quantidade_atual": nova,
                    }
                )

        corpo = {
            "atualizadas": atualizadas,
            "nao_encontradas": nao_encontradas,
            "total_atualizadas": len(atualizadas),
            "total_nao_encontradas": len(nao_encontradas),
        }

        # Se nenhuma peça informada existe, é um 404 claro.
        if not atualizadas and nao_encontradas:
            corpo["detail"] = "Nenhuma das peças informadas foi encontrada."
            return Response(corpo, status=status.HTTP_404_NOT_FOUND)

        return Response(corpo, status=status.HTTP_200_OK)
