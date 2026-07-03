"""Popula o banco com os 5 catálogos CSV fornecidos (uso local/demonstração)."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.marketplace.services import importar_catalogo

# Mapa arquivo -> nome de fornecedor amigável.
FORNECEDORES = {
    "catalogo_01_distribuidora_norte.csv": "Distribuidora Norte",
    "catalogo_02_sul_auto.csv": "Sul Auto",
    "catalogo_03_centro_oeste_pecas.csv": "Centro Oeste Peças",
    "catalogo_04_nordeste_auto.csv": "Nordeste Auto",
    "catalogo_05_sp_distribuidora.csv": "SP Distribuidora",
}


class Command(BaseCommand):
    help = "Importa os catálogos CSV da pasta catalogs/ para o banco de dados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=str(settings.BASE_DIR / "catalogs"),
            help="Diretório com os arquivos CSV de catálogo.",
        )

    def handle(self, *args, **options):
        base = Path(options["dir"])
        if not base.exists():
            self.stderr.write(self.style.ERROR(f"Diretório não encontrado: {base}"))
            return

        total_criadas = total_atualizadas = 0
        for arquivo, fornecedor in FORNECEDORES.items():
            caminho = base / arquivo
            if not caminho.exists():
                self.stdout.write(self.style.WARNING(f"Ignorando ausente: {arquivo}"))
                continue
            resultado = importar_catalogo(caminho.read_bytes(), fornecedor)
            total_criadas += resultado.criadas
            total_atualizadas += resultado.atualizadas
            self.stdout.write(
                f"  {fornecedor}: {resultado.criadas} criada(s), "
                f"{resultado.atualizadas} atualizada(s), {len(resultado.erros)} erro(s)."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed concluído: {total_criadas} criada(s), "
                f"{total_atualizadas} atualizada(s)."
            )
        )
