from __future__ import annotations

from typing import Any

from openai import OpenAI


class DreamLLM:
    def __init__(self, api_key: str, model: str) -> None:
        self.enabled = bool(api_key)
        self.model = model
        self.client = OpenAI(api_key=api_key) if self.enabled else None

    def _chat(self, system: str, user: str) -> str:
        if not self.enabled or self.client is None:
            return "LLM disabled. Add OPENAI_API_KEY in .env to enable AI interpretation and protocol coaching."

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.7,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or "No response generated."

    def interpret_dream(self, entry: dict[str, Any]) -> str:
        system = (
            "You are a lucid dreaming coach inspired by evidence-based practices "
            "(dream recall training, MILD, reality testing, sleep hygiene, WBTB). "
            "You never claim medical certainty. Keep output practical and safe. "
            "Respond in plain text (no markdown symbols) with sections:\n"
            "Core Themes:\nDream Signs:\nTonight Action Plan:\nOne Reflection Question:\n"
            "Use short bullets and keep total response compact."
        )
        user = (
            f"Dream title: {entry.get('title', '')}\n"
            f"Types: {entry.get('dream_types', [])}\n"
            f"Narrative: {entry.get('narrative', '')}\n"
            f"Mood: {entry.get('mood', '')}\n"
            f"Symbols: {entry.get('symbols', '')}\n"
            f"Self interpretation: {entry.get('self_interpretation', '')}\n"
            f"Lucidity score: {entry.get('lucidity_score', '')}\n"
            f"REM minutes: {entry.get('rem_minutes', '')}\n"
            f"Deep sleep minutes: {entry.get('deep_sleep_minutes', '')}\n"
            f"Total sleep minutes: {entry.get('total_sleep_minutes', '')}"
        )
        return self._chat(system, user)

    def protocol_plan(self, stats: dict[str, Any], recent: list[dict[str, Any]]) -> str:
        recent_titles = [r.get("title", "Untitled") for r in recent[:7]]
        system = (
            "You are a world-class lucid dreaming protocol designer. "
            "Make a 7-day progressive protocol for a Telegram user. "
            "Blend consistency and variety to reduce dropout. "
            "Use sections: Day Routine, Pre-Sleep, Night Interrupt, Morning Capture, Weekly Review. "
            "Add a difficulty score 1-10 and one anti-burnout adaptation."
        )
        user = (
            f"Stats: {stats}\n"
            f"Recent dream titles: {recent_titles}\n"
            "Goal: maximize lucid dreaming rate without harming sleep quality."
        )
        return self._chat(system, user)
