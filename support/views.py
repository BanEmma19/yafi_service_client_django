import logging
from collections import Counter

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Count
from django.utils.timezone import now
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import Ticket, Message
from .serializers import TicketSerializer, MessageSerializer, UtilisateurSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework import generics, permissions
from support.models import Utilisateur
from .permissions import IsAdmin, IsAgent, IsClient, IsAdminOrSelf

# ✅ 1️⃣ Ajout de la permission personnalisée pour gérer les modifications
class IsOwnerOrAdmin(permissions.BasePermission):
    """
    - Un client peut modifier uniquement son propre compte.
    - Un agent peut modifier uniquement son propre compte.
    - Un admin peut gérer les agents et clients mais pas d'autres admins.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == "superadmin":
            return True  # Le superadmin peut tout faire

        if request.user.role == "admin":
            return obj.role != "admin"  # L'admin ne peut pas toucher un autre admin

        if request.user.role in ["client", "agent"]:
            return obj == request.user  # Un client/agent ne peut modifier que son propre compte

        return False  # Sinon, action interdite

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# ✅ 2️⃣ Correction des permissions pour UtilisateurViewSet
class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all()
    serializer_class = UtilisateurSerializer

    def get_permissions(self):
        """Assigne les bonnes permissions selon l'action demandée."""
        if self.action == 'create':
            return [AllowAny()]  # Tout le monde peut créer un compte (client uniquement)
        elif self.action == 'list':
            return [IsAdminOrSelf()]  # Seuls les admins et superadmins voient la liste
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]  # Un utilisateur peut voir/modifier son compte
        elif self.action == 'destroy':
            return [IsAuthenticated(), IsAdminOrSelf()]  # Un utilisateur peut supprimer son propre compte
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Contrôle la création des utilisateurs selon leur rôle."""
        user = self.request.user
        role = self.request.data.get("role", "client")  # Par défaut, un client

        if role == "admin" and (not user.is_authenticated or user.role != "superadmin"):
            raise PermissionDenied("Seuls les superadmins peuvent créer des admins.")
        if role == "agent" and (not user.is_authenticated or user.role not in ["superadmin", "admin"]):
            raise PermissionDenied("Seuls les superadmins et admins peuvent créer des agents.")
        if role == "client" and user.is_authenticated:
            raise PermissionDenied("Les clients doivent créer leur compte eux-mêmes.")

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Permet uniquement aux clients de supprimer leur propre compte, et aux superadmins de gérer les autres."""
        utilisateur = self.get_object()

        if utilisateur.role == "client" and utilisateur == request.user:
            return super().destroy(request, *args, **kwargs)
        elif request.user.role == "admin":
            return super().destroy(request, *args, **kwargs)
        else:
            raise PermissionDenied("Vous n'avez pas la permission de supprimer cet utilisateur.")

    def get_queryset(self):
        user = self.request.user

        if user.is_authenticated and user.role in ['admin', 'superadmin']:
            role = self.request.query_params.get('role', None)
            if role:
                return self.queryset.filter(role=role)
            return self.queryset
        else:
            # Empêche les clients de voir la liste
            return self.queryset.none()

    # Action personnalisée pour récupérer le profil de l'utilisateur connecté
    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """Permet à un utilisateur authentifié de changer son mot de passe"""
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not user.check_password(old_password):
            return Response({"error": "Ancien mot de passe incorrect."}, status=status.HTTP_400_BAD_REQUEST)

        if not new_password or len(new_password) < 6:
            return Response({"error": "Le nouveau mot de passe doit contenir au moins 6 caractères."},
                            status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Mot de passe changé avec succès."}, status=status.HTTP_200_OK)

logger = logging.getLogger(__name__)

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer

    def get_permissions(self):
        if self.action in ['create_ticket_chatbot']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAgent()]
        elif self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        ticket = serializer.save()
        logger.warning("[perform_create] Ticket créé via perform_create() pour : %s", ticket)
        self._broadcast_ticket("created", ticket)

    def perform_update(self, serializer):
        ticket = serializer.save()
        logger.info("[perform_update] Ticket mis à jour : %s", ticket)
        self._broadcast_ticket("updated", ticket)

    def perform_destroy(self, instance):
        logger.info("[perform_destroy] Ticket supprimé : %s", instance)
        self._broadcast_ticket("deleted", instance)
        instance.delete()

    def _broadcast_ticket(self, action, ticket):
        channel_layer = get_channel_layer()
        data = TicketSerializer(ticket).data
        logger.info("[broadcast] Action : %s | Ticket ID : %s", action, ticket.id)
        async_to_sync(channel_layer.group_send)(
            "tickets",
            {
                "type": "ticket_update",
                "content": {
                    "action": action,
                    "ticket": data
                }
            }
        )

    @action(detail=False, methods=['post'], url_path='create', permission_classes=[IsAuthenticated])
    def create_ticket_chatbot(self, request):
        """Endpoint appelé par le chatbot pour créer un ticket."""
        user = request.user
        logger.warning("[create_ticket_chatbot] Requête reçue de : %s", user)

        if user.role != 'client':
            raise PermissionDenied("Seuls les clients peuvent créer un ticket.")

        titre = request.data.get("titre")
        description = request.data.get("description")

        if not titre or not description:
            raise ValidationError("Le titre et la description sont obligatoires.")

        # Rechercher l’agent avec le moins de tickets assignés
        agent_le_moins_charge = Utilisateur.objects.filter(role='agent')\
            .annotate(nb_tickets=Count('tickets_agent'))\
            .order_by('nb_tickets')\
            .first()

        if not agent_le_moins_charge:
            raise ValidationError("Aucun agent disponible pour assignation.")

        logger.warning("[create_ticket_chatbot] Agent assigné : %s", agent_le_moins_charge)

        ticket = Ticket.objects.create(
            titre=titre,
            description=description,
            statut="Assigné",
            client=user,
            agent=agent_le_moins_charge
        )

        logger.warning("[create_ticket_chatbot] Ticket ID %s créé pour %s", ticket.id, user)

        self._broadcast_ticket("created", ticket)

        return Response({
            "titre": ticket.titre,
            "description": ticket.description,
            "statut": ticket.statut,
            "agent": agent_le_moins_charge.nom,
            "date_creation": ticket.date_creation,
            "date_modification": ticket.date_modification,
        })

    @action(detail=False, methods=['get'], url_path='mes-tickets', permission_classes=[IsAuthenticated])
    def mes_tickets(self, request):
        """Retourne uniquement les tickets du client connecté."""
        user = request.user
        if user.role != 'client':
            raise PermissionDenied("Seuls les clients peuvent accéder à leurs tickets.")

        tickets = Ticket.objects.filter(client=user).order_by('-date_creation')
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)

    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework.exceptions import PermissionDenied
    from django.db.models import Count

    # ... déjà dans ta classe TicketViewSet

    @action(detail=False, methods=['get'], url_path='agent', permission_classes=[IsAuthenticated])
    def tickets_agent(self, request):
        """Retourne les tickets assignés à l’agent connecté."""
        user = request.user
        if user.role != 'agent':
            raise PermissionDenied("Seuls les agents peuvent accéder à leurs tickets.")

        tickets = Ticket.objects.filter(agent=user).order_by('-date_creation')
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='changer-statut', permission_classes=[IsAuthenticated])
    def changer_statut(self, request, pk=None):
        """Permet à un agent de changer le statut d’un ticket qui lui est assigné."""
        user = request.user
        if user.role != 'agent':
            raise PermissionDenied("Seuls les agents peuvent modifier le statut d’un ticket.")

        ticket = self.get_object()

        if ticket.agent != user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres tickets.")

        nouveau_statut = request.data.get('statut')
        if nouveau_statut not in ['Assigné', 'En cours', 'Résolu', 'Rejeté']:
            return Response({"error": "Statut invalide."}, status=400)

        ticket.statut = nouveau_statut
        ticket.save()
        self._broadcast_ticket("updated", ticket)

        serializer = self.get_serializer(ticket)
        return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_dashboard_stats(request):
    agent = request.user
    year = request.GET.get('year', str(now().year))

    # Filtrage des tickets assignés à l’agent
    tickets = Ticket.objects.filter(agent=agent)

    total = tickets.count()
    en_cours = tickets.filter(statut='En cours').count()
    resolus = tickets.filter(statut='Résolu').count()
    rejetes = tickets.filter(statut='Rejeté').count()

    # Graphe : taux de résolution par mois (résolus / total du mois)
    monthly_stats = []
    for month in range(1, 13):
        month_tickets = tickets.filter(date_creation__year=year, date_creation__month=month)
        resolved_tickets = month_tickets.filter(statut='Résolu')
        total_count = month_tickets.count()
        resolved_count = resolved_tickets.count()
        resolution_rate = round((resolved_count / total_count) * 100, 2) if total_count else 0

        monthly_stats.append({
            'month': month,
            'resolved': resolved_count,
            'total': total_count,
            'resolution_rate': resolution_rate
        })

    return Response({
        'total_tickets': total,
        'en_cours': en_cours,
        'resolus': resolus,
        'rejetes': rejetes,
        'monthly_resolution_rate': monthly_stats
    })

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_agent_stats(request, agent_id):
    year = int(request.GET.get('year', now().year))
    month = request.GET.get('month')  # optionnel

    tickets = Ticket.objects.filter(agent_id=agent_id)

    if month is not None:
        month = int(month)
        tickets = tickets.filter(date_creation__year=year, date_creation__month=month)
    else:
        tickets = tickets.filter(date_creation__year=year)

    total = tickets.count()
    en_cours = tickets.filter(statut='En cours').count()
    resolus_qs = tickets.filter(statut='Résolu')
    resolus = resolus_qs.count()
    rejetes = tickets.filter(statut='Rejeté').count()

    # Taux de résolution
    resolution_rate = round((resolus / total) * 100, 2) if total else 0

    # Calcul du temps moyen de résolution en heures
    durations = []
    for ticket in resolus_qs:
        if ticket.date_creation and ticket.date_modification:
            delta = ticket.date_modification - ticket.date_creation
            durations.append(delta.total_seconds())

    average_resolution_time = round(sum(durations) / len(durations) / 3600, 2) if durations else 0

    return Response({
        'total_tickets': total,
        'en_cours': en_cours,
        'resolus': resolus,
        'rejetes': rejetes,
        'resolution_rate': resolution_rate,
        'average_resolution_time': average_resolution_time  # en heures
    })
from django.contrib.auth import get_user_model

# ...

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_global_stats(request):
    year = int(request.GET.get('year', now().year))

    tickets = Ticket.objects.filter(date_creation__year=year)

    total = tickets.count()
    en_cours = tickets.filter(statut='En cours').count()
    resolus = tickets.filter(statut='Résolu').count()
    rejetes = tickets.filter(statut='Rejeté').count()

    resolution_rate = round((resolus / total) * 100, 2) if total else 0

    monthly_resolution_rate = []
    monthly_resolution_time = []

    for month in range(1, 13):
        month_tickets = tickets.filter(date_creation__month=month)
        total_count = month_tickets.count()
        resolved_tickets = month_tickets.filter(statut='Résolu')
        resolved_count = resolved_tickets.count()

        rate = round((resolved_count / total_count) * 100, 2) if total_count else 0
        monthly_resolution_rate.append({
            'month': month,
            'resolution_rate': rate
        })

        durations = []
        for ticket in resolved_tickets:
            if ticket.date_creation and ticket.date_modification:
                delta = ticket.date_modification - ticket.date_creation
                durations.append(delta.total_seconds())
        avg_hours = round(sum(durations) / len(durations) / 3600, 2) if durations else 0
        monthly_resolution_time.append({
            'month': month,
            'average_resolution_time': avg_hours
        })

    intents = list(tickets.values_list('titre', flat=True))
    most_common_intent = Counter(intents).most_common(1)
    most_frequent_intent = most_common_intent[0][0] if most_common_intent else None

    # ✅ Ajout du nombre total d'agents
    User = get_user_model()
    total_agents = User.objects.filter(role='agent').count()  # Modifie selon ta logique

    return Response({
        'total_tickets': total,
        'en_cours': en_cours,
        'resolus': resolus,
        'rejetes': rejetes,
        'resolution_rate': resolution_rate,
        'monthly_resolution_rate': monthly_resolution_rate,
        'monthly_resolution_time': monthly_resolution_time,
        'most_frequent_intent': most_frequent_intent,
        'total_agents': total_agents  # <- Ajouté ici
    })

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from datetime import datetime
from collections import defaultdict
from django.db.models import Q
from .models import Ticket
from django.utils.timezone import now

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.utils.timezone import now
from .models import Utilisateur, Ticket

@api_view(['GET'])
@permission_classes([IsAdminUser])
def generate_agents_report_data(request):
    year = int(request.GET.get('year', now().year))
    month = int(request.GET.get('month', now().month))

    agents = Utilisateur.objects.filter(role='agent')
    report = []

    global_current = {
        'total': 0, 'en_cours': 0, 'resolus': 0, 'rejetes': 0,
        'taux_resolution': 0.0, 'temps_moyen_resolution': 0.0
    }
    global_previous = {
        'total': 0, 'en_cours': 0, 'resolus': 0, 'rejetes': 0,
        'taux_resolution': 0.0, 'temps_moyen_resolution': 0.0
    }

    for agent in agents:
        current_stats = compute_agent_stats(agent.id, year, month)
        prev_month = month - 1 or 12
        prev_year = year if month > 1 else year - 1
        previous_stats = compute_agent_stats(agent.id, prev_year, prev_month)

        delta_stats = compute_delta(current_stats, previous_stats)
        comment = generate_comment(delta_stats)

        # Ajout au report
        report.append({
            'nom': agent.nom,
            'email': agent.email,
            'telephone': agent.telephone,
            'stats': current_stats,
            'evolution': delta_stats,
            'commentaire': comment
        })

        # Cumul pour moyennes globales
        for key in global_current:
            global_current[key] += current_stats.get(key, 0)
            global_previous[key] += previous_stats.get(key, 0)

    # Moyennes globales
    total_agents = agents.count()
    if total_agents > 0:
        avg_current = {
            k: round(global_current[k] / total_agents, 2) for k in global_current
        }
        avg_previous = {
            k: round(global_previous[k] / total_agents, 2) for k in global_previous
        }
        avg_delta = compute_delta(avg_current, avg_previous)
        avg_comment = generate_comment(avg_delta)

        report.append({
            'nom': 'MOYENNE GLOBALE',
            'email': '',
            'telephone': '',
            'stats': avg_current,
            'evolution': avg_delta,
            'commentaire': avg_comment
        })

    return Response(report)


def compute_agent_stats(agent_id, year, month):
    tickets = Ticket.objects.filter(
        agent_id=agent_id,
        date_creation__year=year,
        date_creation__month=month
    )

    total = tickets.count()
    en_cours = tickets.filter(statut='En cours').count()
    resolus = tickets.filter(statut='Résolu').count()
    rejetes = tickets.filter(statut='Rejeté').count()

    taux_resolution = round((resolus / total) * 100, 2) if total else 0

    durations = [
        (t.date_modification - t.date_creation).total_seconds()
        for t in tickets.filter(statut='Résolu')
        if t.date_creation and t.date_modification
    ]
    temps_moyen = round(sum(durations) / len(durations) / 3600, 2) if durations else 0

    return {
        'total': total,
        'en_cours': en_cours,
        'resolus': resolus,
        'rejetes': rejetes,
        'taux_resolution': taux_resolution,
        'temps_moyen_resolution': temps_moyen
    }


def compute_delta(current, previous):
    delta = {}
    for key in current:
        delta[key] = round(current[key] - previous.get(key, 0), 2)
    return delta


def generate_comment(delta):
    taux_delta = delta.get('taux_resolution', 0)
    temps_delta = -delta.get('temps_moyen_resolution', 0)  # Inversé, car moins = mieux
    score = (taux_delta + temps_delta) / 2

    if score > 0.5:
        return "Bonne performance globale ce mois-ci. Les indicateurs s'améliorent."
    elif score < -0.5:
        return "Les performances se sont dégradées ce mois-ci. Une attention particulière est recommandée."
    else:
        return "Performances globalement stables par rapport au mois précédent."



# ✅ 4️⃣ Ajout des permissions pour MessageViewSet
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def get_permissions(self):
        """Gère l'accès aux messages selon le rôle."""
        if self.action == "create":
            permission_classes = [IsAuthenticated]  # Tous les utilisateurs connectés peuvent envoyer un message
        elif self.action in ["update", "partial_update", "destroy"]:
            permission_classes = [IsAgent]  # Seuls les agents peuvent modifier/supprimer un message
        elif self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated]  # Tous les utilisateurs connectés peuvent voir les messages
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

