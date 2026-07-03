"""Testes do Consultor de IA (chamada ao LLM é mockada)."""
import json

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

URL = reverse("consultor")


def test_consultor_exige_autenticacao(api_client):
    resp = api_client.post(URL, {"mensagem": "preciso de filtro de óleo"}, format="json")
    assert resp.status_code == 401


def test_consultor_valida_mensagem_curta(client_comum):
    resp = client_comum.post(URL, {"mensagem": "a"}, format="json")
    assert resp.status_code == 400


def test_consultor_sugere_pecas(client_comum, pecas_sinonimos, mocker):
    # O LLM escolhe as duas primeiras peças candidatas.
    ids = [p.id for p in pecas_sinonimos[:2]]
    fake = json.dumps({"peca_ids": ids, "resposta": "Recomendo estes filtros."})
    mocker.patch("apps.consultor.services._chamar_gemini", return_value=fake)

    resp = client_comum.post(URL, {"mensagem": "filtro do motor"}, format="json")

    assert resp.status_code == 200
    assert resp.data["resposta"] == "Recomendo estes filtros."
    assert len(resp.data["pecas"]) == 2
    # Preço/quantidade vêm do banco (fonte da verdade), com todos os campos exigidos.
    primeira = resp.data["pecas"][0]
    for campo in ("nome", "descricao", "preco", "quantidade"):
        assert campo in primeira


def test_consultor_ignora_ids_alucinados(client_comum, pecas_sinonimos, mocker):
    """IDs retornados pelo LLM que não estão entre as candidatas são descartados."""
    fake = json.dumps({"peca_ids": [999999], "resposta": "..."})
    mocker.patch("apps.consultor.services._chamar_gemini", return_value=fake)

    resp = client_comum.post(URL, {"mensagem": "filtro"}, format="json")
    assert resp.status_code == 200
    assert resp.data["pecas"] == []


def test_consultor_trata_sinonimos(client_comum, pecas_sinonimos, mocker):
    """As 3 peças são sinônimos; o consultor pode retornar todas como equivalentes."""
    ids = [p.id for p in pecas_sinonimos]
    fake = json.dumps(
        {"peca_ids": ids, "resposta": "São a mesma peça em fornecedores diferentes."}
    )
    mocker.patch("apps.consultor.services._chamar_gemini", return_value=fake)

    resp = client_comum.post(URL, {"mensagem": "elemento filtrante de óleo"}, format="json")
    assert resp.status_code == 200
    assert len(resp.data["pecas"]) == 3
    fornecedores = {p["fornecedor"] for p in resp.data["pecas"]}
    assert len(fornecedores) == 3


def test_consultor_retorna_503_quando_llm_indisponivel(client_comum, pecas_sinonimos, mocker):
    from apps.consultor.services import ConsultorIndisponivel

    mocker.patch(
        "apps.consultor.services._chamar_gemini",
        side_effect=ConsultorIndisponivel("sem chave"),
    )
    resp = client_comum.post(URL, {"mensagem": "filtro de óleo"}, format="json")
    assert resp.status_code == 503


def test_consultor_sem_estoque_nao_chama_llm(client_comum, mocker):
    spy = mocker.patch("apps.consultor.services._chamar_gemini")
    resp = client_comum.post(URL, {"mensagem": "qualquer peça"}, format="json")
    assert resp.status_code == 200
    assert resp.data["pecas"] == []
    spy.assert_not_called()
