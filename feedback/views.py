"""Thin HTTP layer (DRF views) delegating to controllers.

These are intentionally minimal: parse/validate via serializers, call a
controller, serialize the result. All business logic lives in controllers and
services.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response as DRFResponse
from rest_framework.views import APIView

from feedback.controllers.ai_controller import AIController
from feedback.controllers.alert_controller import AlertController
from feedback.controllers.dashboard_controller import DashboardController
from feedback.controllers.feedback_controller import FeedbackController
from feedback.controllers.sms_controller import SMSController
from feedback.serializers import (
    AlertAckSerializer,
    AlertSerializer,
    AskRequestSerializer,
    AskResponseSerializer,
    DashboardSummarySerializer,
    FeedbackCreateSerializer,
    FeedbackResultSerializer,
    InviteRequestSerializer,
    PaginatedResponsesSerializer,
    ResponseSerializer,
    SendReplySerializer,
    SmartReplySerializer,
)


class FeedbackView(APIView):
    def post(self, request: Request) -> DRFResponse:
        serializer = FeedbackCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        response, alert_created = FeedbackController().submit(
            name=data["name"],
            email=data.get("email") or None,
            phone=data.get("phone") or None,
            q1=data["q1"],
            q2=data["q2"],
            q3=data["q3"],
            comment=data.get("comment") or None,
            source="web",
        )
        message = (
            "Thanks for your feedback — we're sorry to hear it, someone will reach out."
            if alert_created
            else "Thanks for your feedback!"
        )
        payload = {
            "response": ResponseSerializer(response).data,
            "mean": float(response.mean),
            "classification": response.classification,
            "alert_created": alert_created,
            "message": message,
        }
        return DRFResponse(
            FeedbackResultSerializer(payload).data, status=status.HTTP_201_CREATED
        )

    def get(self, request: Request) -> DRFResponse:
        # Listing responses exposes customer PII — care team only.
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))
        rows = FeedbackController().list(limit, offset)
        return DRFResponse(ResponseSerializer(rows, many=True).data)

    def get_permissions(self):
        # Public can submit (POST); listing (GET) requires auth.
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return super().get_permissions()


class ResponsesPageView(APIView):
    """Server-paginated responses for the dashboard table."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> DRFResponse:
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 10))
        except ValueError:
            page, page_size = 1, 10
        classification = request.query_params.get("classification") or None
        data = FeedbackController().paginate(page, page_size, classification)
        return DRFResponse(PaginatedResponsesSerializer(data).data)


class FeedbackDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, _request: Request, response_id: int) -> DRFResponse:
        row = FeedbackController().get(response_id)
        if row is None:
            return DRFResponse({"detail": "Response not found"}, status=404)
        return DRFResponse(ResponseSerializer(row).data)


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> DRFResponse:
        days = int(request.query_params.get("days", 14))
        data = DashboardController().summary(days)
        return DRFResponse(DashboardSummarySerializer(data).data)


class AlertListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> DRFResponse:
        status_filter = request.query_params.get("status")
        rows = AlertController().list(status_filter)
        return DRFResponse(AlertSerializer(rows, many=True).data)


class AlertDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, _request: Request, alert_id: int) -> DRFResponse:
        alert = AlertController().get(alert_id)
        if alert is None:
            return DRFResponse({"detail": "Alert not found"}, status=404)
        return DRFResponse(AlertSerializer(alert).data)


class AlertAckView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, alert_id: int) -> DRFResponse:
        serializer = AlertAckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alert = AlertController().acknowledge(
            alert_id, serializer.validated_data["status"]
        )
        if alert is None:
            return DRFResponse({"detail": "Alert not found"}, status=404)
        return DRFResponse(AlertSerializer(alert).data)


class AlertDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, _request: Request, alert_id: int) -> DRFResponse:
        result = AlertController().regenerate_draft(alert_id)
        if result is None:
            return DRFResponse({"detail": "Alert not found"}, status=404)
        draft, degraded = result
        return DRFResponse(
            SmartReplySerializer({"draft": draft, "degraded": degraded}).data
        )


class AlertSendEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, alert_id: int) -> DRFResponse:
        serializer = SendReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AlertController().send_email_reply(
            alert_id, serializer.validated_data.get("message") or None
        )
        if result is None:
            return DRFResponse({"detail": "Alert not found"}, status=404)
        return DRFResponse(result)


class AlertSendSmsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, alert_id: int) -> DRFResponse:
        serializer = SendReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = AlertController().send_sms_reply(
            alert_id, serializer.validated_data.get("message") or None
        )
        if result is None:
            return DRFResponse({"detail": "Alert not found"}, status=404)
        return DRFResponse(result)


class AskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> DRFResponse:
        serializer = AskRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer, chart, degraded = AIController().ask(
            serializer.validated_data["question"]
        )
        return DRFResponse(
            AskResponseSerializer(
                {"answer": answer, "chart": chart, "degraded": degraded}
            ).data
        )


class SMSInviteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> DRFResponse:
        serializer = InviteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = SMSController().send_invite(
            serializer.validated_data["phone"],
            serializer.validated_data.get("name"),
        )
        return DRFResponse(result)


class SMSInboundView(APIView):
    def post(self, request: Request) -> DRFResponse:
        from_ = request.data.get("from", "")
        text = request.data.get("text", "")
        result = SMSController().handle_inbound(from_, text)
        return DRFResponse(result)
