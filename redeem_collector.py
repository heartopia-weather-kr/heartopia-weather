"""Collect verified Heartopia redeem codes from forwarded Discord announcements."""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CHANNEL_ID = "1569545070234046624"
OUT = Path("redeem-codes.json")
KST = ZoneInfo("Asia/Seoul")
CODE_RE = re.compile(r"(?:gift\s*code|redeem\s*code|redemption\s*code|리딤\s*코드|쿠폰\s*코드|쿠폰코드)\s*[:：]\s*[`* ]*([a-zA-Z0-9_-]{5,40})", re.I)
REWARD_RE = re.compile(r"(?:rewards?|보상(?:\s*목록)?|선물\s*목록)[ \t]*[:：]?[ \t]*([^\n]*)", re.I)
DEADLINE_RE = re.compile(r"(?:redemption\s*deadline|expiration|expires?|교환\s*마감|사용\s*기한|사용\s*기간|만료(?:일|일시)?)\s*[:：]\s*([^\n]+)", re.I)
STAMP_RE = re.compile(r"<t:(\d{10}):[a-zA-Z]>")
KOREAN_DATE_RE = re.compile(r"(20\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*(\d{1,2}):(\d{2})")
US_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})\s*,?\s*(\d{1,2}):(\d{2})")
EN_DATE_RE = re.compile(r"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})\s+(?:at\s+)?(\d{1,2}):(\d{2})", re.I)
MONTHS = {name.lower(): i for i, name in enumerate(("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"), 1)}
TRANSLATIONS = (
    ("Mermaid Fish Attractor", "인어 집어기"),
    ("Wishing star", "소원별"),
    ("Fertilizer", "비료"),
    ("Pumpkin Seeds", "호박 씨앗"),
    ("Roaming Oak Timber", "그 자리 참나무"),
    ("Quality Fertilizer", "고급 비료"),
    ("Quality Timber", "고급 목재"),
)
STOP_RE = re.compile(r"(?:gift\s*code|redeem\s*code|리딤\s*코드|쿠폰\s*코드|redemption\s*deadline|사용\s*기한|사용\s*기간|만료|교환\s*마감|https?://)", re.I)

def request_messages(token):
    messages = []
    before = None
    for _ in range(4):
        url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=100"
        if before:
            url += f"&before={before}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "HeartopiaRedeemCollector/1.1",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                page = json.load(response)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"Discord HTTP {error.code}") from None
        if not isinstance(page, list):
            raise RuntimeError("Unexpected Discord response")
        messages.extend(page)
        if len(page) < 100:
            break
        before = page[-1]["id"]
    return messages

def message_text(message):
    parts = [message.get("content") or ""]
    for embed in message.get("embeds") or []:
        parts.extend([embed.get("title") or "", embed.get("description") or ""])
        for field in embed.get("fields") or []:
            parts.append(f"{field.get('name', '')}: {field.get('value', '')}")
    return "\n".join(parts)

def parse_expiry(value):
    if not value:
        return None
    stamp = STAMP_RE.search(value)
    if stamp:
        return datetime.fromtimestamp(int(stamp.group(1)), timezone.utc).isoformat()
    match = KOREAN_DATE_RE.search(value)
    if match:
        year, month, day, hour, minute = map(int, match.groups())
    else:
        match = US_DATE_RE.search(value)
        if match:
            month, day, year, hour, minute = map(int, match.groups())
            if year < 100:
                year += 2000
        else:
            match = EN_DATE_RE.search(value)
            if not match:
                return None
            month_name, day, year, hour, minute = match.groups()
            month = MONTHS[month_name.lower()]
            year, day, hour, minute = map(int, (year, day, hour, minute))
    try:
        # Official examples use Korean local time, including Discord's rendered dates.
        return datetime(year, month, day, hour, minute, tzinfo=KST).astimezone(timezone.utc).isoformat()
    except ValueError:
        return None

def translate_rewards(value):
    for english, korean in TRANSLATIONS:
        value = re.sub(re.escape(english), korean, value, flags=re.I)
    return value.strip()[:500]

def extract_rewards(body):
    match = REWARD_RE.search(body)
    if match:
        start = match.end()
        first = match.group(1).strip()
        if first:
            return translate_rewards(first)
        remainder = body[start:]
    else:
        marker = re.search(r"(?:freebies are ready|don't forget to claim them|작은 선물을 준비|선물을 준비|혜택 시간)", body, re.I)
        if not marker:
            return ""
        remainder = body[marker.end():]
    lines = []
    for raw in remainder.splitlines():
        line = raw.strip()
        if not line:
            if lines:
                break
            continue
        if STOP_RE.search(line):
            break
        if re.search(r"(?:[x×]\s*\d+|\d+\s*개)", line):
            lines.append(line)
        elif lines:
            break
    return translate_rewards(", ".join(lines))

def parse(message):
    body = message_text(message)
    match = CODE_RE.search(body)
    if not match:
        return None
    code = match.group(1)
    if code.lower() in {"coming", "soon", "later", "check", "today", "update", "please"}:
        return None
    deadline = DEADLINE_RE.search(body)
    return {
        "code": code,
        "rewards": extract_rewards(body),
        "expiresAt": parse_expiry(deadline.group(1)) if deadline else None,
        "source": f"https://discord.com/channels/{message.get('guild_id') or '@me'}/{CHANNEL_ID}/{message['id']}",
        "postedAt": message.get("timestamp"),
    }

def merge_items(old, new):
    """Preserve known fields; never erase a populated reward or expiry."""
    merged = dict(old)
    for field in ("rewards", "expiresAt"):
        if new.get(field) and (not merged.get(field) or (field == "rewards" and len(new[field]) > len(merged[field]))):
            merged[field] = new[field]
    # Preserve the first known source and posting time for a stable record.
    for field in ("source", "postedAt"):
        if not merged.get(field) and new.get(field):
            merged[field] = new[field]
    return merged

def main():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        sys.exit("DISCORD_BOT_TOKEN is not configured")
    messages = request_messages(token)
    existing = []
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding="utf-8")).get("codes", [])
        except (ValueError, OSError, AttributeError):
            sys.exit("Existing redeem-codes.json is invalid")
    by_code = {item["code"].lower(): item for item in existing if isinstance(item, dict) and item.get("code")}
    found = 0
    for message in reversed(messages):
        item = parse(message)
        if item:
            key = item["code"].lower()
            by_code[key] = merge_items(by_code[key], item) if key in by_code else item
            found += 1
    codes = sorted(by_code.values(), key=lambda x: x.get("postedAt") or "", reverse=True)
    data = {"codes": codes}
    serialized = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8") != serialized:
        OUT.write_text(serialized, encoding="utf-8")
    print(f"Discord messages checked: {len(messages)}; formatted code posts: {found}; ignored: {len(messages)-found}; saved codes: {len(codes)}")
    if not messages:
        print("No messages yet; verify official announcement forwarding separately.")

if __name__ == "__main__":
    main()
