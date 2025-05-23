from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils.timezone import now

# Définition des rôles possibles
ROLES = (
    ('client', 'Client'),
    ('agent', 'Agent'),
    ('admin', 'Administrateur'),
)


class UtilisateurManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        extra_fields.setdefault('role', 'client')  # Définit 'client' par défaut
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # Hash du mot de passe
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')  # Définit 'admin' pour les superusers
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    nom = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=20)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, choices=ROLES, default='client')  # Différenciation des rôles
    last_login = models.DateTimeField(default=now)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    groups = models.ManyToManyField("auth.Group", related_name="utilisateur_groups", blank=True)
    user_permissions = models.ManyToManyField("auth.Permission", related_name="utilisateur_permissions", blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom', 'role']

    objects = UtilisateurManager()

    def __str__(self):
        return f"{self.nom} ({self.role})"

    def save(self, *args, **kwargs):
        # Supprime la logique de hachage ici (déjà gérée par create_user/set_password)
        super().save(*args, **kwargs)


class Ticket(models.Model):
    STATUTS = [
        ('ASSIGNÉ', 'Assigné'),
        ('EN COURS', 'En cours'),
        ('RÉSOLU', 'Résolu'),
        ('REJETÉ', 'Rejeté'),
    ]
    titre = models.CharField(max_length=255, default="Problème de commande")
    description = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='Assigné')
    client = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        limit_choices_to={'role': 'client'},
        related_name='tickets_client'
    )
    agent = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'agent'},
        related_name='tickets_agent'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)


class Message(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    contenu = models.TextField()
    auteur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)  # L'auteur est un utilisateur (client ou agent)
    date_envoi = models.DateTimeField(auto_now_add=True)
