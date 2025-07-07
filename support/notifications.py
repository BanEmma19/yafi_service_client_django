from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_ticket_email(action, ticket):
    """
    Envoie un email en fonction de l'action sur le ticket.
    action : 'created', 'updated', 'deleted'
    ticket : instance Ticket
    """

    subject = None
    html_message = None
    recipient_list = []

    client_email = ticket.client.email if ticket.client else None
    agent_email = ticket.agent.email if ticket.agent else None

    # Construire le sujet et message selon l'action
    if action == "created":
        subject = f"[YaFi] Nouveau ticket créé : {ticket.titre}"
        html_message = render_to_string("emails/ticket_created.html", {"ticket": ticket})
        recipient_list = [client_email, agent_email]
    elif action == "updated":
        subject = f"[YaFi] Ticket mis à jour : {ticket.titre} (Statut: {ticket.statut})"
        html_message = render_to_string("emails/ticket_updated.html", {"ticket": ticket})
        recipient_list = [client_email, agent_email]
    elif action == "deleted":
        subject = f"[YaFi] Ticket supprimé : {ticket.titre}"
        html_message = render_to_string("emails/ticket_deleted.html", {"ticket": ticket})
        # On n'envoie l'info qu'au client (pas à l'agent)
        recipient_list = [client_email]
    else:
        logger.warning(f"Action email inconnue : {action}")
        return

    # Nettoyer le message texte pour fallback
    message = strip_tags(html_message)

    # Filtrer les emails valides (non None)
    recipient_list = [email for email in recipient_list if email]

    if not recipient_list:
        logger.warning(f"Aucun destinataire valide pour l'email ticket {ticket.id} action {action}")
        return

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email envoyé pour ticket {ticket.id}, action {action} aux : {recipient_list}")
    except Exception as e:
        logger.error(f"Erreur envoi email ticket {ticket.id}, action {action} : {e}")

        # -- contenu SMS simple --
    sms_message = None

    if action == "created":
        ...
        sms_message = f"🎫 Nouveau ticket YaFi service client : '{ticket.titre}' créé avec succès."
    elif action == "updated":
        ...
        sms_message = f"✏️ Ticket YaFi service client '{ticket.titre}' mis à jour. Statut : {ticket.statut}"
    elif action == "deleted":
        ...
        sms_message = f"🗑️ Votre ticket YaFi service client '{ticket.titre}' a été supprimé."



    def format_telephone_cameroon(phone_number: str) -> str:
            phone_number = phone_number.strip()

            # Supprime les espaces, tirets ou parenthèses
            for ch in [' ', '-', '(', ')']:
                phone_number = phone_number.replace(ch, '')

            # Si déjà au format international
            if phone_number.startswith('+237'):
                return phone_number

            # Si commence par 237 sans le +
            if phone_number.startswith('237'):
                return f'+{phone_number}'

            # Si commence par 6 ou autre (numéro local au Cameroun)
            if phone_number.startswith('6') and len(phone_number) == 9:
                return f'+237{phone_number}'

            # Sinon, retourne tel quel (ou ajoutez une exception selon votre logique)
            return phone_number

    # Envoi SMS au client uniquement (s'il a un numéro)
    if hasattr(ticket.client, "telephone") and ticket.client.telephone:
        formatted_number = format_telephone_cameroon(ticket.client.telephone)
        send_sms(formatted_number, sms_message)

from twilio.rest import Client
import os

def send_sms(to_number, message):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_PHONE_NUMBER")

    if not (account_sid and auth_token and from_number):
        logger.warning("Configuration Twilio manquante")
        return

    try:
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_=from_number,
            to=to_number,
        )
        logger.info(f"SMS envoyé à {to_number}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du SMS : {e}")

def envoyer_code_reinit(user, code):
        """
        Envoie un email avec le code de réinitialisation de mot de passe à l'utilisateur.
        """
        subject = "[YaFi] Réinitialisation de votre mot de passe"
        html_message = render_to_string("emails/password_reset_code.html", {
            "user": user,
            "code": code
        })
        message = strip_tags(html_message)
        recipient_list = [user.email]

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email de code de réinitialisation envoyé à {user.email}")
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de réinitialisation : {e}")