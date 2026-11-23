"""Calendar-first Heartopia forecast from year-scoped internal tables.

A file data/weather-YYYY.json is authoritative ONLY for its named year.
Missing years, dates, hours or unknown IDs are rendered as '?' and never
shift the calendar or borrow another year's forecast.
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "weather.json"

NAMES = {
    101: ("Sunny", "Clear"), 102: "Cloudy", 104: "Heatwave",
    105: "Cloudy", 106: "Petal Rain",
    119: "Aurora 1", 120: "Aurora 2", 121: "Aurora 3",
    201: ("Sunshower", "Moon Rain"), 202: "Light Rain",
    203: "Moderate Rain", 204: "Heavy Rain",
    211: "Light Snow", 212: "Moderate Snow", 213: "Heavy Snow",
    301: "Moon Rainbow", 302: "Moon Rainbow",
    303: "Rainbow", 304: "Rainbow", 305: "Moon Rainbow",
}
for _index in range(107, 119):
    NAMES[_index] = "Meteor Shower " + str((_index - 107) % 3 + 1)

KO = {
    "Sunny": "맑음", "Clear": "쾌청", "Cloudy": "흐림",
    "Heatwave": "폭염", "Petal Rain": "꽃잎 비",
    "Sunshower": "여우비", "Moon Rain": "달빛 비",
    "Light Rain": "약한 비", "Moderate Rain": "보통 비",
    "Heavy Rain": "강한 비", "Light Snow": "약한 눈",
    "Moderate Snow": "보통 눈", "Heavy Snow": "강한 눈",
    "Rainbow": "무지개", "Moon Rainbow": "달 무지개",
}
ICONS = {
    "Sunny": "☀️", "Clear": "🌤️", "Cloudy": "☁️",
    "Heatwave": "🔥", "Petal Rain": "🌸",
    "Sunshower": "🦊", "Moon Rain": "🌙",
    "Light Rain": "🌦️", "Moderate Rain": "🌧️", "Heavy Rain": "🌧️",
    "Light Snow": "❄️", "Moderate Snow": "❄️", "Heavy Snow": "❄️",
    "Rainbow": "🌈", "Moon Rainbow": "🌈",
}

def weather_name(identifier, hour):
    value = NAMES.get(identifier)
    if isinstance(value, tuple):
        return value[0] if 6 <= hour < 18 else value[1]
    return value

def normalized(value):
    if value is None:
        return None
    return "rainbow" if re.fullmatch(r"Rainbow(?:\\s+\\d+)?", value, re.I) else value.lower()

def load_year(year):
    path = ROOT / "data" / f"weather-{year}.json"
    if not path.exists():
        return {}
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, list):
        raise ValueError(f"Invalid year table: {path}")
    indexed = {}
    for record in source:
        month, day = record["month"], record["day"]
        key = f"{year:04d}-{month:02d}-{day:02d}"
        try:
            datetime(year, month, day)
        except ValueError:
            # Leap-day entry in a non-leap year is intentionally unused.
            if month == 2 and day == 29:
                continue
            raise
        if key in indexed:
            raise ValueError(f"Duplicate weather date: {key}")
        hours = record.get("weatherIds")
        if not isinstance(hours, list) or len(hours) != 24:
            raise ValueError(f"Invalid hourly table: {key}")
        indexed[key] = hours
    return indexed

def build(now=None):
    now = now or datetime.now(KST)
    base = now.date()
    dates = [base + timedelta(days=offset) for offset in range(-1, 9)]
    tables = {date.year: load_year(date.year) for date in dates}
    def at(date, hour):
        values = tables[date.year].get(date.isoformat())
        return weather_name(values[hour], hour) if values else None
    days = []
    stamp = now.strftime("%Y-%m-%d %H:%M")
    for day in dates[1:]:
        rows = []
        for hour in range(24):
            current = at(day, hour)
            previous = at(day - timedelta(days=1), 23) if hour == 0 else at(day, hour - 1)
            changed = current is not None and previous is not None and normalized(current) != normalized(previous)
            unknown = current is None
            name = "?" if unknown else (KO.get(current) or
                ("유성우 " + current.split()[-1] if current.startswith("Meteor Shower") else
                 "오로라 " + current.split()[-1] if current.startswith("Aurora") else current))
            icon = "❓" if unknown else (
                "☄️" if current.startswith("Meteor Shower") else
                "🌌" if current.startswith("Aurora") else ICONS.get(current, "❓"))
            rows.append({
                "time": f"{hour:02d}:00", "weather": current or "Unknown",
                "name": name, "icon": icon, "changed": bool(changed),
                "mark": "?" if unknown or previous is None else ("⭕" if changed else "❌"),
                "special": bool(current and (current.startswith(("Meteor Shower", "Aurora")) or current in ("Rainbow", "Moon Rainbow"))),
            })
        changes = sum(row["changed"] for row in rows)
        # Unknown comparisons must not silently become a 0% change rate.
        complete = all(at(day, h) is not None and
                       (at(day - timedelta(days=1), 23) if h == 0 else at(day, h - 1)) is not None
                       for h in range(24))
        rate = round(changes / 24 * 100, 1) if complete else None
        status = ("❓ 확인 불가" if rate is None else
                  "🟢 안정적" if rate <= 25 else
                  "🟡 보통" if rate <= 50 else
                  "🟠 변화 많음" if rate <= 75 else "🔴 매우 잦음")
        periods = []
        for i, key in enumerate(("dawn", "morning", "afternoon", "evening")):
            subset = rows[i*6:i*6+6]
            periods.append({"key": key, "label": f"{i*6:02d}:00 ~ {i*6+5:02d}:00",
                            "changes": sum(r["changed"] for r in subset), "weather": subset})
        days.append({
            "startDate": day.isoformat(), "endDate": day.isoformat(),
            "dateLabel": f"{day.month}월 {day.day}일", "timeRange": "00:00 ~ 23:00",
            "updated": stamp, "updatedTime": now.strftime("%H:%M"),
            "changes": changes, "changeRate": rate, "status": status,
            "weather": rows, "periods": periods,
        })
    return {"updated": stamp, "updatedTime": now.strftime("%H:%M"), "days": days}

def main():
    data = build()
    OUTPUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(data['days'])} calendar dates: {data['days'][0]['startDate']} ~ {data['days'][-1]['startDate']}")

if __name__ == "__main__":
    main()
