"""Testes dos endpoints de peças (listagem, cadastro, edição, remoção)."""
import pytest
from django.urls import reverse

from apps.marketplace.models import Peca

pytestmark = pytest.mark.django_db


def test_listar_exige_autenticacao(api_client):
    resp = api_client.get(reverse("peca-list"))
    assert resp.status_code == 401


def test_usuario_comum_lista_pecas(client_comum, peca):
    resp = client_comum.get(reverse("peca-list"))
    assert resp.status_code == 200
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["nome"] == "Filtro de Óleo"


def test_detalhe_peca(client_comum, peca):
    resp = client_comum.get(reverse("peca-detail", args=[peca.id]))
    assert resp.status_code == 200
    assert resp.data["preco"] == "45.90"
    assert resp.data["quantidade"] == 50


def test_usuario_comum_nao_cria_peca(client_comum):
    payload = {"nome": "Vela", "preco": "22.00", "quantidade": 10, "fornecedor": "X"}
    resp = client_comum.post(reverse("peca-list"), payload)
    assert resp.status_code == 403
    assert Peca.objects.count() == 0


def test_admin_cria_peca(client_admin):
    payload = {
        "nome": "Vela de Ignição",
        "descricao": "Vela NGK",
        "preco": "22.00",
        "quantidade": 100,
        "fornecedor": "Distribuidora Norte",
    }
    resp = client_admin.post(reverse("peca-list"), payload)
    assert resp.status_code == 201
    assert Peca.objects.count() == 1


def test_admin_edita_peca(client_admin, peca):
    resp = client_admin.patch(
        reverse("peca-detail", args=[peca.id]), {"quantidade": 5}, format="json"
    )
    assert resp.status_code == 200
    peca.refresh_from_db()
    assert peca.quantidade == 5


def test_admin_remove_peca(client_admin, peca):
    resp = client_admin.delete(reverse("peca-detail", args=[peca.id]))
    assert resp.status_code == 204
    assert Peca.objects.count() == 0


def test_definir_reposicao_dispara_task(client_admin, peca, mocker):
    """Definir `reposicao` (> 0) via API deve enfileirar a task de reposição."""
    delay = mocker.patch("apps.marketplace.views.aplicar_reposicao_peca.delay")
    resp = client_admin.patch(
        reverse("peca-detail", args=[peca.id]), {"reposicao": 15}, format="json"
    )
    assert resp.status_code == 200
    delay.assert_called_once_with(peca.id)


def test_estoque_baixo_sinalizado_na_serializacao(client_comum):
    from apps.marketplace.models import Peca

    baixa = Peca.objects.create(
        nome="Radiador", preco="490.00", quantidade=2, fornecedor="Norte",
        estoque_minimo=5,
    )
    resp = client_comum.get(reverse("peca-detail", args=[baixa.id]))
    assert resp.status_code == 200
    assert resp.data["estoque_baixo"] is True


def test_filtro_disponivel(client_comum):
    Peca.objects.create(nome="A", preco="1.00", quantidade=0, fornecedor="F")
    Peca.objects.create(nome="B", preco="1.00", quantidade=5, fornecedor="F")
    resp = client_comum.get(reverse("peca-list"), {"disponivel": "true"})
    assert resp.status_code == 200
    nomes = [p["nome"] for p in resp.data["results"]]
    assert nomes == ["B"]
