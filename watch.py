"""Check Sala Mirari (Amelia booking) events and send a Telegram message
whenever the number of remaining places changes."""
import json
import os
import pathlib
import urllib.parse
import urllib.request

EVENT_IDS = os.environ.get("EVENT_IDS", "527").split(",")
TOKEN = "9062101411:AAEGQW634hhCJEw2u34oZt7asuqRylt1G6k"
CHAT_ID = "9009807387"
STATE = pathlib.Path("state.json")
API = "https://salamirari.com/wp-admin/admin-ajax.php?action=wpamelia_api&call=/events&page=1&id[]={}"


def get(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def telegram(text):
    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
    get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data)


state = json.loads(STATE.read_text()) if STATE.exists() else {}

for eid in EVENT_IDS:
    eid = eid.strip()
    ev = json.loads(get(API.format(eid)))["data"]["events"][0]
    places, cap, name = ev["places"], ev["maxCapacity"], ev["name"]
    prev = state.get(eid)
    print(f"{name}: {places}/{cap} left (before: {prev})")
    if prev is None:
        telegram(f"👀 Vigilando {name}: quedan {places} de {cap} plazas")
    elif places != prev:
        diff = prev - places
        what = f"🎟️ {diff} vendida(s)" if diff > 0 else f"↩️ {-diff} liberada(s)"
        telegram(
            f"{what} – {name}\nQuedan {places} de {cap} plazas ({cap - places} vendidas)"
        )
    state[eid] = places

STATE.write_text(json.dumps(state))
