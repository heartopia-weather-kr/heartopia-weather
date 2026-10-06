import asyncio
import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright


# ============================================================
# 기본 설정
# ============================================================

URL = "https://heartopia.th.gl/forecast"
OUTPUT_FILE = "weather.json"
KST = ZoneInfo("Asia/Seoul")


# ============================================================
# 날씨 이름 / 아이콘
# ============================================================

def korean_weather(weather):
    if re.match(r"^Meteor Shower(?:\s+\d+)?$", weather, re.IGNORECASE):
        return "유성우"
    if re.match(r"^Rainbow(?:\s+\d+)?$", weather, re.IGNORECASE):
        return "무지개"
    if re.match(r"^Aurora(?:\s+\d+)?$", weather, re.IGNORECASE):
        return "오로라"

    names = {
        "Sunny": "맑음",
        "Clear": "쾌청",
        "Cloudy": "흐림",
        "Sunshower": "여우비",
        "Light Rain": "약한 비",
        "Moderate Rain": "보통 비",
        "Moon Rain": "달빛 비",
        "Snow": "눈",
    }
    return names.get(weather, weather)


def weather_icon(weather):
    if re.match(r"^Meteor Shower(?:\s+\d+)?$", weather, re.IGNORECASE):
        return "☄️"
    if re.match(r"^Rainbow(?:\s+\d+)?$", weather, re.IGNORECASE):
        return "🌈"
    if re.match(r"^Aurora(?:\s+\d+)?$", weather, re.IGNORECASE):
        return "🌌"

    icons = {
        "Sunny": "☀️",
        "Clear": "🌤️",
        "Cloudy": "☁️",
        "Sunshower": "🦊",
        "Light Rain": "🌦️",
        "Moderate Rain": "🌧️",
        "Moon Rain": "🌙",
        "Snow": "❄️",
    }
    return icons.get(weather, "❓")


# ============================================================
# 특수 날씨 판정
# 무지개만 숫자를 무시하고, 유성우/오로라는 숫자 차이도 구분
# ============================================================

def normalize_weather(weather):
    weather = weather.strip()

    # 무지개만 뒤의 숫자가 있더라도 같은 날씨로 처리
    if re.match(
        rf"^{re.escape('Rainbow')}(?:\s+\d+)?$",
        weather,
        re.IGNORECASE,
    ):
        return "rainbow"

    # 유성우 / 오로라는 1, 2, 3 숫자 차이도
    # 실제 날씨 변경으로 구분
    return weather.lower()


def is_weather_changed(hour, weather, previous_weather):
    # 00 / 06 / 12 / 18시는 무조건 변경
    if hour in [0, 6, 12, 18]:
        return True

# 날씨 이름과 숫자까지 비교하여 변경 여부 판단
    return normalize_weather(weather) != normalize_weather(previous_weather)


# ============================================================
# 날짜 선택
# ============================================================

async def select_month(page, target_date):
    month_buttons = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
    }

    month_name = month_buttons[target_date.month]

    print(f"{target_date.strftime('%Y-%m-%d')} 날짜 선택 중...")

    button = page.get_by_role(
        "button",
        name=month_name,
        exact=True,
    )
    await button.click()
    await page.wait_for_timeout(400)


async def select_day(page, target_date):
    day = target_date.day
    buttons = page.locator("button")
    count = await buttons.count()
    candidates = []

    for i in range(count):
        button = buttons.nth(i)

        try:
            text = (await button.inner_text()).strip()
            match = re.match(r"^(\d+)", text)

            if match and int(match.group(1)) == day:
                candidates.append(button)
        except Exception:
            pass

    if not candidates:
        raise RuntimeError(
            f"{target_date.strftime('%Y-%m-%d')} 날짜 버튼을 찾지 못했습니다."
        )

    await candidates[-1].click()
    await page.wait_for_timeout(600)


async def select_date(page, target_date):
    await select_month(page, target_date)
    await select_day(page, target_date)


# ============================================================
# 시간별 날씨 읽기
# ============================================================

async def read_hourly_forecast(page):
    text = await page.locator("body").inner_text()

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    weather = {}
    time_pattern = re.compile(r"^(\d{2}):00$")

    for i, line in enumerate(lines):
        match = time_pattern.match(line)

        if not match:
            continue

        hour = int(match.group(1))

        for j in range(i + 1, min(i + 6, len(lines))):
            candidate = lines[j]

            if time_pattern.match(candidate):
                break

            if candidate in [
                "Dawn 00–06",
                "Morning 06–12",
                "Afternoon 12–18",
                "Evening 18–24",
            ]:
                continue

            if candidate in [
                "☄️", "🌈", "🌌", "🌦️", "❄️",
                "🔥", "🌸", "☀️", "☁️", "🌙", "🌧️",
            ]:
                continue

            # 유성우 / 오로라는 바로 다음 줄의
            # 1, 2, 3 variant까지 함께 저장
            if candidate in ["Meteor Shower", "Aurora"]:
                variant = None

                if j + 1 < len(lines):
                    next_line = lines[j + 1]

                    if next_line in ["1", "2", "3"]:
                        variant = next_line

                if variant:
                    weather[hour] = f"{candidate} {variant}"
                else:
                    weather[hour] = candidate
            else:
                weather[hour] = candidate

            break

    return weather

# ============================================================
# 웹사이트용 24시간 데이터 만들기
# 06:00 ~ 오늘 23:00 + 다음날 00:00 ~ 05:00
# ============================================================

def build_weather_data(today, tomorrow, today_weather, tomorrow_weather):
    rows = []
    changed_count = 0

    hours = list(range(6, 24)) + list(range(0, 6))

    for index, hour in enumerate(hours):
        source = today_weather if hour >= 6 else tomorrow_weather
        weather = source[hour]

        if index == 0:
            previous_weather = today_weather[5]
        elif hour == 0:
            previous_weather = today_weather[23]
        else:
            previous_source = today_weather if hour > 6 else tomorrow_weather
            previous_weather = previous_source[hour - 1]

        changed = is_weather_changed(
            hour,
            weather,
            previous_weather,
        )

        if changed:
            changed_count += 1

        rows.append({
            "time": f"{hour:02d}:00",
            "weather": weather,
            "name": korean_weather(weather),
            "icon": weather_icon(weather),
            "changed": changed,
            "mark": "⭕" if changed else "❌",
            "special": (
                weather.lower().startswith("meteor shower")
                or weather.lower().startswith("aurora")
                or normalize_weather(weather) == "rainbow"
            ),
        })

    change_rate = round((changed_count / 24) * 100, 1)

    if change_rate <= 25:
        status = "🟢 안정적"
    elif change_rate <= 50:
        status = "🟡 보통"
    elif change_rate <= 75:
        status = "🟠 변화 많음"
    else:
        status = "🔴 매우 잦음"

    periods = [
        {"key": "morning", "label": "06:00 ~ 11:00", "start": 0, "end": 6},
        {"key": "afternoon", "label": "12:00 ~ 17:00", "start": 6, "end": 12},
        {"key": "evening", "label": "18:00 ~ 23:00", "start": 12, "end": 18},
        {"key": "dawn", "label": "00:00 ~ 05:00", "start": 18, "end": 24},
    ]

    period_data = []

    for period in periods:
        period_rows = rows[period["start"]:period["end"]]
        period_changes = sum(1 for row in period_rows if row["changed"])

        period_data.append({
            "key": period["key"],
            "label": period["label"],
            "changes": period_changes,
            "weather": period_rows,
        })

    return {
        "startDate": today.strftime("%Y-%m-%d"),
        "endDate": tomorrow.strftime("%Y-%m-%d"),
        "dateLabel": f"{today.month}월 {today.day}일 ~ {tomorrow.month}월 {tomorrow.day}일",
        "timeRange": "06:00 ~ 다음날 05:00",
        "updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "updatedTime": datetime.now(KST).strftime("%H:%M"),
        "changes": changed_count,
        "changeRate": change_rate,
        "status": status,
        "weather": rows,
        "periods": period_data,
    }


# ============================================================
# weather.json 저장
# ============================================================

def save_weather_json(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"✅ {OUTPUT_FILE} 저장 완료")
    print(f"📅 총 {len(data['days'])}일치 날씨 저장")

    for index, day in enumerate(data["days"], start=1):
        print(
            f"{index}일차 · {day['dateLabel']} · "
            f"전체 변경 {day['changes']}회 · "
            f"변동률 {day['changeRate']}% {day['status']}"
        )


# ============================================================
# 실행
# ============================================================

async def main():
    now = datetime.now(KST)

    # 게임 날짜는 오전 06:00 기준으로 변경
    if now.hour < 6:
        base_date = now - timedelta(days=1)
    else:
        base_date = now

    # 7일치 게임 날짜를 만들기 위해
    # 오늘부터 7일 뒤까지 총 8개의 실제 날짜가 필요함
    dates = [
        base_date + timedelta(days=i)
        for i in range(8)
    ]

    print()
    print("=" * 50)
    print("Heartopia 7일 날씨 수집")
    print("=" * 50)
    print("시작 날짜:", dates[0].strftime("%Y-%m-%d"))
    print("마지막 날짜:", dates[6].strftime("%Y-%m-%d"))
    print()

    async with async_playwright() as p:
        # GitHub Actions에서도 실행되도록 브라우저 창을 띄우지 않음
        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page(
            locale="en-US",
        )

        try:
            print("Heartopia 사이트 접속 중...")

            await page.goto(
                URL,
                wait_until="networkidle",
                timeout=60000,
            )

            # 실제 달력 날짜 8일치의 24시간 예보를 먼저 수집
            weather_by_date = {}

            for target_date in dates:
                print(
                    f"날씨 읽는 중: "
                    f"{target_date.strftime('%Y-%m-%d')}"
                )

                await select_date(page, target_date)
                hourly_weather = await read_hourly_forecast(page)

                if len(hourly_weather) != 24:
                    raise RuntimeError(
                        f"{target_date.strftime('%Y-%m-%d')} "
                        f"날씨를 24시간 모두 읽지 못했습니다. "
                        f"현재 {len(hourly_weather)}개"
                    )

                weather_by_date[
                    target_date.strftime("%Y-%m-%d")
                ] = hourly_weather

                print(
                    f"✅ {target_date.strftime('%Y-%m-%d')} "
                    f"날씨 읽기 완료"
                )

            # 수집한 8일 데이터를 이용해
            # 06:00 ~ 다음날 05:00 기준의 7일치 데이터를 만듦
            days = []

            for i in range(7):
                today = dates[i]
                tomorrow = dates[i + 1]

                today_weather = weather_by_date[
                    today.strftime("%Y-%m-%d")
                ]
                tomorrow_weather = weather_by_date[
                    tomorrow.strftime("%Y-%m-%d")
                ]

                day_data = build_weather_data(
                    today,
                    tomorrow,
                    today_weather,
                    tomorrow_weather,
                )

                days.append(day_data)

            data = {
                "updated": datetime.now(KST).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "updatedTime": datetime.now(KST).strftime("%H:%M"),
                "days": days,
            }

            save_weather_json(data)

        finally:
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print()
        print("=" * 50)
        print("❌ 오류 발생")
        print(e)
        print("=" * 50)
        raise
