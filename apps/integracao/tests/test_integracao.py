"""Testes do endpoint de integração externa (API Key + atualização em lote)."""
import pytest
from django.urls import reverse

from apps.marketplace.models import Peca

pytestmark = pytest.mark.django_db

URL = reverse("integracao-estoque")
API_KEY = "chave-de-teste-123"


@pytest.fixture(autouse=True)
def configura_api_key(settings):
    settings.INTEGRATION_API_KEY = API_KEY
    settings.INTEGRATION_API_KEY_HEADER = "X-API-KEY"


def _headers(chave=API_KEY):
    return {"HTTP_X_API_KEY": chave}


def test_sem_api_key_retorna_401(api_client):
    resp = api_client.post(
        URL, {"atualizacoes": [{"id": 1, "quantidade": 10}]}, format="json"
    )
    assert resp.status_code == 401


def test_api_key_invalida_retorna_401(api_client):
    resp = api_client.post(
        URL,
        {"atualizacoes": [{"id": 1, "quantidade": 10}]},
        format="json",
        **_headers("errada"),
    )
    assert resp.status_code == 401


def test_atualiza_estoque_definir(api_client):
    peca = Peca.objects.create(nome="Vela", preco="22.00", quantidade=10, fornecedor="N")
    resp = api_client.post(
        URL,
        {"atualizacoes": [{"id": peca.id, "quantidade": 99}]},
        format="json",
        **_headers(),
    )
    assert resp.status_code == 200
    peca.refresh_from_db()
    assert peca.quantidade == 99
    assert resp.data["total_atualizadas"] == 1


def test_atualiza_estoque_em_lote(api_client):
    p1 = Peca.objects.create(nome="A", preco="1.00", quantidade=10, fornecedor="N")
    p2 = Peca.objects.create(nome="B", preco="1.00", quantidade=10, fornecedor="N")
    payload = {
        "atualizacoes": [
            {"id": p1.id, "quantidade": 5, "operacao": "incrementar"},
            {"id": p2.id, "quantidade": 3, "operacao": "decrementar"},
        ]
    }
    resp = api_client.post(URL, payload, format="json", **_headers())
    assert resp.status_code == 200
    p1.refresh_from_db(); p2.refresh_from_db()
    assert p1.quantidade == 15
    assert p2.quantidade == 7


def test_decrementar_nao_fica_negativo(api_client):
    peca = Peca.objects.create(nome="A", preco="1.00", quantidade=2, fornecedor="N")
    resp = api_client.post(
        URL,
        {"atualizacoes": [{"id": peca.id, "quantidade": 10, "operacao": "decrementar"}]},
        format="json",
        **_headers(),
    )
    assert resp.status_code == 200
    peca.refresh_from_db()
    assert peca.quantidade == 0


def test_peca_inexistente_retorna_404(api_client):
    resp = api_client.post(
        URL,
        {"atualizacoes": [{"id": 999999, "quantidade": 10}]},
        format="json",
        **_headers(),
    )
    assert resp.status_code == 404
    assert 999999 in resp.data["nao_encontradas"]


def test_lote_parcial_retorna_200_com_detalhes(api_client):
    peca = Peca.objects.create(nome="A", preco="1.00", quantidade=10, fornecedor="N")
    payload = {
        "atualizacoes": [
            {"id": peca.id, "quantidade": 50},
            {"id": 999999, "quantidade": 5},
        ]
    }
    resp = api_client.post(URL, payload, format="json", **_headers())
    assert resp.status_code == 200
    assert resp.data["total_atualizadas"] == 1
    assert resp.data["total_nao_encontradas"] == 1
