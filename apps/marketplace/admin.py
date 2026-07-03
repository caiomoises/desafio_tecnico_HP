"""Configuração do Django Admin para o marketplace."""
from django.contrib import admin

from .models import ImportacaoCatalogo, Peca


@admin.register(Peca)
class PecaAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "fornecedor",
        "preco",
        "quantidade",
        "estoque_minimo",
        "reposicao",
        "estoque_baixo",
        "ativo",
    )
    list_filter = ("fornecedor", "ativo")
    search_fields = ("nome", "descricao", "fornecedor")
    list_editable = ("quantidade", "reposicao", "ativo")
    ordering = ("nome", "fornecedor")

    @admin.display(boolean=True, description="estoque baixo")
    def estoque_baixo(self, obj):
        return obj.estoque_baixo


@admin.register(ImportacaoCatalogo)
class ImportacaoCatalogoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "fornecedor",
        "status",
        "total_linhas",
        "linhas_criadas",
        "linhas_atualizadas",
        "criado_por",
        "criado_em",
    )
    list_filter = ("status", "fornecedor")
    readonly_fields = (
        "status",
        "total_linhas",
        "linhas_criadas",
        "linhas_atualizadas",
        "erros",
        "detalhe",
        "criado_em",
        "atualizado_em",
    )
