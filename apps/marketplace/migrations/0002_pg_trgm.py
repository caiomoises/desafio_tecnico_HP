"""Habilita a extensão pg_trgm (usada pelo pré-filtro por trigramas do consultor)."""
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace", "0001_initial"),
    ]

    operations = [
        TrigramExtension(),
    ]
