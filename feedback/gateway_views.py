"""Dedicated signed endpoint for the SMSGate Android application."""

from django.conf import settings
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from feedback.services import sim_gateway


class IncomingPayload(serializers.Serializer):
    sender = serializers.CharField(max_length=32)
    message = serializers.CharField(max_length=2000, trim_whitespace=False)


class IncomingEvent(serializers.Serializer):
    id = serializers.CharField(max_length=128)
    deviceId = serializers.CharField(max_length=128)
    event = serializers.ChoiceField(choices=["sms:received"])
    payload = IncomingPayload()


class GatewayWebhookView(APIView):
    authentication_classes = []  # Device authentication is the HMAC, never a care-account cookie.
    permission_classes = [AllowAny]

    def post(self, request):
        if not sim_gateway.valid_signature(
            request.body,
            request.headers.get("X-Timestamp", ""),
            request.headers.get("X-Signature", ""),
        ):
            return Response({"detail": "Invalid gateway signature"}, status=403)
        serializer = IncomingEvent(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if settings.SMSGATE_DEVICE_ID and data["deviceId"] != settings.SMSGATE_DEVICE_ID:
            return Response({"detail": "Unexpected gateway device"}, status=403)
        return Response(sim_gateway.receive(data))


class GatewayStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "provider": settings.SMS_PROVIDER,
                "credentials_configured": bool(
                    settings.SMSGATE_USERNAME and settings.SMSGATE_PASSWORD
                ),
                "webhook_configured": len(settings.SMSGATE_WEBHOOK_SECRET) >= 32,
                "device_configured": bool(settings.SMSGATE_DEVICE_ID),
            }
        )
