"""Serializers do Consultor de IA."""
from rest_framework import serializers

from apps.marketplace.serializers import PecaSerializer


class ConsultaSerializer(serializers.Serializer):
    """Entrada do consultor: uma mensagem em texto livre."""

    mensagem = serializers.CharField(
        min_length=3,
        max_length=1000,
        trim_whitespace=True,
        help_text="Descreva o problema/sintoma ou a peça desejada.",
    )


class RespostaConsultaSerializer(serializers.Serializer):
    """Saída do consultor."""

    mensagem = serializers.CharField()
    resposta = serializers.CharField()
    pecas = PecaSerializer(many=True)
    modelo = serializers.CharField()
