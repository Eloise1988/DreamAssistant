from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError


class Database:
    def __init__(self, uri: str, db_name: str) -> None:
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.users: Collection = self.db["users"]
        self.entries: Collection = self.db["dream_entries"]
        self.exercises: Collection = self.db["lucid_exercises"]
        self.reality_checks: Collection = self.db["reality_check_validations"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.users.create_index("telegram_id", unique=True)
        self.entries.create_index([("telegram_id", 1), ("created_at", -1)])
        self.exercises.create_index("slug", unique=True)
        self.reality_checks.create_index([("telegram_id", 1), ("reminder_key", 1)], unique=True)
        self.reality_checks.create_index([("telegram_id", 1), ("local_date", 1)])

    def ensure_user(self, telegram_id: int, username: str | None, chat_id: int | None = None) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        updates = {
            "username": username,
            "updated_at": now,
        }
        if chat_id is not None:
            updates["chat_id"] = chat_id

        self.users.update_one(
            {"telegram_id": telegram_id},
            {
                "$setOnInsert": {
                    "telegram_id": telegram_id,
                    "created_at": now,
                    "streak": 0,
                },
                "$set": updates,
            },
            upsert=True,
        )
        return self.users.find_one({"telegram_id": telegram_id}) or {}

    def save_entry(self, telegram_id: int, entry: dict[str, Any]) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            **entry,
            "telegram_id": telegram_id,
            "created_at": now,
            "updated_at": now,
        }
        result = self.entries.insert_one(payload)
        self._update_streak(telegram_id)
        return str(result.inserted_id)

    def get_last_entry(self, telegram_id: int) -> dict[str, Any] | None:
        return self.entries.find_one({"telegram_id": telegram_id}, sort=[("created_at", -1)])

    def get_recent_entries(self, telegram_id: int, limit: int = 30) -> list[dict[str, Any]]:
        return list(self.entries.find({"telegram_id": telegram_id}).sort("created_at", -1).limit(limit))

    def seed_exercises(self, exercises: list[dict[str, Any]]) -> int:
        now = datetime.now(timezone.utc)
        inserted = 0
        for exercise in exercises:
            slug = str(exercise.get("slug", "")).strip()
            if not slug:
                continue
            result = self.exercises.update_one(
                {"slug": slug},
                {
                    "$set": {
                        **exercise,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
            if result.upserted_id is not None:
                inserted += 1
        return inserted

    def get_random_exercise(self) -> dict[str, Any] | None:
        rows = list(self.exercises.aggregate([{"$sample": {"size": 1}}]))
        return rows[0] if rows else None

    def get_users_with_chat_id(self) -> list[dict[str, Any]]:
        return list(self.users.find({"chat_id": {"$exists": True}}, {"telegram_id": 1, "chat_id": 1, "_id": 0}))

    def record_reality_check(self, telegram_id: int, reminder_key: str, local_date: str) -> bool:
        now = datetime.now(timezone.utc)
        payload = {
            "telegram_id": telegram_id,
            "reminder_key": reminder_key,
            "local_date": local_date,
            "created_at": now,
        }
        try:
            self.reality_checks.insert_one(payload)
        except DuplicateKeyError:
            return False
        return True

    def get_reality_check_count(self, telegram_id: int, local_date: str) -> int:
        return int(self.reality_checks.count_documents({"telegram_id": telegram_id, "local_date": local_date}))

    def get_stats(self, telegram_id: int) -> dict[str, Any]:
        entries_30 = self.get_recent_entries(telegram_id, limit=30)
        recalled_entries = [e for e in entries_30 if not e.get("no_dream_recall", False)]
        no_recall_entries = [e for e in entries_30 if e.get("no_dream_recall", False)]
        lucid_count = sum(1 for e in recalled_entries if "Lucid" in e.get("dream_types", []))
        recurring = {}
        for e in recalled_entries:
            symbols = str(e.get("symbols", "")).split(",")
            for raw in symbols:
                s = raw.strip().lower()
                if s:
                    recurring[s] = recurring.get(s, 0) + 1
        top_symbols = sorted(recurring.items(), key=lambda it: it[1], reverse=True)[:5]
        user = self.users.find_one({"telegram_id": telegram_id}) or {}

        def average_sleep_minutes(rows: list[dict[str, Any]]) -> float | None:
            values = [v for v in (row.get("total_sleep_minutes") for row in rows) if isinstance(v, int)]
            if not values:
                return None
            return round(sum(values) / len(values), 1)

        return {
            "entries_30": len(entries_30),
            "recalled_30": len(recalled_entries),
            "no_recall_30": len(no_recall_entries),
            "lucid_30": lucid_count,
            "lucid_ratio": round((lucid_count / len(recalled_entries)) * 100, 1) if recalled_entries else 0,
            "avg_sleep_recalled": average_sleep_minutes(recalled_entries),
            "avg_sleep_no_recall": average_sleep_minutes(no_recall_entries),
            "streak": int(user.get("streak", 0)),
            "top_symbols": top_symbols,
        }

    def _update_streak(self, telegram_id: int) -> None:
        today = datetime.now(timezone.utc).date()
        start = datetime.combine(today - timedelta(days=60), datetime.min.time(), tzinfo=timezone.utc)
        recent = list(
            self.entries.find(
                {"telegram_id": telegram_id, "created_at": {"$gte": start}},
                {"created_at": 1, "_id": 0},
            ).sort("created_at", -1)
        )

        unique_days = []
        seen = set()
        for row in recent:
            day = row["created_at"].date()
            if day not in seen:
                seen.add(day)
                unique_days.append(day)

        streak = 0
        cursor = today
        day_set = set(unique_days)
        while cursor in day_set:
            streak += 1
            cursor = cursor - timedelta(days=1)

        self.users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"streak": streak, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
