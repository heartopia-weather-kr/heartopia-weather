"""Collect explicitly formatted Heartopia redeem codes from a followed Discord channel."""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CHANNEL_ID = "1569545070234046624"
OUT = Path("redeem-codes.json")
CODE_RE = re.compile(r"(?:gift\s*code|redeem\s*code|리딤\s*코드|쿠폰\s*코드)\s*[:：]\s*[`* ]*([a-zA-Z0-9_-]{5,40})", re.I)
REWARD_RE = re.compile(r"(?:rewards?|보상)\s*[:：]\s*(.+)", re.I)
DEADLINE_RE = re.compile(r"(?:redemption\s*deadline|expiration|expires?|만료(?:일|일시)?)\s*[:：]\s*(.+)", re.I)
STAMP_RE = re.compile(r"<t:(\d{10}):[a-zA-Z]>")

def request_messages(token):
    messages = []
    before = None
    for _ in range(4):
        url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=100"
        if before:
            url += f"&before={before}"
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "HeartopiaRedeemCollector/1.0",
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

def parse(message):
    body = message_text(message)
    code = CODE_RE.search(body)
    if not code:
        return None
    rewards = REWARD_RE.search(body)
    deadline = DEADLINE_RE.search(body)
    expiry = None
    if deadline:
        stamp = STAMP_RE.search(deadline.group(1))
        if stamp:
            expiry = datetime.fromtimestamp(int(stamp.group(1)), timezone.utc).isoformat()
        else:
            # Do not guess a timezone or invent an expiry date.
            expiry = None
    return {
        "code": code.group(1),
        "rewards": rewards.group(1).strip()[:500] if rewards else "",
        "expiresAt": expiry,
        "source": f"https://discord.com/channels/{message.get('guild_id', '@me')}/{CHANNEL_ID}/{message['id']}",
        "postedAt": message.get("timestamp"),
    }

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
            by_code[item["code"].lower()] = item
            found += 1
    codes = sorted(by_code.values(), key=lambda x: x.get("postedAt") or "", reverse=True)
    # Avoid noisy commits on every scheduled run.
    data = {"codes": codes}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Discord messages checked: {len(messages)}; formatted code posts: {found}; saved codes: {len(codes)}")
    if not messages:
        print("No messages yet; verify official announcement forwarding separately.")

if __name__ == "__main__":
    main()
