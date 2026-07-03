"""Serializers da integração externa."""
from rest_framework import serializers


class AtualizacaoEstoqueItemSerializer(serializers.Serializer):
    """Um item de atualização de estoque."""

    OPERACOES = ("definir", "incrementar", "decrementar")

    id = serializers.IntegerField(min_value=1)
    quantidade = serializers.IntegerField(
        min_value=0,
        help_text="Valor da operação. Para 'definir' é o estoque absoluto; para "
        "'incrementar'/'decrementar' é o delta aplicado.",
    )
    operacao = serializers.ChoiceField(
        choices=OPERACOES,
        default="definir",
        help_text="definir (padrão), incrementar ou decrementar.",
    )


class AtualizacaoEstoqueLoteSerializer(serializers.Serializer):
    """Payload em lote para atualização de estoque."""

    atualizacoes = AtualizacaoEstoqueItemSerializer(many=True, allow_empty=False)
