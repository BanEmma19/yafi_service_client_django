from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Ticket, Message

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from support.models import Utilisateur
from django.contrib.auth import authenticate
from rest_framework import serializers

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        # Vérifier l'authentification
        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError("No active account found with the given credentials")

        # Vérifier si l'utilisateur est actif
        if not user.is_active:
            raise serializers.ValidationError("This account is inactive")

        # Générer le token JWT
        data = super().validate(attrs)
        data["role"] = user.role  # Ajout du rôle dans le token

        return data

class UtilisateurSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Utilisateur
        fields = ['id', 'email', 'nom', 'password', 'telephone', 'role']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}  # ← important ici
        }

    def create(self, validated_data):
        # Délègue le hachage à la méthode `create_user` du manager
        user = Utilisateur.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


from rest_framework import serializers
from .models import Ticket

class TicketSerializer(serializers.ModelSerializer):
    agent_nom = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = ['id', 'titre', 'description', 'statut', 'agent_nom', 'date_creation', 'date_modification']
        read_only_fields = ['statut', 'agent_nom', 'date_creation', 'date_modification']

    def get_agent_nom(self, obj):
        return obj.agent.nom if obj.agent else None


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
