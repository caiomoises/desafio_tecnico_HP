"""Testes do endpoint de upload de catálogo (importação assíncrona)."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.marketplace.models import ImportacaoCatalogo

pytestmark = pytest.mark.django_db

URL = reverse("peca-importar")
CSV = b"nome,descricao,preco,quantidade_inicial\nFiltro,desc,45.90,50\n"


def test_upload_exige_admin(client_comum):
    arquivo = SimpleUploadedFile("cat.csv", CSV, content_type="text/csv")
    resp = client_comum.post(
        URL, {"arquivo": arquivo, "fornecedor": "Norte"}, format="multipart"
    )
    assert resp.status_code == 403


def test_admin_faz_upload_e_dispara_task(client_admin, mocker):
    delay = mocker.patch("apps.marketplace.views.processar_importacao_catalogo.delay")
    arquivo = SimpleUploadedFile("cat.csv", CSV, content_type="text/csv")

    resp = client_admin.post(
        URL, {"arquivo": arquivo, "fornecedor": "Norte"}, format="multipart"
    )

    assert resp.status_code == 202
    assert ImportacaoCatalogo.objects.count() == 1
    importacao = ImportacaoCatalogo.objects.first()
    assert importacao.status == ImportacaoCatalogo.Status.PENDENTE
    delay.assert_called_once_with(importacao.id)


def test_upload_rejeita_extensao_invalida(client_admin):
    arquivo = SimpleUploadedFile("cat.txt", b"conteudo", content_type="text/plain")
    resp = client_admin.post(
        URL, {"arquivo": arquivo, "fornecedor": "Norte"}, format="multipart"
    )
    assert resp.status_code == 400
