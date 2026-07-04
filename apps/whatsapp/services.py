"""Integração com a Evolution API (WhatsApp não oficial).

Responsável por:
- interpretar o payload de webhook de mensagem recebida;
- formatar a resposta do consultor de IA para texto de WhatsApp;
- enviar mensagens de volta pela Evolution API.

A Evolution API expõe endpoints REST autenticados por uma `apikey` no header.
Envio de texto: `POST {EVOLUTION_API_URL}/message/sendText/{instance}` com corpo
`{"number": "<jid>", "text": "<mensagem>"}`.
"""
from __future__ import annotations

import logging

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class EvolutionError(Exception):
    """Falha ao comunicar com a Evolution API."""


def _apenas_digitos(valor: str) -> str:
    """Extrai só os dígitos de um JID/número (ex.: '5511999@s.whatsapp.net')."""
    return "".join(filter(str.isdigit, valor))


def extrair_mensagem(payload: dict) -> dict | None:
    """Extrai remetente e texto de um webhook `messages.upsert` da Evolution.

    Retorna `None` para eventos que não devem ser respondidos (mensagens
    enviadas por nós mesmos, sem texto, de outra instância, de grupos, ou de
    números fora da allowlist quando ela está configurada).
    """
    instancia = payload.get("instance")
    if settings.EVOLUTION_INSTANCE and instancia and instancia != settings.EVOLUTION_INSTANCE:
        logger.debug("Ignorando webhook de instância '%s'.", instancia)
        return None

    data = payload.get("data") or {}
    key = data.get("key") or {}
    if key.get("fromMe"):  # evita responder às próprias mensagens (loop)
        return None

    mensagem = data.get("message") or {}
    texto = mensagem.get("conversation") or (
        mensagem.get("extendedTextMessage") or {}
    ).get("text")
    numero = key.get("remoteJid")
    if not texto or not numero:
        return None

    # Só conversas 1:1: ignora grupos (@g.us), broadcast/status e newsletters.
    if not numero.endswith("@s.whatsapp.net"):
        logger.debug("Ignorando mensagem de origem não-1:1 '%s'.", numero)
        return None

    # Allowlist opcional: se configurada, responde apenas aos números listados.
    if settings.WHATSAPP_ALLOWLIST and _apenas_digitos(numero) not in settings.WHATSAPP_ALLOWLIST:
        logger.info("Número '%s' fora da allowlist; ignorado.", numero)
        return None

    return {"numero": numero, "texto": texto.strip(), "nome": data.get("pushName", "")}


def formatar_resposta(resultado: dict) -> str:
    """Formata a saída do consultor (`resposta` + `pecas`) como texto de WhatsApp."""
    linhas = [resultado.get("resposta", "").strip()]
    pecas = resultado.get("pecas") or []
    if pecas:
        linhas.append("")
        linhas.append("*Peças sugeridas:*")
        for p in pecas:
            linhas.append(
                f"• {p.nome} — R$ {p.preco} ({p.quantidade} em estoque) — {p.fornecedor}"
            )
    else:
        linhas.append("")
        linhas.append("Não encontrei peças no estoque para esse pedido.")
    return "\n".join(linha for linha in linhas if linha is not None).strip()


def enviar_texto(numero: str, texto: str) -> dict:
    """Envia uma mensagem de texto via Evolution API."""
    if not settings.EVOLUTION_API_URL or not settings.EVOLUTION_API_KEY:
        raise EvolutionError("Evolution API não configurada (URL/API key ausentes).")

    url = (
        f"{settings.EVOLUTION_API_URL.rstrip('/')}"
        f"/message/sendText/{settings.EVOLUTION_INSTANCE}"
    )
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": numero, "text": texto}

    try:
        resposta = httpx.post(url, json=payload, headers=headers, timeout=30)
        resposta.raise_for_status()
    except httpx.HTTPError as exc:
        raise EvolutionError(f"Falha ao enviar mensagem via Evolution: {exc}") from exc
    return resposta.json() if resposta.content else {}
