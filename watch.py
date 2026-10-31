"""Sala Mirari seat watcher.
Runs for RUN_MINUTES, checking every INTERVAL seconds, and sends a Telegram
message whenever the remaining places of an event change.
Network hiccups are retried and never crash the run."""
import json
import os
import pathlib
import subprocess
import time
import urllib.parse
import urllib.request

EVENT_IDS = [e.strip() for e in os.environ.get("EVENT_IDS", "527").split(",")]
TOKEN = os.environ["TG_TOKEN"].strip()
CHAT_ID = os.environ["TG_CHAT_ID"].strip()
INTERVAL = int(os.environ.get("INTERVAL", "180"))  # seconds between checks
RUN_MINUTES = int(
    os.environ.get("RUN_MINUTES", "345")
)  # how long one run keeps looping
STATE = pathlib.Path("state.json")
API = "https://salamirari.com/wp-admin/admin-ajax.php?action=wpamelia_api&call=/events&page=1&id[]={}"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36",
    "Referer": "https://salamirari.com/reservar/",
}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def get(url, data=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode()
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code < 500:  # 4xx won't fix itself by retrying
                raise RuntimeError(f"HTTP {e.code}: {body}")
            err = f"HTTP {e.code}"
        except Exception as e:  # network unreachable, timeouts, ...
            err = repr(e)
        log(f"  attempt {i+1} failed: {err}")
        time.sleep(10 * (i + 1))
    raise RuntimeError(f"gave up after {tries} attempts: {err}")


def telegram(text):
    try:
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
        get(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data)
        log("  telegram sent")
    except Exception as e:
        log(f"  TELEGRAM FAILED (did you block the bot? press Start): {e}")


def save(state):
    STATE.write_text(json.dumps(state))
    if os.environ.get("GITHUB_ACTIONS"):  # persist between runs
        cmds = [
            ["git", "add", "state.json"],
            ["git", "commit", "-qm", "update seats"],
            ["git", "pull", "-q", "--rebase"],
            ["git", "push", "-q"],
        ]
        for c in cmds:
            subprocess.run(c, check=False)


state = json.loads(STATE.read_text()) if STATE.exists() else {}
end = time.time() + RUN_MINUTES * 60

while True:
    for eid in EVENT_IDS:
        try:
            ev = json.loads(get(API.format(eid)))["data"]["events"][0]
        except Exception as e:
            log(f"event {eid}: could not read ({e}) - will retry next round")
            continue
        places, cap, name = ev["places"], ev["maxCapacity"], ev["name"]
        prev = state.get(eid)
        log(f"{name}: {places}/{cap} left (before: {prev})")
        if prev is None:
            telegram(f"👀 Vigilando {name}: quedan {places} de {cap} plazas")
        elif places != prev:
            diff = prev - places
            what = f"🎟️ {diff} vendida(s)" if diff > 0 else f"↩️ {-diff} liberada(s)"
            telegram(
                f"{what} – {name}\nQuedan {places} de {cap} plazas ({cap - places} vendidas)"
            )
        if places != prev:
            state[eid] = places
            save(state)
    if time.time() + INTERVAL > end:
        break
    time.sleep(INTERVAL)
log("done, next run will take over")
