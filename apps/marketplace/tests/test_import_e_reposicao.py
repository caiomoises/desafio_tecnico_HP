"""Testes de importação de catálogo (Celery) e reposição de estoque (cronjob)."""
import pytest

from apps.marketplace.models import ImportacaoCatalogo, Peca
from apps.marketplace.services import (
    aplicar_reposicoes,
    importar_catalogo,
    listar_estoque_baixo,
)
from apps.marketplace.tasks import (
    aplicar_reposicao_peca,
    monitorar_estoque_periodico,
    processar_importacao_catalogo,
)

pytestmark = pytest.mark.django_db

CSV_VALIDO = (
    "nome,descricao,preco,quantidade_inicial\n"
    "Filtro de Óleo,Filtro do motor,45.90,50\n"
    "Vela de Ignição,Vela NGK flex,22.00,100\n"
)


def test_importar_catalogo_cria_pecas():
    resultado = importar_catalogo(CSV_VALIDO, "Distribuidora Norte")
    assert resultado.total_linhas == 2
    assert resultado.criadas == 2
    assert Peca.objects.count() == 2
    filtro = Peca.objects.get(nome="Filtro de Óleo")
    assert str(filtro.preco) == "45.90"
    assert filtro.fornecedor == "Distribuidora Norte"


def test_importar_catalogo_e_idempotente():
    importar_catalogo(CSV_VALIDO, "Norte")
    resultado = importar_catalogo(CSV_VALIDO, "Norte")
    assert resultado.atualizadas == 2
    assert resultado.criadas == 0
    assert Peca.objects.count() == 2


def test_importar_catalogo_coleta_erros_de_linha():
    csv_ruim = (
        "nome,descricao,preco,quantidade_inicial\n"
        "Peça Ok,desc,10.00,5\n"
        ",desc,10.00,5\n"  # nome vazio
        "Peça Ruim,desc,abc,5\n"  # preço inválido
    )
    resultado = importar_catalogo(csv_ruim, "Norte")
    assert resultado.criadas == 1
    assert len(resultado.erros) == 2


def test_importar_catalogo_rejeita_colunas_faltando():
    with pytest.raises(ValueError):
        importar_catalogo("nome,preco\nX,10.00\n", "Norte")


def test_task_importacao_atualiza_status(tmp_path, django_user_model):
    from django.core.files.base import ContentFile

    importacao = ImportacaoCatalogo.objects.create(fornecedor="Norte")
    importacao.arquivo.save("cat.csv", ContentFile(CSV_VALIDO.encode("utf-8")))

    processar_importacao_catalogo(importacao.id)

    importacao.refresh_from_db()
    assert importacao.status == ImportacaoCatalogo.Status.CONCLUIDA
    assert importacao.linhas_criadas == 2
    assert Peca.objects.count() == 2


def test_estoque_baixo_e_sinalizado():
    baixa = Peca.objects.create(
        nome="Radiador", preco="490.00", quantidade=2, fornecedor="Norte",
        estoque_minimo=5,
    )
    ok = Peca.objects.create(
        nome="Vela", preco="22.00", quantidade=100, fornecedor="Norte",
        estoque_minimo=5,
    )
    assert baixa.estoque_baixo is True
    assert ok.estoque_baixo is False
    sinalizadas = listar_estoque_baixo()
    assert baixa in sinalizadas and ok not in sinalizadas


def test_aplicar_reposicoes_soma_e_zera_o_campo():
    peca = Peca.objects.create(
        nome="Radiador", preco="490.00", quantidade=2, fornecedor="Norte",
        estoque_minimo=5, reposicao=18,
    )
    sem_reposicao = Peca.objects.create(
        nome="Vela", preco="22.00", quantidade=100, fornecedor="Norte",
    )

    resultado = aplicar_reposicoes()

    peca.refresh_from_db(); sem_reposicao.refresh_from_db()
    assert peca.quantidade == 20  # 2 + 18
    assert peca.reposicao == 0  # zerado após aplicar
    assert sem_reposicao.quantidade == 100  # sem reposição pendente, inalterada
    assert resultado.pecas_repostas == 1
    assert resultado.unidades_adicionadas == 18


def test_aplicar_reposicoes_e_idempotente():
    peca = Peca.objects.create(
        nome="Radiador", preco="490.00", quantidade=2, fornecedor="Norte", reposicao=10,
    )
    aplicar_reposicoes()
    resultado = aplicar_reposicoes()  # segunda execução não deve somar de novo
    peca.refresh_from_db()
    assert peca.quantidade == 12
    assert resultado.pecas_repostas == 0


def test_task_aplicar_reposicao_peca():
    peca = Peca.objects.create(
        nome="Radiador", preco="490.00", quantidade=1, fornecedor="Norte", reposicao=9,
    )
    resultado = aplicar_reposicao_peca(peca.id)
    peca.refresh_from_db()
    assert peca.quantidade == 10
    assert peca.reposicao == 0
    assert resultado["unidades_adicionadas"] == 9


def test_cronjob_monitora_e_aplica():
    Peca.objects.create(
        nome="Radiador", preco="490.00", quantidade=2, fornecedor="Norte",
        estoque_minimo=5, reposicao=8,
    )
    Peca.objects.create(
        nome="Correia", preco="98.00", quantidade=1, fornecedor="Norte",
        estoque_minimo=5,  # baixa, mas sem reposição pendente -> só sinalizada
    )
    resultado = monitorar_estoque_periodico()
    assert resultado["pecas_repostas"] == 1
    assert resultado["unidades_adicionadas"] == 8
    # Correia (1) e Radiador antes de aplicar (2) estavam baixas: 2 sinalizadas.
    assert resultado["estoque_baixo"] == 2
