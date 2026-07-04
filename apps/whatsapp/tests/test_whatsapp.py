"""Testes do canal WhatsApp (Evolution API). HTTP e LLM são mockados."""
import pytest
from django.urls import reverse

from apps.whatsapp import services
from apps.whatsapp.services import extrair_mensagem, formatar_resposta
from apps.whatsapp.tasks import processar_mensagem_whatsapp

pytestmark = pytest.mark.django_db

URL = reverse("whatsapp-webhook")


def _payload(texto="preciso de filtro de óleo", from_me=False, numero="5511999@s.whatsapp.net"):
    return {
        "event": "messages.upsert",
        "instance": "consultor",
        "data": {
            "key": {"remoteJid": numero, "fromMe": from_me, "id": "ABC"},
            "pushName": "Cliente",
            "message": {"conversation": texto},
        },
    }


# --- extrair_mensagem ---

def test_extrair_mensagem_texto_simples(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    info = extrair_mensagem(_payload("filtro de óleo"))
    assert info == {"numero": "5511999@s.whatsapp.net", "texto": "filtro de óleo", "nome": "Cliente"}


def test_extrair_mensagem_ignora_from_me(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    assert extrair_mensagem(_payload(from_me=True)) is None


def test_extrair_mensagem_extended_text(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    payload = _payload()
    payload["data"]["message"] = {"extendedTextMessage": {"text": "barulho na roda"}}
    info = extrair_mensagem(payload)
    assert info["texto"] == "barulho na roda"


def test_extrair_mensagem_outra_instancia_ignorada(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    payload = _payload()
    payload["instance"] = "outra"
    assert extrair_mensagem(payload) is None


def test_extrair_mensagem_ignora_grupo(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    payload = _payload(numero="120363@g.us")
    assert extrair_mensagem(payload) is None


def test_extrair_mensagem_ignora_broadcast(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    payload = _payload(numero="status@broadcast")
    assert extrair_mensagem(payload) is None


def test_extrair_mensagem_allowlist_bloqueia_numero_de_fora(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    settings.WHATSAPP_ALLOWLIST = ["5511888887777"]
    payload = _payload(numero="5511999998888@s.whatsapp.net")
    assert extrair_mensagem(payload) is None


def test_extrair_mensagem_allowlist_permite_numero_listado(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    settings.WHATSAPP_ALLOWLIST = ["5511999998888"]
    payload = _payload(numero="5511999998888@s.whatsapp.net")
    info = extrair_mensagem(payload)
    assert info["numero"] == "5511999998888@s.whatsapp.net"


def test_extrair_mensagem_allowlist_vazia_responde_todos(settings):
    settings.EVOLUTION_INSTANCE = "consultor"
    settings.WHATSAPP_ALLOWLIST = []
    info = extrair_mensagem(_payload(numero="5511999998888@s.whatsapp.net"))
    assert info is not None


# --- formatar_resposta ---

def test_formatar_resposta_com_pecas(pecas_sinonimos):
    resultado = {"resposta": "Recomendo estes filtros.", "pecas": pecas_sinonimos}
    texto = formatar_resposta(resultado)
    assert "Recomendo estes filtros." in texto
    assert "Filtro de Óleo" in texto
    assert "R$ 45.90" in texto


def test_formatar_resposta_sem_pecas():
    texto = formatar_resposta({"resposta": "Não achei.", "pecas": []})
    assert "Não encontrei peças" in texto


# --- webhook ---

def test_webhook_enfileira_task(api_client, settings, mocker):
    settings.WHATSAPP_WEBHOOK_TOKEN = "segredo"
    settings.EVOLUTION_INSTANCE = "consultor"
    delay = mocker.patch("apps.whatsapp.views.processar_mensagem_whatsapp.delay")

    resp = api_client.post(URL, _payload("filtro"), format="json", HTTP_APIKEY="segredo")

    assert resp.status_code == 200
    delay.assert_called_once_with("5511999@s.whatsapp.net", "filtro")


def test_webhook_token_invalido_401(api_client, settings, mocker):
    settings.WHATSAPP_WEBHOOK_TOKEN = "segredo"
    delay = mocker.patch("apps.whatsapp.views.processar_mensagem_whatsapp.delay")

    resp = api_client.post(URL, _payload(), format="json", HTTP_APIKEY="errado")

    assert resp.status_code == 401
    delay.assert_not_called()


def test_webhook_from_me_nao_enfileira(api_client, settings, mocker):
    settings.WHATSAPP_WEBHOOK_TOKEN = ""
    settings.EVOLUTION_INSTANCE = "consultor"
    delay = mocker.patch("apps.whatsapp.views.processar_mensagem_whatsapp.delay")

    resp = api_client.post(URL, _payload(from_me=True), format="json")

    assert resp.status_code == 200  # ignorado, mas não é erro
    delay.assert_not_called()


# --- task ---

def test_task_consulta_e_envia(pecas_sinonimos, mocker):
    consultar = mocker.patch(
        "apps.whatsapp.tasks.consultar",
        return_value={"resposta": "Recomendo.", "pecas": pecas_sinonimos},
    )
    enviar = mocker.patch("apps.whatsapp.tasks.services.enviar_texto")

    processar_mensagem_whatsapp("5511999@s.whatsapp.net", "filtro de óleo")

    consultar.assert_called_once_with("filtro de óleo")
    enviar.assert_called_once()
    numero, texto = enviar.call_args.args
    assert numero == "5511999@s.whatsapp.net"
    assert "Recomendo." in texto


def test_task_llm_indisponivel_envia_mensagem_amigavel(mocker):
    from apps.consultor.services import ConsultorIndisponivel

    mocker.patch("apps.whatsapp.tasks.consultar", side_effect=ConsultorIndisponivel("x"))
    enviar = mocker.patch("apps.whatsapp.tasks.services.enviar_texto")

    processar_mensagem_whatsapp("5511999@s.whatsapp.net", "oi")

    texto = enviar.call_args.args[1]
    assert "indisponível" in texto.lower()


def test_enviar_texto_faz_post_correto(settings, mocker):
    settings.EVOLUTION_API_URL = "http://evo:8080"
    settings.EVOLUTION_API_KEY = "chave"
    settings.EVOLUTION_INSTANCE = "consultor"
    post = mocker.patch("apps.whatsapp.services.httpx.post")
    post.return_value.raise_for_status.return_value = None
    post.return_value.content = b"{}"
    post.return_value.json.return_value = {}

    services.enviar_texto("5511999@s.whatsapp.net", "olá")

    url = post.call_args.args[0]
    assert url == "http://evo:8080/message/sendText/consultor"
    assert post.call_args.kwargs["json"] == {"number": "5511999@s.whatsapp.net", "text": "olá"}
    assert post.call_args.kwargs["headers"]["apikey"] == "chave"


def test_enviar_texto_sem_config_erro(settings):
    settings.EVOLUTION_API_URL = ""
    with pytest.raises(services.EvolutionError):
        services.enviar_texto("5511999@s.whatsapp.net", "olá")
