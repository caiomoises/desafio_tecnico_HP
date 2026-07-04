"""Serviço do Consultor de IA.

Estratégia híbrida (pré-filtro + LLM):

1. **Pré-filtro no Postgres** — usa similaridade por trigramas (`pg_trgm`) entre a
   mensagem do usuário e os campos `nome`/`descricao` para selecionar as peças
   candidatas mais relevantes, reduzindo o contexto enviado ao LLM. Escala melhor
   que mandar o catálogo inteiro e ainda captura sinônimos/variações de escrita.
2. **LLM (Gemini)** — recebe as candidatas como contexto, interpreta a intenção do
   usuário (inclusive sintomas, ex.: "barulho na roda"), agrupa sinônimos e
   seleciona as peças mais adequadas, devolvendo os IDs escolhidos e uma resposta
   em linguagem natural.

O preço e a quantidade retornados ao cliente vêm sempre do banco (fonte da
verdade), nunca do texto gerado pelo LLM.
"""
from __future__ import annotations

import json
import logging

from django.conf import settings
from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import FloatField, Value
from django.db.models.functions import Greatest

from apps.marketplace.models import Peca

logger = logging.getLogger(__name__)


class ConsultorIndisponivel(Exception):
    """Erro recuperável: o LLM não pôde ser consultado (config/rede/resposta)."""


SYSTEM_PROMPT = (
    "Você é um consultor especialista em autopeças de um marketplace brasileiro. "
    "Sua função é, a partir da mensagem de um cliente (que pode descrever um "
    "sintoma, um problema ou pedir uma peça diretamente), recomendar as peças mais "
    "adequadas ESTRITAMENTE dentro da lista de peças disponíveis fornecida.\n\n"
    "Regras importantes:\n"
    "- Peças com nomes diferentes podem ser a MESMA peça física (sinônimos do "
    "mercado). Ex.: 'Filtro de Óleo', 'Filtro do Motor' e 'Elemento Filtrante de "
    "Óleo' são a mesma peça. Trate-as como equivalentes.\n"
    "- Só recomende peças presentes na lista. Nunca invente peças ou IDs.\n"
    "- Selecione apenas peças realmente relevantes para a necessidade do cliente.\n"
    "- Responda SEMPRE em português do Brasil, de forma objetiva e cordial.\n\n"
    "Responda SOMENTE com um JSON válido no formato:\n"
    '{"peca_ids": [<ids inteiros das peças recomendadas>], '
    '"resposta": "<explicação curta e útil para o cliente>"}'
)


def selecionar_candidatos(mensagem: str, limite: int | None = None) -> list[Peca]:
    """Pré-filtra as peças candidatas via similaridade por trigramas."""
    limite = limite or settings.CONSULTOR_MAX_CANDIDATOS
    similaridade = Greatest(
        TrigramWordSimilarity(mensagem, "nome"),
        TrigramWordSimilarity(mensagem, "descricao"),
        output_field=FloatField(),
    )
    qs = (
        Peca.objects.filter(ativo=True, quantidade__gt=0)
        .annotate(relevancia=similaridade)
        .order_by("-relevancia", "nome")
    )
    candidatos = list(qs[:limite])
    # Se nada teve similaridade relevante (ex.: mensagem muito genérica), ainda
    # assim devolvemos o topo para o LLM ter contexto com o que trabalhar.
    return candidatos


def _formatar_contexto(pecas: list[Peca]) -> str:
    linhas = [
        f"- id={p.id} | nome={p.nome} | fornecedor={p.fornecedor} | "
        f"preco=R${p.preco} | quantidade={p.quantidade} | descricao={p.descricao}"
        for p in pecas
    ]
    return "\n".join(linhas)


def _chamar_gemini(prompt: str) -> str:
    """Chama a API do Gemini e retorna o texto (JSON) da resposta.

    Isolado numa função própria para ser facilmente mockado nos testes.
    """
    if not settings.GEMINI_API_KEY:
        raise ConsultorIndisponivel(
            "GEMINI_API_KEY não configurada. Defina a variável de ambiente."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        resposta = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                response_mime_type="application/json",
            ),
        )
        return resposta.text or ""
    except ConsultorIndisponivel:
        raise
    except Exception as exc:  # noqa: BLE001 — normaliza qualquer erro do SDK/rede
        logger.exception("Erro ao chamar o Gemini")
        raise ConsultorIndisponivel(f"Falha ao consultar o modelo de IA: {exc}") from exc


def _extrair_json(texto: str) -> dict:
    texto = (texto or "").strip()
    # Remove cercas de código eventualmente adicionadas pelo modelo.
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise ConsultorIndisponivel("Resposta da IA não é um JSON válido.") from exc


def consultar(mensagem: str) -> dict:
    """Orquestra o consultor: pré-filtro -> LLM -> hidratação a partir do banco.

    Retorna um dict com `resposta` (texto), `pecas` (objetos Peca) e `modelo`.
    """
    candidatos = selecionar_candidatos(mensagem)
    if not candidatos:
        return {
            "resposta": "No momento não há peças disponíveis em estoque para atender "
            "à sua solicitação.",
            "pecas": [],
            "modelo": settings.GEMINI_MODEL,
        }

    prompt = (
        f"Mensagem do cliente: {mensagem}\n\n"
        f"Peças disponíveis no estoque:\n{_formatar_contexto(candidatos)}"
    )
    bruto = _chamar_gemini(prompt)
    dados = _extrair_json(bruto)

    ids = dados.get("peca_ids") or []
    # Mantém apenas IDs que realmente existem entre as candidatas (evita alucinação)
    # e preserva a ordem sugerida pelo LLM.
    candidatos_por_id = {p.id: p for p in candidatos}
    pecas = [candidatos_por_id[i] for i in ids if i in candidatos_por_id]

    return {
        "resposta": dados.get("resposta")
        or "Seguem as peças que podem atender à sua necessidade.",
        "pecas": pecas,
        "modelo": settings.GEMINI_MODEL,
    }
