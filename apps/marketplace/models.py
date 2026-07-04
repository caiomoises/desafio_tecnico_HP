"""Modelos do marketplace de autopeças."""
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Peca(models.Model):
    """Uma peça de autopeça disponível no estoque.

    Cada linha de um catálogo (CSV) de fornecedor vira uma `Peca`. A mesma peça
    física aparece com nomes distintos entre fornecedores (sinônimos reais do
    mercado). O agrupamento de sinônimos é resolvido pelo Consultor de IA, não
    pela modelagem — por isso cada oferta é um registro independente.
    """

    nome = models.CharField("nome", max_length=200, db_index=True)
    descricao = models.TextField("descrição", blank=True)
    preco = models.DecimalField(
        "preço",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    quantidade = models.PositiveIntegerField("quantidade disponível", default=0)
    fornecedor = models.CharField(
        "fornecedor",
        max_length=120,
        db_index=True,
        help_text="Catálogo/fornecedor de origem da peça.",
    )

    # Nível mínimo: abaixo dele a peça é sinalizada como "estoque baixo".
    estoque_minimo = models.PositiveIntegerField(
        "estoque mínimo",
        default=5,
        help_text="Abaixo deste nível a peça é sinalizada como estoque baixo.",
    )
    # Ordem de reposição: valor a ser somado ao estoque pela task de reposição,
    # que zera este campo após aplicá-lo.
    reposicao = models.PositiveIntegerField(
        "reposição pendente",
        default=0,
        help_text="Quantidade a somar ao estoque. A task de reposição aplica e zera.",
    )

    ativo = models.BooleanField("ativo", default=True)

    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "peça"
        verbose_name_plural = "peças"
        ordering = ["nome", "fornecedor"]
        constraints = [
            models.UniqueConstraint(
                fields=["nome", "fornecedor"],
                name="uniq_peca_nome_fornecedor",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.fornecedor})"

    @property
    def estoque_baixo(self) -> bool:
        """Sinaliza que a peça está com estoque abaixo do mínimo."""
        return self.ativo and self.quantidade < self.estoque_minimo


class ImportacaoCatalogo(models.Model):
    """Registro de uma importação assíncrona de catálogo (CSV) via Celery."""

    class Status(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        PROCESSANDO = "PROCESSANDO", "Processando"
        CONCLUIDA = "CONCLUIDA", "Concluída"
        ERRO = "ERRO", "Erro"

    arquivo = models.FileField("arquivo CSV", upload_to="importacoes/")
    fornecedor = models.CharField("fornecedor", max_length=120)
    status = models.CharField(
        "status", max_length=20, choices=Status.choices, default=Status.PENDENTE
    )
    total_linhas = models.PositiveIntegerField("total de linhas", default=0)
    linhas_criadas = models.PositiveIntegerField("linhas criadas", default=0)
    linhas_atualizadas = models.PositiveIntegerField("linhas atualizadas", default=0)
    erros = models.JSONField("erros", default=list, blank=True)
    detalhe = models.TextField("detalhe", blank=True)

    criado_por = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importacoes",
    )
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "importação de catálogo"
        verbose_name_plural = "importações de catálogo"
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"Importação #{self.pk} — {self.fornecedor} ({self.status})"
