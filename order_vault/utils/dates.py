
from typing import Optional
from datetime import datetime, timedelta

def parse_iso_dt(s: Optional[str]) -> Optional[datetime]:
    if not s: return None
    s = s.strip()
    # Accept 'YYYY-MM-DD' or full ISO
    try:
        if len(s) == 10:
            return datetime.fromisoformat(s)  # midnight
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None

def normalize_range(start_str, end_str):
    start = parse_iso_dt(start_str)
    end = parse_iso_dt(end_str)
    # If end is date-only, bump to end-of-day (exclusive upper bound)
    if end and len(end_str.strip()) == 10:
        end = end + timedelta(days=1)
    return start, end
