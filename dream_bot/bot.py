from __future__ import annotations

import random
from datetime import datetime, time, timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import load_settings
from .content import (
    DREAM_TYPE_OPTIONS,
    DREAM_TYPES_GUIDE,
    ENTRY_QUESTIONS,
    PROBING_QUESTIONS,
    RECALL_TIPS,
    SLEEP_QUALITY_OPTIONS,
    WAKE_FEELING_OPTIONS,
)
from .db import Database
from .llm import DreamLLM


class DreamDiaryBot:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.db = Database(self.settings.mongodb_uri, self.settings.mongodb_db)
        self.llm = DreamLLM(self.settings.openai_api_key, self.settings.openai_model)
        self.sessions: dict[int, dict[str, Any]] = {}

    def app(self) -> Application:
        application = Application.builder().token(self.settings.telegram_bot_token).build()

        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("menu", self.menu))
        application.add_handler(CommandHandler("cancel", self.cancel))
        application.add_handler(CommandHandler("set_reminder", self.set_reminder))
        application.add_handler(CommandHandler("clear_reminder", self.clear_reminder))

        application.add_handler(CallbackQueryHandler(self.on_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_text))

        return application

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None or update.message is None:
            return

        self.db.ensure_user(user.id, user.username)

        text = (
            "Dream Diary activated.\n\n"
            "This bot is optimized for lucid dream training with progressive depth:\n"
            "- Structured nightly journal\n"
            "- Pattern detection and dream-sign tracking\n"
            "- AI interpretation and 7-day lucid protocol\n"
            "- Streak system and anti-dropout variety\n\n"
            "Use the menu below."
        )
        await update.message.reply_text(text, reply_markup=self.main_menu_keyboard())

    async def menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None:
            return
        await update.message.reply_text("Main menu", reply_markup=self.main_menu_keyboard())

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None or update.message is None:
            return
        self.sessions.pop(user.id, None)
        await update.message.reply_text("Current flow canceled.", reply_markup=self.main_menu_keyboard())

    async def set_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.effective_user is None:
            return

        if not context.args:
            await update.message.reply_text("Usage: /set_reminder HH:MM (24h, UTC). Example: /set_reminder 07:30")
            return

        raw = context.args[0]
        try:
            hh, mm = raw.split(":")
            when = time(hour=int(hh), minute=int(mm), tzinfo=timezone.utc)
        except ValueError:
            await update.message.reply_text("Invalid time format. Use HH:MM in 24h format.")
            return

        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id is None:
            return

        job_name = f"daily_reminder_{update.effective_user.id}"
        for job in context.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()

        context.job_queue.run_daily(
            self.daily_reminder,
            time=when,
            chat_id=chat_id,
            user_id=update.effective_user.id,
            name=job_name,
        )
        await update.message.reply_text(
            f"Daily reminder set at {raw} UTC. I will prompt morning recall and evening intention every day."
        )

    async def clear_reminder(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if update.message is None or update.effective_user is None:
            return
        job_name = f"daily_reminder_{update.effective_user.id}"
        removed = 0
        for job in context.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
            removed += 1
        await update.message.reply_text("Reminder removed." if removed else "No reminder found.")

    async def daily_reminder(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = context.job.user_id
        if user_id is None:
            return
        message = (
            "Daily lucid protocol check:\n"
            "1) Morning: log dreams immediately.\n"
            "2) Daytime: 10 reality checks.\n"
            "3) Night: intention phrase + visualize dream signs."
        )
        if context.job.chat_id is not None:
            await context.bot.send_message(chat_id=context.job.chat_id, text=message)

    def main_menu_keyboard(self) -> InlineKeyboardMarkup:
        keys = [
            [InlineKeyboardButton("📝 New Dream Entry", callback_data="menu:new_entry")],
            [InlineKeyboardButton("📚 Dream Index", callback_data="menu:index")],
            [InlineKeyboardButton("🧠 Interpret Last Dream", callback_data="menu:interpret")],
            [InlineKeyboardButton("🎯 7-Day Protocol", callback_data="menu:protocol")],
            [InlineKeyboardButton("🔥 Streak & Progress", callback_data="menu:stats")],
            [InlineKeyboardButton("🛠 Reality Check Drill", callback_data="menu:drill")],
            [InlineKeyboardButton("💡 Helpful Tips", callback_data="menu:tips")],
            [InlineKeyboardButton("📖 Dream Types", callback_data="menu:types")],
        ]
        return InlineKeyboardMarkup(keys)

    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user = update.effective_user
        if query is None or user is None:
            return
        await query.answer()

        data = query.data or ""
        if data.startswith("menu:"):
            action = data.split(":", 1)[1]
            if action == "new_entry":
                await self.begin_entry(query, user.id)
            elif action == "index":
                await self.show_index(query, user.id)
            elif action == "interpret":
                await self.interpret_last(query, user.id)
            elif action == "protocol":
                await self.show_protocol(query, user.id)
            elif action == "stats":
                await self.show_stats(query, user.id)
            elif action == "drill":
                await self.reality_drill(query)
            elif action == "tips":
                await query.message.reply_text(RECALL_TIPS)
            elif action == "types":
                await query.message.reply_text(DREAM_TYPES_GUIDE)
            return

        if data.startswith("pick:"):
            await self.handle_picker_callback(query, user.id, data)

    async def begin_entry(self, query, user_id: int) -> None:
        self.sessions[user_id] = {
            "mode": "entry",
            "phase": "dream_types",
            "data": {
                "dream_types": [],
                "sleep_quality": [],
                "wake_feeling": [],
            },
            "q_index": 0,
        }
        await query.message.reply_text(
            "Step 1/4: Select dream types, then press Done.",
            reply_markup=self.build_toggle_keyboard("dream_types", DREAM_TYPE_OPTIONS, []),
        )

    def build_toggle_keyboard(self, category: str, options: list[str], selected: list[str]) -> InlineKeyboardMarkup:
        rows = []
        for option in options:
            mark = "✅ " if option in selected else "⬜ "
            rows.append([InlineKeyboardButton(mark + option, callback_data=f"pick:{category}:toggle:{option}")])
        rows.append([InlineKeyboardButton("Done", callback_data=f"pick:{category}:done")])
        return InlineKeyboardMarkup(rows)

    async def handle_picker_callback(self, query, user_id: int, data: str) -> None:
        session = self.sessions.get(user_id)
        if not session or session.get("mode") != "entry":
            await query.message.reply_text("No active entry. Tap 'New Dream Entry' first.")
            return

        _, category, action, *rest = data.split(":")
        payload = session["data"]

        if action == "toggle":
            option = rest[0]
            current = payload.get(category, [])
            if option in current:
                current.remove(option)
            else:
                current.append(option)
            payload[category] = current

            options_map = {
                "dream_types": DREAM_TYPE_OPTIONS,
                "sleep_quality": SLEEP_QUALITY_OPTIONS,
                "wake_feeling": WAKE_FEELING_OPTIONS,
            }
            await query.edit_message_reply_markup(
                reply_markup=self.build_toggle_keyboard(category, options_map[category], current)
            )
            return

        if action == "done":
            await query.edit_message_reply_markup(reply_markup=None)
            if category == "dream_types":
                session["phase"] = "sleep_quality"
                await query.message.reply_text(
                    "Step 2/4: Select sleep quality.",
                    reply_markup=self.build_toggle_keyboard("sleep_quality", SLEEP_QUALITY_OPTIONS, payload["sleep_quality"]),
                )
                return
            if category == "sleep_quality":
                session["phase"] = "wake_feeling"
                await query.message.reply_text(
                    "Step 3/4: Select waking feelings.",
                    reply_markup=self.build_toggle_keyboard("wake_feeling", WAKE_FEELING_OPTIONS, payload["wake_feeling"]),
                )
                return
            if category == "wake_feeling":
                session["phase"] = "questions"
                await query.message.reply_text("Step 4/4: free-text details. Type /cancel anytime.")
                await self.ask_next_question(query.message.chat_id, query.message.get_bot(), user_id)

    async def ask_next_question(self, chat_id: int, bot, user_id: int) -> None:
        session = self.sessions.get(user_id)
        if not session:
            return

        idx = session.get("q_index", 0)
        if idx >= len(ENTRY_QUESTIONS):
            await self.finish_entry(chat_id, bot, user_id)
            return

        _, prompt = ENTRY_QUESTIONS[idx]
        await bot.send_message(chat_id=chat_id, text=f"Q{idx + 1}/{len(ENTRY_QUESTIONS)}: {prompt}")

    async def on_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = update.message
        if user is None or message is None:
            return

        session = self.sessions.get(user.id)
        if not session or session.get("mode") != "entry" or session.get("phase") != "questions":
            await message.reply_text(
                "Use /menu to open options, or tap New Dream Entry.",
                reply_markup=self.main_menu_keyboard(),
            )
            return

        idx = session.get("q_index", 0)
        key, _ = ENTRY_QUESTIONS[idx]

        value = message.text.strip()
        if key in {"lucidity_score", "reality_checks", "rem_minutes", "deep_sleep_minutes", "total_sleep_minutes"}:
            if not value.isdigit():
                await message.reply_text("Please enter a number.")
                return
            value = int(value)

        session["data"][key] = value
        session["q_index"] = idx + 1
        await self.ask_next_question(message.chat_id, context.bot, user.id)

    async def finish_entry(self, chat_id: int, bot, user_id: int) -> None:
        session = self.sessions.get(user_id)
        if not session:
            return
        payload = session["data"]
        payload["entry_date"] = datetime.now(timezone.utc).date().isoformat()
        entry_id = self.db.save_entry(user_id, payload)
        self.sessions.pop(user_id, None)

        summary = (
            f"Dream saved. ID: {entry_id}\n"
            f"Title: {payload.get('title', 'Untitled')}\n"
            f"Types: {', '.join(payload.get('dream_types', [])) or 'N/A'}\n"
            f"Lucidity score: {payload.get('lucidity_score', 'N/A')}\n"
            f"REM: {payload.get('rem_minutes', 'N/A')} min | "
            f"Deep: {payload.get('deep_sleep_minutes', 'N/A')} min | "
            f"Total: {payload.get('total_sleep_minutes', 'N/A')} min"
        )
        await bot.send_message(chat_id=chat_id, text=summary, reply_markup=self.main_menu_keyboard())

        interpretation = self.llm.interpret_dream(payload)
        await bot.send_message(chat_id=chat_id, text=interpretation)

    async def show_index(self, query, user_id: int) -> None:
        entries = self.db.get_recent_entries(user_id, limit=12)
        if not entries:
            await query.message.reply_text("No entries yet. Start with New Dream Entry.")
            return

        lines = ["Dream Index (latest 12):"]
        for i, item in enumerate(entries, start=1):
            date = item.get("entry_date") or item.get("created_at", "")
            title = item.get("title", "Untitled")
            kinds = ", ".join(item.get("dream_types", []))
            lines.append(f"{i}. {date} | {title} | {kinds}")

        await query.message.reply_text("\n".join(lines))

    async def interpret_last(self, query, user_id: int) -> None:
        last = self.db.get_last_entry(user_id)
        if not last:
            await query.message.reply_text("No dream found. Save one first.")
            return
        await query.message.reply_text("Generating interpretation...")
        text = self.llm.interpret_dream(last)
        await query.message.reply_text(text)

    async def show_protocol(self, query, user_id: int) -> None:
        stats = self.db.get_stats(user_id)
        recent = self.db.get_recent_entries(user_id, limit=14)

        baseline = (
            "Lucid Dream Protocol (baseline):\n"
            "- Morning: write within 3 minutes of waking.\n"
            "- Daytime: 10 reality checks tied to cues (doorways, mirrors, phone).\n"
            "- Evening: 10 minutes dream-sign review + intention script.\n"
            "- Night: optional WBTB 1-2 times/week only if rested.\n"
            "- Weekly: symbol review and trigger plan update."
        )
        await query.message.reply_text(baseline)

        ai_plan = self.llm.protocol_plan(stats, recent)
        await query.message.reply_text(ai_plan)

    async def show_stats(self, query, user_id: int) -> None:
        stats = self.db.get_stats(user_id)
        symbols = ", ".join([f"{k}({v})" for k, v in stats["top_symbols"]]) or "No recurring symbols yet"
        text = (
            "Progress Snapshot:\n"
            f"- 30-day entries: {stats['entries_30']}\n"
            f"- 30-day lucid count: {stats['lucid_30']}\n"
            f"- Lucid ratio: {stats['lucid_ratio']}%\n"
            f"- Current streak: {stats['streak']} days\n"
            f"- Top recurring symbols: {symbols}"
        )
        await query.message.reply_text(text)

    async def reality_drill(self, query) -> None:
        questions = random.sample(PROBING_QUESTIONS, k=min(3, len(PROBING_QUESTIONS)))
        text = "Reality Check Drill:\n" + "\n".join([f"- {q}" for q in questions])
        await query.message.reply_text(text)



def run() -> None:
    bot = DreamDiaryBot()
    app = bot.app()
    app.run_polling(close_loop=False)
