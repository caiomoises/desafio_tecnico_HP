"""Serializers do marketplace."""
from django.conf import settings
from rest_framework import serializers

from .models import ImportacaoCatalogo, Peca


class PecaSerializer(serializers.ModelSerializer):
    estoque_baixo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Peca
        fields = [
            "id",
            "nome",
            "descricao",
            "preco",
            "quantidade",
            "fornecedor",
            "estoque_minimo",
            "reposicao",
            "estoque_baixo",
            "ativo",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = ["id", "criado_em", "atualizado_em", "estoque_baixo"]


class ImportacaoCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportacaoCatalogo
        fields = [
            "id",
            "arquivo",
            "fornecedor",
            "status",
            "total_linhas",
            "linhas_criadas",
            "linhas_atualizadas",
            "erros",
            "detalhe",
            "criado_em",
            "atualizado_em",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_linhas",
            "linhas_criadas",
            "linhas_atualizadas",
            "erros",
            "detalhe",
            "criado_em",
            "atualizado_em",
        ]

    def validate_arquivo(self, arquivo):
        nome = (arquivo.name or "").lower()
        if not nome.endswith(".csv"):
            raise serializers.ValidationError("O arquivo deve ter extensão .csv.")
        if arquivo.size and arquivo.size > settings.IMPORT_MAX_FILE_SIZE:
            limite_mb = settings.IMPORT_MAX_FILE_SIZE / (1024 * 1024)
            raise serializers.ValidationError(
                f"Arquivo excede o tamanho máximo de {limite_mb:.0f} MB."
            )
        return arquivo


class UploadCatalogoSerializer(serializers.Serializer):
    """Entrada do endpoint de importação de catálogo."""

    arquivo = serializers.FileField()
    fornecedor = serializers.CharField(max_length=120)

    def validate_arquivo(self, arquivo):
        return ImportacaoCatalogoSerializer().validate_arquivo(arquivo)
