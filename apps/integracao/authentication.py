"""Autenticação por API Key para sistemas externos (ERP/WMS).

Não usa JWT: a credencial é uma API Key enviada em um header configurável
(`INTEGRATION_API_KEY_HEADER`, padrão `X-API-KEY`) e comparada, em tempo
constante, com o valor de `INTEGRATION_API_KEY` (variável de ambiente).
"""
import hmac

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class SistemaExterno:
    """Identidade mínima para um sistema externo autenticado por API Key."""

    is_authenticated = True
    is_active = True
    is_staff = False

    def __str__(self) -> str:  # pragma: no cover - representação trivial
        return "sistema-externo"


class APIKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        chave = request.headers.get(settings.INTEGRATION_API_KEY_HEADER)
        if not chave:
            # Sem credencial: deixa a permissão retornar 401 (via authenticate_header).
            return None

        esperada = settings.INTEGRATION_API_KEY
        if not esperada:
            raise AuthenticationFailed(
                "Integração via API Key não configurada no servidor."
            )
        if not hmac.compare_digest(chave, esperada):
            raise AuthenticationFailed("API Key inválida.")

        return (SistemaExterno(), chave)

    def authenticate_header(self, request):
        # Presença deste header faz o DRF responder 401 (e não 403) quando
        # nenhuma credencial válida é fornecida.
        return settings.INTEGRATION_API_KEY_HEADER
