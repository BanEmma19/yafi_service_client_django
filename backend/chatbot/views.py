import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ChatbotView(APIView):
    def post(self, request):
        message = request.data.get("message", "")
        rasa_url = "http://localhost:5005/webhooks/rest/webhook"
        response = requests.post(rasa_url, json={"sender": "user", "message": message})

        if response.status_code == 200:
            return Response(response.json(), status=status.HTTP_200_OK)
        return Response({"error": "Erreur avec Rasa"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
