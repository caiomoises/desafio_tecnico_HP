"""Filtros de listagem de peças."""
import django_filters as filters
from django.db.models import F

from .models import Peca


class PecaFilter(filters.FilterSet):
    preco_min = filters.NumberFilter(field_name="preco", lookup_expr="gte")
    preco_max = filters.NumberFilter(field_name="preco", lookup_expr="lte")
    disponivel = filters.BooleanFilter(method="filter_disponivel")
    estoque_baixo = filters.BooleanFilter(method="filter_estoque_baixo")

    class Meta:
        model = Peca
        fields = ["fornecedor", "ativo", "preco_min", "preco_max", "disponivel", "estoque_baixo"]

    def filter_disponivel(self, queryset, name, value):
        """`disponivel=true` retorna apenas peças ativas com estoque > 0."""
        if value is True:
            return queryset.filter(ativo=True, quantidade__gt=0)
        if value is False:
            return queryset.filter(quantidade=0)
        return queryset

    def filter_estoque_baixo(self, queryset, name, value):
        """`estoque_baixo=true` retorna peças ativas com quantidade < estoque_minimo."""
        if value is True:
            return queryset.filter(ativo=True, quantidade__lt=F("estoque_minimo"))
        if value is False:
            return queryset.filter(quantidade__gte=F("estoque_minimo"))
        return queryset
