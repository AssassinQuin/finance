import re
from datetime import datetime

def normalize_time(time_str: str) -> str:
    """
    Normalize time string to unified format: YYYY-MM-DD HH:mm
    """
    if not time_str or time_str in ["Parse Error", "N/A", ""]:
        return "-"

    # Normalize separators
    time_str = time_str.replace("/", "-").strip()

    # Format: YYYY-MM-DD HH:mm:ss -> YYYY-MM-DD HH:mm
    # Also matches YYYY-MM-DD HH:mm
    match = re.match(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})(?::\d{2})?", time_str)
    if match:
        return f"{match.group(1)} {match.group(2)}"

    # Format: YYYY-MM-DD -> YYYY-MM-DD 00:00 (Unified format for dates without time)
    match = re.match(r"^(\d{4}-\d{2}-\d{2})$", time_str)
    if match:
        return f"{match.group(1)} 00:00"

    # Format: HH:mm:ss -> YYYY-MM-DD HH:mm
    # Also matches HH:mm
    match = re.match(r"^(\d{2}:\d{2})(?::\d{2})?$", time_str)
    if match:
        today = datetime.now().strftime("%Y-%m-%d")
        return f"{today} {match.group(1)}"

    return time_str
