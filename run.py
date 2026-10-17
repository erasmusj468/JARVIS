"""Run the local JARVIS web app and its lightweight Python command API."""

from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path
import json
import re
import webbrowser

ROOT = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", 8000


def command_reply(prompt: str) -> str:
    text = prompt.lower()
    now = datetime.now().astimezone()
    clock = now.strftime("%I:%M %p").lstrip("0")
    if re.search(r"\b(time|clock)\b", text):
        return f"It's {clock} in your local time zone."
    if re.search(r"\b(date|day|today)\b", text):
        return f"Today is {now.strftime('%A, %B')} {now.day}, {now.year}."
    if re.search(r"brief|morning|start.*day", text):
        return f"Here's your quick briefing: it's {clock} on {now.strftime('%A, %B')} {now.day}. I'm ready when you are. Connect an AI provider for news, calendar, and task summaries."
    if re.search(r"interesting|surprise", text):
        return "A day on Venus is longer than its year. Venus takes about 243 Earth days to rotate once, and about 225 Earth days to orbit the Sun."
    if re.search(r"capabilit|what can you|help", text):
        return "I can tell you the local time and date, listen for your voice, and speak my replies. Connect an AI provider to add general conversation, research, and your own tools."
    return "I'm in local demo mode, so I can't answer that one yet. Connect an AI provider for open conversations. For now, ask me for the time, date, a quick briefing, or what I can do."


class JarvisHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/command":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
            prompt = str(data.get("prompt", ""))[:2000]
            payload = {"reply": command_reply(prompt)}
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_error(400, "Expected JSON containing a prompt")
            return
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), JarvisHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"JARVIS is running at {url} — press Ctrl+C to stop")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nJARVIS server stopped.")
    finally:
        server.server_close()
