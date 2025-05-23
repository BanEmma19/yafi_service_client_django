import re
from socket import socket

from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import ActiveLoop, SlotSet
from typing import Dict, Text, Any, List

from rasa_sdk.types import DomainDict


class ActionCommandeMauvaisEtat(Action):
    def name(self) -> Text:
        return "action_commande_mauvais_etat"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Active le formulaire pour signaler une commande en mauvais état
        return [ActiveLoop("commande_mauvais_etat_form")]


class ActionFacturationDouble(Action):
    def name(self) -> Text:
        return "action_facturation_double"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Active le formulaire pour une double facturation
        return [ActiveLoop("double_facturation_form")]


class ActionCompteSuspendu(Action):
    def name(self) -> Text:
        return "action_compte_suspendu"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Active le formulaire pour un compte suspendu
        return [ActiveLoop("compte_suspendu_form")]


class ActionCommandeNonLivree(Action):
    def name(self) -> Text:
        return "action_commande_non_livree"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Active le formulaire pour une commande non reçue
        return [ActiveLoop("commande_non_recue_form")]


class ActionRemboursement(Action):
    def name(self) -> Text:
        return "action_remboursement"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        # Active le formulaire pour une demande de remboursement
        return [ActiveLoop("remboursement_form")]

class ValidateCommandeMauvaisEtatForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_commande_mauvais_etat_form"

    def validate_numero_commande(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "commande_mauvais_etat_form":
            if value and value.isdigit():  # Validation supplémentaire pour numéro de commande
                return {"numero_commande": value}
            dispatcher.utter_message(text="Le numéro de commande doit contenir uniquement des chiffres.")
        return {"numero_commande": None}

    def validate_photo_produit(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "commande_mauvais_etat_form":
            if value:  # Ici vous pourriez vérifier si c'est une URL/image valide
                return {"photo_produit": value}
            dispatcher.utter_message(text="Veuillez fournir une photo valide.")
        return {"photo_produit": None}

    def validate_details_probleme(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "commande_mauvais_etat_form":
            if value and len(value) > 10:  # Validation de longueur minimale
                return {"details_probleme": value}
            dispatcher.utter_message(text="Veuillez décrire le problème plus en détail (au moins 10 caractères).")
        return {"details_probleme": None}

class ValidateDoubleFacturationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_double_facturation_form"

    def validate_numero_commande(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "double_facturation_form":
            if value and value.isdigit():
                return {"numero_commande": value}
            dispatcher.utter_message(text="Numéro de commande invalide. Veuillez entrer uniquement des chiffres.")
        return {"numero_commande": None}

    def validate_photo_double_transaction(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "double_facturation_form":
            if value:  # Vérification basique de présence
                return {"photo_double_transaction": value}
            dispatcher.utter_message(text="Veuillez envoyer une preuve de la double transaction.")
        return {"photo_double_transaction": None}

class ValidateCommandeNonLivreeForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_commande_non_livree_form"

    def validate_numero_commande(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "commande_non_livree_form":
            if value and value.isdigit():
                return {"numero_commande": value}
            dispatcher.utter_message(text="Nous avons besoin de votre numéro de commande (chiffres uniquement).")
        return {"numero_commande": None}

    def validate_adresse_livraison(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "commande_non_livree_form":
            if value and len(value) > 5:  # Validation d'adresse minimale
                return {"adresse_livraison": value}
            dispatcher.utter_message(text="Veuillez confirmer une adresse valide.")
        return {"adresse_livraison": None}

    def validate_disponibilite_nouvelle_livraison(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "commande_non_livree_form":
            return {"disponibilite_nouvelle_livraison": value}  # Pas de validation stricte
        return {"disponibilite_nouvelle_livraison": None}


class ValidateCompteSuspenduForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_compte_suspendu_form"

    async def validate_email_utilisateur(
            self,
            slot_value: Any,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict
    ) -> Dict[Text, Any]:
        """Validation robuste avec regex"""
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

        if re.fullmatch(email_regex, slot_value):
            dispatcher.utter_message("Email validé avec succès!")
            return {"email_utilisateur": slot_value}

        dispatcher.utter_message(response="utter_email_invalide")
        return {"email_utilisateur": None}

class ValidateRemboursementForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_remboursement_form"

    def validate_numero_commande(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "remboursement_form":
            if value and value.isdigit() and len(value) >= 6:
                return {"numero_commande": value}
            dispatcher.utter_message(text="Le numéro de commande doit contenir au moins 6 chiffres.")
        return {"numero_commande": None}

    def validate_details_probleme(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "remboursement_form":
            if value and len(value.strip()) >= 20:
                return {"details_probleme": value}
            dispatcher.utter_message(text="Veuillez décrire le problème en au moins 20 caractères.")
        return {"details_probleme": None}

    def validate_photo_transaction(
        self, value: Text, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get("name") == "remboursement_form":
            if value:  # Validation basique de présence
                return {"photo_transaction": value}
            dispatcher.utter_message(text="Veuillez envoyer une preuve de transaction.")
        return {"photo_transaction": None}