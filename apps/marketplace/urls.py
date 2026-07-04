"""Rotas do marketplace."""
from rest_framework.routers import DefaultRouter

from .views import ImportacaoCatalogoViewSet, PecaViewSet

router = DefaultRouter()
router.register(r"pecas", PecaViewSet, basename="peca")
router.register(r"importacoes", ImportacaoCatalogoViewSet, basename="importacao")

urlpatterns = router.urls
