from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection


class Database:
    def __init__(self, uri: str, db_name: str) -> None:
        self.client = MongoClient(uri)
        self.db = self.client[db_name]
        self.users: Collection = self.db["users"]
        self.entries: Collection = self.db["dream_entries"]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        self.users.create_index("telegram_id", unique=True)
        self.entries.create_index([("telegram_id", 1), ("created_at", -1)])

    def ensure_user(self, telegram_id: int, username: str | None) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        self.users.update_one(
            {"telegram_id": telegram_id},
            {
                "$setOnInsert": {
                    "telegram_id": telegram_id,
                    "created_at": now,
                    "streak": 0,
                },
                "$set": {
                    "username": username,
                    "updated_at": now,
                },
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

    def get_stats(self, telegram_id: int) -> dict[str, Any]:
        entries_30 = self.get_recent_entries(telegram_id, limit=30)
        lucid_count = sum(1 for e in entries_30 if "Lucid" in e.get("dream_types", []))
        recurring = {}
        for e in entries_30:
            symbols = str(e.get("symbols", "")).split(",")
            for raw in symbols:
                s = raw.strip().lower()
                if s:
                    recurring[s] = recurring.get(s, 0) + 1
        top_symbols = sorted(recurring.items(), key=lambda it: it[1], reverse=True)[:5]
        user = self.users.find_one({"telegram_id": telegram_id}) or {}

        return {
            "entries_30": len(entries_30),
            "lucid_30": lucid_count,
            "lucid_ratio": round((lucid_count / len(entries_30)) * 100, 1) if entries_30 else 0,
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
