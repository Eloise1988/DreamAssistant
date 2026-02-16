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
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content or "No response generated."
        except Exception:
            return "AI analysis unavailable right now. Try again in a moment."

    def _fallback_blockage_paragraph(self, entry: dict[str, Any]) -> str:
        mood = str(entry.get("mood", "")).strip()
        symbols = str(entry.get("symbols", "")).strip()
        hints = []
        if mood:
            hints.append(f"emotion pattern around '{mood}'")
        if symbols:
            hints.append(f"recurring symbol pressure around '{symbols}'")
        core = ", ".join(hints) if hints else "unfinished daytime concerns and avoidance themes"
        return (
            "Potential blockages (hypothesis): this dream may reflect "
            f"{core}. Use one reality check on that theme tomorrow and set a calm in-dream intention to face it."
        )

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

    def blockage_scan(self, stats: dict[str, Any], recent: list[dict[str, Any]]) -> str:
        filtered = []
        for row in recent:
            if row.get("no_dream_recall"):
                continue
            filtered.append(
                {
                    "entry_date": row.get("entry_date"),
                    "title": row.get("title"),
                    "narrative": str(row.get("narrative", ""))[:500],
                    "mood": row.get("mood"),
                    "symbols": row.get("symbols"),
                    "characters": row.get("characters"),
                    "lucidity_score": row.get("lucidity_score"),
                    "wake_feeling": row.get("wake_feeling"),
                }
            )

        system = (
            "You are a lucid dreaming coach focused on finding and fixing personal blockages. "
            "Use three lenses and label each as a hypothesis, not certainty:\n"
            "1) Psychoanalytic/depth (Freud/Jung-style conflict, shadow, compensatory themes).\n"
            "2) Cognitive/neurocognitive (Domhoff-style continuity of waking concerns and emotion).\n"
            "3) Threat simulation (Revonsuo-style fear/threat rehearsal patterns).\n"
            "Never diagnose disorders or claim medical truth. Keep practical and safe.\n"
            "Respond in plain text with sections:\n"
            "Likely Blockages:\n"
            "Evidence From Recent Dreams:\n"
            "Framework Synthesis (Depth / Cognitive / Threat):\n"
            "Lucid Repair Plan (Day / Pre-Sleep / In-Dream / Morning):\n"
            "7-Day Exposure Ladder:\n"
            "Tonight's One-Sentence Intention:\n"
            "Use concise bullets."
        )
        user = (
            f"Stats: {stats}\n"
            f"Recent recalled dreams (latest first): {filtered[:8]}\n"
            "Goal: identify emotional blockages/fears and convert them into lucid dream practice steps."
        )
        return self._chat(system, user)

    def potential_blockages_paragraph(self, entry: dict[str, Any]) -> str:
        if not self.enabled or self.client is None:
            return self._fallback_blockage_paragraph(entry)

        system = (
            "You are a lucid dream coach. "
            "Write exactly one short paragraph (2-3 sentences, max 70 words). "
            "Infer potential emotional/behavioral blockages as hypotheses only, not facts. "
            "Blend depth (Freud/Jung), cognitive continuity (Domhoff), and threat simulation (Revonsuo) briefly. "
            "End with one practical next step for tonight."
        )
        user = (
            f"Title: {entry.get('title', '')}\n"
            f"Narrative: {entry.get('narrative', '')}\n"
            f"Mood: {entry.get('mood', '')}\n"
            f"Symbols: {entry.get('symbols', '')}\n"
            f"Self interpretation: {entry.get('self_interpretation', '')}"
        )
        text = self._chat(system, user).strip()
        if not text or "AI analysis unavailable right now" in text:
            return self._fallback_blockage_paragraph(entry)
        return text
