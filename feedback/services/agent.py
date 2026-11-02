"""The 'Ask the dashboard' agent and smart-reply drafting.

The agent is a small tool-using layer: it never runs free SQL. It picks a
safe, parameterised analytics query (via the repository) based on the
question, then asks the LLM to phrase the numbers in plain English. If the LLM
is unavailable, we still return a deterministic, data-backed answer (degraded).
"""

from __future__ import annotations

from feedback.repositories.response_repository import ResponseRepository
from feedback.services import ai

SYSTEM_ANALYST = (
    "You are a concise analytics assistant for a paint company's customer "
    "feedback dashboard. Answer in at most 3 short plain-English sentences. "
    "Use ONLY the numbers in the provided data. Do not invent figures."
)

SYSTEM_CARE = (
    "You draft short, warm, professional follow-up emails for a customer care "
    "rep responding to an unhappy (detractor) customer. Keep it under 120 "
    "words, apologise sincerely, and offer a concrete next step. Output only "
    "the email body."
)

SYSTEM_THANKYOU = (
    "You draft short, warm thank-you emails to a satisfied paint customer who "
    "left positive feedback. Keep it under 90 words, sound genuine and human, "
    "thank them specifically, and invite them to reach out any time. Output "
    "only the email body."
)


def _detect_days(question: str) -> int:
    q = question.lower()
    if "today" in q:
        return 1
    if "month" in q:
        return 30
    if "week" in q:
        return 7
    return 7


def _detect_metric(question: str) -> str:
    q = question.lower()
    if "care" in q or "service" in q or "support" in q:
        return "care"
    if "product" in q or "paint" in q:
        return "product"
    if "happy" in q or "happiness" in q:
        return "happy"
    return "overall"


def gather_facts(question: str) -> dict:
    """Run safe analytics tools and return a structured fact sheet + chart."""
    days = _detect_days(question)
    metric = _detect_metric(question)
    repo = ResponseRepository()

    total = repo.count_since(days)
    average = repo.average_metric_since(metric, days)
    split = repo.classification_counts(days)

    return {
        "days": days,
        "metric": metric,
        "total": total,
        "average": average,
        "split": split,
        "chart": {"type": "donut", "data": split},
    }


def _fallback_sentence(facts: dict) -> str:
    metric_label = {
        "product": "product experience",
        "care": "customer care",
        "happy": "happiness",
        "overall": "overall",
    }[facts["metric"]]
    if facts["total"] == 0:
        return f"No feedback was recorded in the last {facts['days']} days."
    s = facts["split"]
    return (
        f"In the last {facts['days']} days there were {facts['total']} responses, "
        f"with an average {metric_label} score of {facts['average']}. "
        f"That's {s['promoter']} promoters, {s['passive']} passives and "
        f"{s['detractor']} detractors."
    )


def ask_dashboard(question: str) -> tuple[str, dict, bool]:
    """Return (answer, chart, degraded)."""
    facts = gather_facts(question)
    deterministic = _fallback_sentence(facts)
    prompt = (
        f"Question: {question}\n\n"
        f"Data (JSON): {facts}\n\n"
        f"A correct plain-English summary is: {deterministic}\n"
        "Rephrase it naturally in at most 3 sentences."
    )
    result = ai.chat(SYSTEM_ANALYST, prompt)
    answer = deterministic if result.degraded else result.text
    return answer, facts["chart"], result.degraded


def draft_reply(customer, response) -> tuple[str, bool]:
    """Draft a care-rep follow-up for a detractor. Returns (draft, degraded)."""
    prompt = (
        f"Customer name: {customer.name}\n"
        f"Scores (1-5): product={response.q1}, care={response.q2}, "
        f"happy={response.q3} (mean {response.mean}).\n"
        f"Comment: {response.comment or 'none'}\n"
        "Write the follow-up email body."
    )
    result = ai.chat(SYSTEM_CARE, prompt)
    if result.degraded:
        fallback = (
            f"Hi {customer.name},\n\n"
            "Thank you for taking the time to share your feedback, and I'm "
            "sorry your recent experience with us fell short. Your comments "
            "matter and we'd genuinely like to put things right. Could we "
            "arrange a quick call at a time that suits you? I'll personally "
            "make sure we follow up.\n\n"
            "Warm regards,\nCustomer Care, Company X"
        )
        return fallback, True
    return result.text, False


def draft_thankyou(customer, response) -> tuple[str, bool]:
    """Draft a thank-you email for a satisfied customer. Returns (text, degraded)."""
    prompt = (
        f"Customer name: {customer.name}\n"
        f"Scores (1-5): product={response.q1}, care={response.q2}, "
        f"happy={response.q3} (mean {response.mean}).\n"
        f"Comment: {response.comment or 'none'}\n"
        "Write the thank-you email body."
    )
    result = ai.chat(SYSTEM_THANKYOU, prompt)
    if result.degraded:
        fallback = (
            f"Hi {customer.name},\n\n"
            "Thank you so much for your feedback — it genuinely made our day! "
            "We're thrilled you had a great experience with our paint, and we "
            "can't wait to help with your next project. If there's ever "
            "anything we can do, just reach out.\n\n"
            "Warm regards,\nCustomer Care, Company X"
        )
        return fallback, True
    return result.text, False
