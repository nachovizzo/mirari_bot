"""Check Sala Mirari (Amelia booking) events and send a WhatsApp via CallMeBot
whenever the number of remaining places changes."""
import json
import os
import pathlib
import urllib.parse
import urllib.request

EVENT_IDS = os.environ.get("EVENT_IDS", "527").split(",")
PHONE = os.environ["WA_PHONE"]  # e.g. +34612345678
APIKEY = os.environ["WA_APIKEY"]  # from CallMeBot
STATE = pathlib.Path("state.json")
API = "https://salamirari.com/wp-admin/admin-ajax.php?action=wpamelia_api&call=/events&page=1&id[]={}"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def whatsapp(text):
    q = urllib.parse.urlencode({"phone": PHONE, "text": text, "apikey": APIKEY})
    get("https://api.callmebot.com/whatsapp.php?" + q)


state = json.loads(STATE.read_text()) if STATE.exists() else {}

for eid in EVENT_IDS:
    eid = eid.strip()
    ev = json.loads(get(API.format(eid)))["data"]["events"][0]
    places, cap, name = ev["places"], ev["maxCapacity"], ev["name"]
    prev = state.get(eid)
    print(f"{name}: {places}/{cap} left (before: {prev})")
    if prev is not None and places != prev:
        diff = prev - places
        what = f"🎟️ {diff} vendida(s)" if diff > 0 else f"↩️ {-diff} liberada(s)"
        whatsapp(
            f"{what} – {name}\nQuedan {places} de {cap} plazas ({cap - places} vendidas)"
        )
    state[eid] = places

STATE.write_text(json.dumps(state))
