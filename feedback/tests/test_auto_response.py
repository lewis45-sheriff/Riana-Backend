"""Tests for automated responses on satisfactory feedback + care-rep notify."""

from unittest.mock import patch

import pytest

from feedback.controllers.feedback_controller import FeedbackController

pytestmark = pytest.mark.django_db


@patch("feedback.controllers.feedback_controller.notifications")
@patch("feedback.controllers.feedback_controller.agent")
def test_promoter_autosends_thankyou_and_notifies(agent, notifications):
    agent.draft_thankyou.return_value = ("Thanks!", False)
    FeedbackController().submit(
        name="Happy", email="h@example.com", phone=None, q1=5, q2=4, q3=5
    )
    notifications.notify_care_rep.assert_called_once()
    notifications.send_thankyou_to_customer.assert_called_once()
    agent.draft_thankyou.assert_called_once()


@patch("feedback.controllers.feedback_controller.notifications")
@patch("feedback.controllers.feedback_controller.agent")
def test_passive_autosends_thankyou(agent, notifications):
    agent.draft_thankyou.return_value = ("Thanks!", False)
    # 2,4,3 -> mean 3.00 -> passive
    FeedbackController().submit(
        name="Mid", email="m@example.com", phone=None, q1=2, q2=4, q3=3
    )
    notifications.send_thankyou_to_customer.assert_called_once()


@patch("feedback.controllers.feedback_controller.notifications")
@patch("feedback.controllers.feedback_controller.agent")
def test_detractor_does_not_autosend_to_customer(agent, notifications):
    agent.draft_reply.return_value = ("Sorry!", False)
    FeedbackController().submit(
        name="Sad", email="s@example.com", phone=None, q1=1, q2=2, q3=2
    )
    # Detractor: care rep notified (inside alert) but NO auto thank-you.
    notifications.send_thankyou_to_customer.assert_not_called()
    agent.draft_reply.assert_called_once()


@patch("feedback.controllers.feedback_controller.notifications")
@patch("feedback.controllers.feedback_controller.agent")
def test_thankyou_skipped_without_email(agent, notifications):
    agent.draft_thankyou.return_value = ("Thanks!", False)
    FeedbackController().submit(
        name="SMS User", email=None, phone="+254700000001", q1=5, q2=5, q3=5
    )
    # No email on file -> we don't attempt a thank-you send.
    notifications.send_thankyou_to_customer.assert_not_called()
