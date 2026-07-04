"""Views do marketplace de autopeças."""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .filters import PecaFilter
from .models import ImportacaoCatalogo, Peca
from .permissions import IsAdminOrReadOnly
from .serializers import (
    ImportacaoCatalogoSerializer,
    PecaSerializer,
    UploadCatalogoSerializer,
)
from .tasks import aplicar_reposicao_peca, processar_importacao_catalogo


class PecaViewSet(viewsets.ModelViewSet):
    """CRUD de peças.

    - Leitura (list/retrieve): qualquer usuário autenticado.
    - Escrita (create/update/delete): apenas admin (is_staff).

    Ao definir o campo `reposicao` (> 0), dispara-se de forma assíncrona a task
    que soma o valor ao estoque e zera o campo.
    """

    queryset = Peca.objects.all()
    serializer_class = PecaSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_class = PecaFilter
    search_fields = ["nome", "descricao", "fornecedor"]
    ordering_fields = ["nome", "preco", "quantidade", "criado_em"]

    def perform_create(self, serializer):
        peca = serializer.save()
        if peca.reposicao > 0:
            aplicar_reposicao_peca.delay(peca.id)

    def perform_update(self, serializer):
        peca = serializer.save()
        if peca.reposicao > 0:
            aplicar_reposicao_peca.delay(peca.id)

    @extend_schema(
        request=UploadCatalogoSerializer,
        responses={202: ImportacaoCatalogoSerializer},
        description="Upload de catálogo CSV. Processado de forma assíncrona via Celery. "
        "Apenas admin. Retorna 202 com o registro de importação para acompanhamento.",
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="importar",
        permission_classes=[IsAdminUser],
        parser_classes=[MultiPartParser, FormParser],
    )
    def importar(self, request):
        """Recebe um CSV e dispara a importação assíncrona."""
        entrada = UploadCatalogoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        importacao = ImportacaoCatalogo.objects.create(
            arquivo=entrada.validated_data["arquivo"],
            fornecedor=entrada.validated_data["fornecedor"],
            criado_por=request.user,
        )
        processar_importacao_catalogo.delay(importacao.id)

        saida = ImportacaoCatalogoSerializer(importacao, context={"request": request})
        return Response(saida.data, status=status.HTTP_202_ACCEPTED)


class ImportacaoCatalogoViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta o status das importações de catálogo. Apenas admin."""

    queryset = ImportacaoCatalogo.objects.all()
    serializer_class = ImportacaoCatalogoSerializer
    permission_classes = [IsAdminUser]
