"""VIEW layer: DRF serializers (request validation + response presentation)."""

from __future__ import annotations

from rest_framework import serializers

from feedback.models import Alert, Customer, Response


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone"]


class ResponseSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    mean = serializers.FloatField()

    class Meta:
        model = Response
        fields = [
            "id",
            "source",
            "q1",
            "q2",
            "q3",
            "comment",
            "mean",
            "classification",
            "created_at",
            "customer",
        ]


class FeedbackCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    email = serializers.EmailField(required=False, allow_null=True, allow_blank=True)
    phone = serializers.CharField(
        max_length=32, required=False, allow_null=True, allow_blank=True
    )
    q1 = serializers.IntegerField(min_value=1, max_value=5)
    q2 = serializers.IntegerField(min_value=1, max_value=5)
    q3 = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )


class PaginatedResponsesSerializer(serializers.Serializer):
    items = ResponseSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    page_count = serializers.IntegerField()


class FeedbackResultSerializer(serializers.Serializer):
    response = ResponseSerializer()
    mean = serializers.FloatField()
    classification = serializers.CharField()
    alert_created = serializers.BooleanField()
    message = serializers.CharField()


class AlertSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    response = ResponseSerializer(read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "status",
            "channels",
            "ai_draft",
            "created_at",
            "customer",
            "response",
        ]


class SplitSerializer(serializers.Serializer):
    detractor = serializers.IntegerField()
    passive = serializers.IntegerField()
    promoter = serializers.IntegerField()


class TrendPointSerializer(serializers.Serializer):
    date = serializers.CharField()
    mean = serializers.FloatField(allow_null=True)
    count = serializers.IntegerField()
    projected = serializers.BooleanField(default=False)


class DashboardSummarySerializer(serializers.Serializer):
    total_respondents = serializers.IntegerField()
    average_mean = serializers.FloatField(allow_null=True)
    split = SplitSerializer()
    trend = TrendPointSerializer(many=True)
    open_alerts = serializers.IntegerField()


class AskRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=500)


class AskResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    chart = serializers.JSONField(allow_null=True)
    degraded = serializers.BooleanField()


class SmartReplySerializer(serializers.Serializer):
    draft = serializers.CharField()
    degraded = serializers.BooleanField()


class InviteRequestSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    name = serializers.CharField(max_length=160, required=False, allow_null=True)


class AlertAckSerializer(serializers.Serializer):
    status = serializers.CharField(default="acknowledged")


class SendReplySerializer(serializers.Serializer):
    # Optional override; if omitted the saved AI draft is used.
    message = serializers.CharField(required=False, allow_blank=True)


class EmailLogSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    to_email = serializers.CharField()
    subject = serializers.CharField()
    body = serializers.CharField()
    kind = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()


class PaginatedEmailsSerializer(serializers.Serializer):
    items = EmailLogSerializer(many=True)
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    page_count = serializers.IntegerField()
