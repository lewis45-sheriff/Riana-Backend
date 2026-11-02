"""CONTROLLER: AI 'ask the dashboard' natural-language queries."""

from __future__ import annotations

from feedback.services import agent


class AIController:
    def ask(self, question: str) -> tuple[str, dict, bool]:
        return agent.ask_dashboard(question)
