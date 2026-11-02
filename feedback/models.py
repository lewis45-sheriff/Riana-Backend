"""MODEL layer: Django ORM entities for the feedback system."""

from __future__ import annotations

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=160)
    email = models.EmailField(max_length=254, null=True, blank=True)
    phone = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customers"

    def __str__(self) -> str:
        return f"{self.name} ({self.email or self.phone or 'anon'})"


class Response(models.Model):
    SOURCE_WEB = "web"
    SOURCE_SMS = "sms"

    DETRACTOR = "detractor"
    PASSIVE = "passive"
    PROMOTER = "promoter"

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="responses"
    )
    source = models.CharField(max_length=8, default=SOURCE_WEB)
    q1 = models.PositiveSmallIntegerField()  # product experience
    q2 = models.PositiveSmallIntegerField()  # customer care
    q3 = models.PositiveSmallIntegerField()  # happy with product
    comment = models.TextField(null=True, blank=True)
    mean = models.DecimalField(max_digits=4, decimal_places=2)
    classification = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "responses"
        ordering = ["-created_at"]


class Alert(models.Model):
    STATUS_NEW = "new"
    STATUS_ACK = "acknowledged"

    response = models.OneToOneField(
        Response, on_delete=models.CASCADE, related_name="alert"
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="alerts"
    )
    channels = models.CharField(max_length=64, default="")  # csv: email,in_app,sms
    status = models.CharField(max_length=16, default=STATUS_NEW)
    ai_draft = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "alerts"
        ordering = ["-created_at"]


class CommentInsight(models.Model):
    response = models.OneToOneField(
        Response, on_delete=models.CASCADE, related_name="insight"
    )
    mood = models.CharField(max_length=16)  # positive | neutral | negative
    topic = models.CharField(max_length=24)  # colour | price | delivery | service | other

    class Meta:
        db_table = "comment_insights"
