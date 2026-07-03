"""Rotas da integração externa."""
from django.urls import path

from .views import AtualizacaoEstoqueView

urlpatterns = [
    path("integracao/estoque/", AtualizacaoEstoqueView.as_view(), name="integracao-estoque"),
]
