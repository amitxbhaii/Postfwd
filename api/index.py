import os
import json
import re
import requests
from http.server import BaseHTTPRequestHandler

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

DEST_CHAT_ID = -1002822227530
STORAGE_FILE = "/tmp/store.json"   # ✅ Vercel safe temp storage

# ---------------- STORAGE ----------------
if not os.path.exists(STORAGE_FILE):
    with open(STORAGE_FILE, "w") as f:
        json.dump([], f)

def load_store():
    try:
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_store(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)

# ---------------- HELPERS ----------------
def send_message(chat_id, text):
    requests.post(
        f"{API_URL}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        },
        timeout=10
    )

def cut_at_emoji(text):
    for i, ch in enumerate(text):
        if ord(ch) > 10000:
            return text[:i].strip()
    return text.strip()

def extract_bot_number(username):
    clean = username.replace("_", "")
    m = re.search(r"(\d{1,2})Bot$", clean, re.I)
    return int(m.group(1)) if m else None

# ---------------- HANDLER ----------------
class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length))

        msg = body.get("message")
        if not msg:
            self.respond()
            return

        chat_id = msg["chat"]["id"]
        text = msg.get("text") or msg.get("caption") or ""

        # ---------- FORWARDED CHANNEL MESSAGE ----------
        if msg.get("forward_from_chat", {}).get("type") == "channel":

            bots = re.findall(r"@[\w_]+", text)
            numbers = [extract_bot_number(b) for b in bots if extract_bot_number(b)]

            m = re.search(r"CHANNEL NAME\s*[-:]?\s*(.+)", text, re.I)
            if not m or not numbers:
                self.respond()
                return

            base = cut_at_emoji(m.group(1))
            num = numbers[0]

            if not (1 <= num <= 100):
                self.respond()
                return

            store = load_store()
            store.append({"name": base, "num": num})
            save_store(store)

            send_message(
                DEST_CHAT_ID,
                f"Bot :-{num}\n\n`{base}`"
            )

        # ---------- .all ----------
        elif text == ".all" and chat_id == DEST_CHAT_ID:
            store = sorted(load_store(), key=lambda x: x["num"])
            if not store:
                send_message(chat_id, "📦 Empty.")
            else:
                send_message(
                    chat_id,
                    "\n".join(f"{x['name']} {x['num']}" for x in store)
                )

        # ---------- .allx ----------
        elif text == ".allx" and chat_id == DEST_CHAT_ID:
            store = load_store()
            if not store:
                send_message(chat_id, "📦 Empty.")
            else:
                grouped = {}
                for e in store:
                    grouped.setdefault(e["num"], []).append(e["name"])

                out = []
                for num in sorted(grouped):
                    names = grouped[num]
                    for i, name in enumerate(names):
                        if i < len(names) - 1:
                            out.append(f"{num}. `{name}` ❌")
                        else:
                            out.append(f"{num}. `{name}`")
                            out.append("")
                send_message(chat_id, "\n".join(out))

        # ---------- .reset ----------
        elif text == ".reset" and chat_id == DEST_CHAT_ID:
            save_store([])
            send_message(chat_id, "✅ All data reset.")

        self.respond()

    def respond(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        self.respond()
        self.wfile.write(b"Bot running")
