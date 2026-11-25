"""Generate the static, date-indexed forecast distributed with the site."""
import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

import weather

OUTPUT = weather.ROOT / "annual-weather.json"


def forecast_days():
    tables = {
        int(path.stem.removeprefix("weather-")): weather.load_year(int(path.stem[-4:]))
        for path in sorted((weather.ROOT / "data").glob("weather-*.json"))
        if re.fullmatch(r"weather-[0-9]{4}", path.stem)
    }
    days = {}
    for year in tables:
        day, end = date(year, 1, 1), date(year + 1, 1, 1)
        while day < end:
            forecast = weather.build_day(day, tables, include_ids=True)
            del forecast["periods"]
            days[day.isoformat()] = forecast
            day += timedelta(days=1)
    return days


def annual_data(basis_date, days):
    unknown = weather.build_day(date(2026, 1, 1), {}, include_ids=True)
    return {
        "version": 1,
        "basisDate": basis_date,
        "days": days,
        "unknownWeather": unknown["weather"],
        "unknownStatus": unknown["status"],
    }


def encode(payload):
    def inline(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    days = ",\n".join(f"    {inline(day)}: {inline(forecast)}" for day, forecast in payload["days"].items())
    fields = [f"  {inline(key)}: {inline(value)}" for key, value in payload.items() if key != "days"]
    fields.append(f'  "days": {{\n{days}\n  }}')
    return "{\n" + ",\n".join(fields) + "\n}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--basis-date", type=date.fromisoformat)
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    existing = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
    previous = json.loads(existing) if existing else None
    days = forecast_days()
    if not days:
        parser.error("No annual sources found.")
    if args.check:
        if not previous or annual_data(previous["basisDate"], days) != previous:
            parser.error("Annual display data is out of date.")
        return
    basis = args.basis_date.isoformat()
    if previous and days == previous["days"]:
        basis = previous["basisDate"]
    elif previous and basis < previous["basisDate"]:
        parser.error("The basis date cannot precede the previous release.")
    content = encode(annual_data(basis, days))
    if content != existing:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=OUTPUT.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(content)
        temp.replace(OUTPUT)
    print(f"{len(days)} calendar dates, basis date {basis}")


if __name__ == "__main__":
    main()
