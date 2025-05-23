"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from support.views import CustomTokenObtainPairView, UtilisateurViewSet, TicketViewSet, MessageViewSet, \
    agent_dashboard_stats, admin_agent_stats, admin_global_stats, generate_agents_report_data

# Création d'un router pour gérer automatiquement les routes des ViewSets
router = DefaultRouter()
router.register(r'utilisateurs', UtilisateurViewSet, basename='utilisateur')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'messages', MessageViewSet, basename='message')



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/agent/dashboard/', agent_dashboard_stats, name='agent_dashboard_stats'),
    path('api/admin/agent-stats/<int:agent_id>/', admin_agent_stats, name='agent-stats'),
    path('api/admin/global-stats/', admin_global_stats, name='admin-stats'),
    path('api/admin/rapport-agents/', generate_agents_report_data, name='generate_agents_report'),

    path('api/', include(router.urls)),  # Toutes les routes sont gérées ici
]


