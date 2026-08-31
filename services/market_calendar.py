from __future__ import annotations
from datetime import datetime, timezone, timedelta, time, date
from typing import Set

IST = timezone(timedelta(hours=5, minutes=30))

EXCHANGE_HOLIDAYS_2026: Set[date] = {
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 6),   # Mahashivratri
    date(2026, 3, 25),  # Holi
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Ambedkar Jayanti
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Mahatma Gandhi Jayanti
    date(2026, 10, 20), # Dussehra
    date(2026, 11, 8),  # Diwali Laxmi Pujan
    date(2026, 11, 10), # Diwali Balipratipada
    date(2026, 12, 25), # Christmas
}

def now_ist() -> datetime:
    return datetime.now(IST)

def is_market_open(dt: datetime | None = None) -> bool:
    t = dt or now_ist()
    if t.weekday() >= 5:
        return False
    if t.date() in EXCHANGE_HOLIDAYS_2026:
        return False
    market_start = time(9, 15, 0)
    market_end = time(15, 30, 0)
    return market_start <= t.time() <= market_end
