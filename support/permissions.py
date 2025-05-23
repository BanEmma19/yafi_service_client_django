from rest_framework import permissions
from rest_framework.permissions import BasePermission

class IsAdminOrSelf(BasePermission):
    """
    Permission pour autoriser :
    - Un utilisateur à modifier/supprimer son propre compte.
    - Les admins et superadmins à gérer tous les comptes.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated:
            if request.user.role in ["admin", "superadmin"]:
                return True  # Les admins/superadmins ont tous les droits
            return obj == request.user  # Un utilisateur peut modifier/supprimer son propre compte
        return False
class IsAdmin(permissions.BasePermission):
    """Permission pour les administrateurs uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsAgent(permissions.BasePermission):
    """Permission pour les agents de support."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'agent'

class IsClient(permissions.BasePermission):
    """Permission pour les clients uniquement."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'client'
