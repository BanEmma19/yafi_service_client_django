from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UtilisateurViewSet, TicketViewSet, MessageViewSet



router = DefaultRouter()
router.register(r'utilisateurs', UtilisateurViewSet, basename='utilisateur')
router.register(r'tickets', TicketViewSet)
router.register(r'messages', MessageViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
