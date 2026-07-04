"""Permissões do marketplace."""
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Leitura para qualquer usuário autenticado; escrita apenas para admin.

    "Admin" aqui é `user.is_staff` — usuários comuns visualizam o catálogo,
    enquanto administradores cadastram, editam e removem peças.
    """

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_staff)
