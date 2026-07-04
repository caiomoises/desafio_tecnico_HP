"""Fixtures compartilhadas dos testes."""
import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.marketplace.models import Peca


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario_comum(db):
    return User.objects.create_user(username="cliente", password="senha12345")


@pytest.fixture
def usuario_admin(db):
    return User.objects.create_user(
        username="admin", password="senha12345", is_staff=True, is_superuser=True
    )


@pytest.fixture
def client_comum(api_client, usuario_comum):
    api_client.force_authenticate(user=usuario_comum)
    return api_client


@pytest.fixture
def client_admin(api_client, usuario_admin):
    api_client.force_authenticate(user=usuario_admin)
    return api_client


@pytest.fixture
def peca(db):
    return Peca.objects.create(
        nome="Filtro de Óleo",
        descricao="Filtro para retenção de impurezas no óleo do motor",
        preco="45.90",
        quantidade=50,
        fornecedor="Distribuidora Norte",
    )


@pytest.fixture
def pecas_sinonimos(db):
    """Mesma peça física com nomes distintos em fornecedores diferentes."""
    return [
        Peca.objects.create(
            nome="Filtro de Óleo",
            descricao="Filtro para retenção de impurezas no óleo do motor",
            preco="45.90",
            quantidade=50,
            fornecedor="Distribuidora Norte",
        ),
        Peca.objects.create(
            nome="Filtro do Motor",
            descricao="Filtro de óleo lubrificante do motor a combustão",
            preco="47.00",
            quantidade=45,
            fornecedor="Sul Auto",
        ),
        Peca.objects.create(
            nome="Elemento Filtrante de Óleo",
            descricao="Cartucho filtrante para o óleo lubrificante",
            preco="44.50",
            quantidade=55,
            fornecedor="Centro Oeste Peças",
        ),
    ]
