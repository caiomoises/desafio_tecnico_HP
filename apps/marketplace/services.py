"""Regras de negócio reutilizáveis do marketplace.

Mantidas fora de `tasks.py`/`views.py` para serem testáveis isoladamente e
compartilhadas entre a task Celery de importação e o comando de seed.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F

from .models import Peca

COLUNAS_OBRIGATORIAS = {"nome", "descricao", "preco", "quantidade_inicial"}


@dataclass
class ResultadoImportacao:
    total_linhas: int = 0
    criadas: int = 0
    atualizadas: int = 0
    erros: list[dict] = field(default_factory=list)


def _parse_decimal(valor: str) -> Decimal:
    """Converte string em Decimal aceitando formato BR ("1.234,56") e US ("45.90")."""
    texto = (valor or "").strip()
    if "," in texto:  # formato BR: '.' é separador de milhar, ',' é decimal
        texto = texto.replace(".", "").replace(",", ".")
    return Decimal(texto)


def importar_catalogo(conteudo: bytes | str, fornecedor: str) -> ResultadoImportacao:
    """Faz o parse de um CSV de catálogo e realiza upsert das peças.

    Idempotente por (nome, fornecedor): reimportar o mesmo catálogo atualiza as
    peças existentes em vez de duplicá-las.
    """
    if isinstance(conteudo, bytes):
        texto = conteudo.decode("utf-8-sig")
    else:
        texto = conteudo

    leitor = csv.DictReader(io.StringIO(texto))
    resultado = ResultadoImportacao()

    cabecalho = {c.strip() for c in (leitor.fieldnames or [])}
    faltando = COLUNAS_OBRIGATORIAS - cabecalho
    if faltando:
        raise ValueError(
            f"CSV inválido: colunas obrigatórias ausentes: {', '.join(sorted(faltando))}."
        )

    for numero, linha in enumerate(leitor, start=2):  # linha 1 é o cabeçalho
        resultado.total_linhas += 1
        try:
            nome = (linha.get("nome") or "").strip()
            if not nome:
                raise ValueError("campo 'nome' vazio")
            preco = _parse_decimal(linha.get("preco", ""))
            if preco < 0:
                raise ValueError("preço negativo")
            quantidade = int(str(linha.get("quantidade_inicial", "0")).strip() or "0")
            if quantidade < 0:
                raise ValueError("quantidade negativa")
            descricao = (linha.get("descricao") or "").strip()
        except (ValueError, InvalidOperation, TypeError) as exc:
            resultado.erros.append({"linha": numero, "erro": str(exc), "dados": linha})
            continue

        _, criado = Peca.objects.update_or_create(
            nome=nome,
            fornecedor=fornecedor,
            defaults={
                "descricao": descricao,
                "preco": preco,
                "quantidade": quantidade,
            },
        )
        if criado:
            resultado.criadas += 1
        else:
            resultado.atualizadas += 1

    return resultado


@dataclass
class ResultadoReposicao:
    pecas_repostas: int = 0
    unidades_adicionadas: int = 0
    detalhes: list[dict] = field(default_factory=list)


def aplicar_reposicoes(ids: list[int] | None = None) -> ResultadoReposicao:
    """Aplica as reposições pendentes: soma `reposicao` ao estoque e zera o campo.

    Se `ids` for informado, restringe às peças indicadas (usado quando o admin
    lança uma reposição pontual); caso contrário processa todas as pendentes
    (varredura periódica do cronjob). Idempotente: peças com `reposicao=0` são
    ignoradas, então reexecutar não duplica.
    """
    resultado = ResultadoReposicao()
    with transaction.atomic():
        pecas = Peca.objects.select_for_update().filter(reposicao__gt=0)
        if ids is not None:
            pecas = pecas.filter(id__in=ids)
        for peca in pecas:
            adicionar = peca.reposicao
            anterior = peca.quantidade
            peca.quantidade = anterior + adicionar
            peca.reposicao = 0
            peca.save(update_fields=["quantidade", "reposicao", "atualizado_em"])
            resultado.pecas_repostas += 1
            resultado.unidades_adicionadas += adicionar
            resultado.detalhes.append(
                {
                    "id": peca.id,
                    "nome": peca.nome,
                    "fornecedor": peca.fornecedor,
                    "de": anterior,
                    "para": peca.quantidade,
                }
            )
    return resultado


def listar_estoque_baixo() -> list[Peca]:
    """Sinalização: peças ativas com estoque abaixo do mínimo (sem alterá-las)."""
    return list(
        Peca.objects.filter(ativo=True, quantidade__lt=F("estoque_minimo")).order_by(
            "quantidade"
        )
    )
