"""URL routing for the feedback API."""

from __future__ import annotations

from django.urls import path

from feedback import views
from feedback.gateway_views import GatewayStatusView, GatewayWebhookView

urlpatterns = [
    path("sms/gateway/inbound", GatewayWebhookView.as_view()),
    path("sms/gateway/status", GatewayStatusView.as_view()),
    path("feedback", views.FeedbackView.as_view()),
    path("feedback/page", views.ResponsesPageView.as_view()),
    path("feedback/<int:response_id>", views.FeedbackDetailView.as_view()),
    path("feedback/<int:response_id>/draft", views.FeedbackDraftView.as_view()),
    path("feedback/<int:response_id>/send-email", views.FeedbackSendEmailView.as_view()),
    path("emails", views.EmailListView.as_view()),
    path("emails/<int:email_id>", views.EmailDetailView.as_view()),
    path("dashboard/summary", views.DashboardSummaryView.as_view()),
    path("alerts", views.AlertListView.as_view()),
    path("alerts/<int:alert_id>", views.AlertDetailView.as_view()),
    path("alerts/<int:alert_id>/ack", views.AlertAckView.as_view()),
    path("alerts/<int:alert_id>/draft", views.AlertDraftView.as_view()),
    path("alerts/<int:alert_id>/send-email", views.AlertSendEmailView.as_view()),
    path("alerts/<int:alert_id>/send-sms", views.AlertSendSmsView.as_view()),
    path("ai/ask", views.AskView.as_view()),
    path("sms/invite", views.SMSInviteView.as_view()),
    path("sms/africastalking/send", views.LiveAfricaTalkingSMSView.as_view()),
    path("sms/inbound", views.SMSInboundView.as_view()),
]
