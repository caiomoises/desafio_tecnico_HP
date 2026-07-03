"""Tarefas assíncronas do marketplace (Celery)."""
import logging

from celery import shared_task

from .models import ImportacaoCatalogo
from .services import aplicar_reposicoes, importar_catalogo, listar_estoque_baixo

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def processar_importacao_catalogo(self, importacao_id: int):
    """Processa de forma assíncrona uma importação de catálogo (CSV)."""
    try:
        importacao = ImportacaoCatalogo.objects.get(pk=importacao_id)
    except ImportacaoCatalogo.DoesNotExist:
        logger.error("Importação %s não encontrada.", importacao_id)
        return {"erro": "importacao_nao_encontrada", "id": importacao_id}

    importacao.status = ImportacaoCatalogo.Status.PROCESSANDO
    importacao.save(update_fields=["status", "atualizado_em"])

    try:
        conteudo = importacao.arquivo.read()
        resultado = importar_catalogo(conteudo, importacao.fornecedor)
    except Exception as exc:  # noqa: BLE001 — registrar e marcar como erro
        logger.exception("Falha ao importar catálogo %s", importacao_id)
        importacao.status = ImportacaoCatalogo.Status.ERRO
        importacao.detalhe = str(exc)
        importacao.save(update_fields=["status", "detalhe", "atualizado_em"])
        return {"erro": str(exc), "id": importacao_id}

    importacao.status = ImportacaoCatalogo.Status.CONCLUIDA
    importacao.total_linhas = resultado.total_linhas
    importacao.linhas_criadas = resultado.criadas
    importacao.linhas_atualizadas = resultado.atualizadas
    importacao.erros = resultado.erros
    importacao.detalhe = (
        f"{resultado.criadas} criada(s), {resultado.atualizadas} atualizada(s), "
        f"{len(resultado.erros)} erro(s)."
    )
    importacao.save()
    logger.info("Importação %s concluída: %s", importacao_id, importacao.detalhe)
    return {
        "id": importacao_id,
        "criadas": resultado.criadas,
        "atualizadas": resultado.atualizadas,
        "erros": len(resultado.erros),
    }


@shared_task
def aplicar_reposicao_peca(peca_id: int):
    """Aplica a reposição pendente de uma peça específica (disparada pelo admin)."""
    resultado = aplicar_reposicoes(ids=[peca_id])
    logger.info(
        "Reposição da peça %s: +%s unidade(s).",
        peca_id,
        resultado.unidades_adicionadas,
    )
    return {
        "pecas_repostas": resultado.pecas_repostas,
        "unidades_adicionadas": resultado.unidades_adicionadas,
    }


@shared_task
def monitorar_estoque_periodico():
    """Cronjob (Celery Beat): sinaliza peças com estoque baixo e aplica as
    reposições pendentes (rede de segurança caso alguma não tenha sido aplicada).
    """
    baixas = listar_estoque_baixo()
    if baixas:
        logger.warning(
            "Estoque baixo em %s peça(s): %s",
            len(baixas),
            ", ".join(f"{p.nome}({p.quantidade})" for p in baixas),
        )
    resultado = aplicar_reposicoes()
    if resultado.pecas_repostas:
        logger.info(
            "Reposições aplicadas: %s peça(s), +%s unidade(s).",
            resultado.pecas_repostas,
            resultado.unidades_adicionadas,
        )
    return {
        "estoque_baixo": len(baixas),
        "pecas_repostas": resultado.pecas_repostas,
        "unidades_adicionadas": resultado.unidades_adicionadas,
    }
