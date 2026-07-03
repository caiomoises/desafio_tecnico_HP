"""Rotas do Consultor de IA."""
from django.urls import path

from .views import ConsultorView

urlpatterns = [
    path("consultor/", ConsultorView.as_view(), name="consultor"),
]
