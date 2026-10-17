"""JARVIS desktop assistant for Windows."""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models" / "vosk-model-small-en-us-0.15"

try:
    import sounddevice as sd
    from vosk import KaldiRecognizer, Model
except ImportError:
    sd = None
    KaldiRecognizer = Model = None


BG = "#080d13"
PANEL = "#101923"
PANEL_2 = "#131f29"
BORDER = "#253541"
TEXT = "#e7f0f4"
MUTED = "#82919c"
CYAN = "#70def0"
GREEN = "#78e4b9"


def word_distance(left: str, right: str) -> int:
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        diagonal = row[0]
        row[0] = i
        for j, b in enumerate(right, 1):
            above = row[j]
            row[j] = min(row[j] + 1, row[j - 1] + 1, diagonal + (a != b))
            diagonal = above
    return row[-1]


def wake_tail(text: str) -> str | None:
    """Return the words after a likely Jarvis wake word, if present."""
    words = re.findall(r"[a-z]+", text.lower())
    for i in range(min(4, len(words))):
        candidates = [(words[i], 1)]
        if i + 1 < len(words):
            candidates.append((words[i] + words[i + 1], 2))
        for candidate, count in candidates:
            if word_distance(candidate, "jarvis") <= 2:
                return " ".join(words[i + count :])
    return None


class JarvisApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("JARVIS | Personal Assistant")
        self.root.geometry("1020x700")
        self.root.minsize(820, 590)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.events: queue.Queue = queue.Queue()
        self.audio: queue.Queue = queue.Queue(maxsize=24)
        self.stop_event = threading.Event()
        self.speaking_event = threading.Event()
        self.listening = False
        self.voice_thread: threading.Thread | None = None
        self.voice_state = "idle"
        self.animation = 0
        self._build_ui()
        self._update_clock()
        self._animate()
        self.root.after(100, self._drain_events)
        self._add_message("JARVIS", "Good to have you here. Enable voice activation, then say “Jarvis” followed by what you need.", "assistant")

    def _build_ui(self):
        header = tk.Frame(self.root, bg=BG, padx=26, pady=19)
        header.pack(fill="x")
        tk.Label(header, text="◉  J A R V I S", bg=BG, fg=CYAN, font=("Segoe UI", 13, "bold")).pack(side="left")
        self.clock_label = tk.Label(header, text="", bg=BG, fg=MUTED, font=("Segoe UI", 10))
        self.clock_label.pack(side="right")

        body = tk.Frame(self.root, bg=BG, padx=24)
        body.pack(fill="both", expand=True)
        left = tk.Frame(body, bg=BG, width=340)
        left.pack(side="left", fill="y", padx=(0, 20))
        left.pack_propagate(False)

        self.orb = tk.Canvas(left, width=300, height=245, bg=BG, highlightthickness=0)
        self.orb.pack(pady=(23, 2))
        tk.Label(left, text="AT YOUR SERVICE.", bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(pady=(4, 5))
        self.status = tk.Label(left, text="Voice activation is off", bg=BG, fg=MUTED, font=("Segoe UI", 10), wraplength=300)
        self.status.pack(pady=(0, 17))

        self.listen_button = tk.Button(left, text="Enable voice activation", command=self.toggle_voice,
                                       bg="#12303b", fg=CYAN, activebackground="#194252", activeforeground="white",
                                       relief="flat", bd=0, padx=18, pady=11, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.listen_button.pack(fill="x", padx=12)
        tk.Label(left, text="SAY  “JARVIS, OPEN CALCULATOR”\nOR  “JARVIS, SEARCH FOR WEATHER”", bg=BG, fg="#657681",
                 font=("Consolas", 8), justify="center", pady=13).pack()

        tk.Label(left, text="QUICK ACTIONS", bg=BG, fg="#71828e", font=("Consolas", 9)).pack(anchor="w", padx=6, pady=(8, 8))
        actions = tk.Frame(left, bg=BG)
        actions.pack(fill="x", padx=4)
        for title, command in [("Calculator", "open calculator"), ("Browser", "open browser"), ("Notepad", "open notepad")]:
            tk.Button(actions, text=title, command=lambda c=command: self.handle_command(c), bg=PANEL_2, fg=TEXT,
                      activebackground="#203542", activeforeground="white", relief="flat", padx=10, pady=9,
                      font=("Segoe UI", 9), cursor="hand2").pack(fill="x", pady=3)

        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="left", fill="both", expand=True)
        row = tk.Frame(right, bg=PANEL, padx=17, pady=14)
        row.pack(fill="x")
        tk.Label(row, text="CONVERSATION", bg=PANEL, fg="#9aabb5", font=("Consolas", 9)).pack(side="left")
        tk.Button(row, text="Clear", command=self.clear_chat, bg=PANEL, fg=MUTED, activebackground=PANEL_2,
                  relief="flat", font=("Segoe UI", 9), cursor="hand2").pack(side="right")

        self.chat = tk.Text(right, bg=PANEL, fg=TEXT, insertbackground=CYAN, relief="flat", wrap="word",
                            padx=18, pady=12, font=("Segoe UI", 10), state="disabled", spacing1=3, spacing3=12)
        self.chat.pack(fill="both", expand=True, padx=5)
        self.chat.tag_configure("assistant_name", foreground=CYAN, font=("Segoe UI", 9, "bold"))
        self.chat.tag_configure("user_name", foreground="#c4d0d6", font=("Segoe UI", 9, "bold"))
        self.chat.tag_configure("body", foreground=TEXT, lmargin1=4, lmargin2=4)

        composer = tk.Frame(right, bg="#0c141b", padx=10, pady=10)
        composer.pack(fill="x", padx=8, pady=(0, 9))
        self.entry = tk.Entry(composer, bg="#0c141b", fg=TEXT, insertbackground=CYAN, relief="flat",
                              font=("Segoe UI", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=6, ipady=7)
        self.entry.insert(0, "Type a command…")
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<Return>", self._submit_entry)
        tk.Button(composer, text="Send  ↑", command=self._submit_entry, bg="#38b5ce", fg="#07171d",
                  activebackground="#69d8e8", relief="flat", padx=13, pady=7, font=("Segoe UI", 9, "bold"),
                  cursor="hand2").pack(side="right")

        self.footer = tk.Label(self.root, text="LOCAL VOICE RECOGNITION  ·  NO BROWSER REQUIRED", bg=BG, fg="#52636e",
                               font=("Consolas", 8), pady=10)
        self.footer.pack(fill="x")

    def _update_clock(self):
        self.clock_label.config(text=datetime.now().astimezone().strftime("%A, %d %B  ·  %H:%M"))
        self.root.after(1000, self._update_clock)

    def _animate(self):
        self.orb.delete("all")
        self.animation += 1
        pulse = 1 if self.voice_state == "listening" else (4 if self.voice_state == "command" else 2)
        wobble = (self.animation % 40) / 40
        for i in range(4):
            radius = 48 + i * 13 + (pulse * 1.7 if i == 0 else wobble * 3)
            color = ["#2b8090", "#236070", "#1b4654", "#15303a"][i]
            self.orb.create_oval(150-radius, 122-radius, 150+radius, 122+radius, outline=color, width=1)
        self.orb.create_oval(111, 83, 189, 161, fill="#123541", outline="#60d9e9", width=2)
        self.orb.create_oval(128, 100, 172, 144, fill="#236d7b", outline="#3c9eac", width=1)
        self.orb.create_text(150, 122, text="J", fill="#b7f5ff", font=("Consolas", 24, "bold"))
        self.root.after(70, self._animate)

    def _add_message(self, speaker: str, text: str, role: str):
        self.chat.configure(state="normal")
        tag = "user_name" if role == "user" else "assistant_name"
        self.chat.insert("end", speaker.upper() + "\n", tag)
        self.chat.insert("end", text + "\n\n", "body")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _set_status(self, state: str, text: str):
        self.voice_state = state
        self.status.config(text=text, fg=GREEN if state == "listening" else (CYAN if state == "command" else MUTED))

    def toggle_voice(self):
        if self.listening:
            self.stop_event.set()
            self.listening = False
            self._discard_audio()
            self.listen_button.config(text="Enable voice activation", bg="#12303b", fg=CYAN)
            self._set_status("idle", "Voice activation is off")
            return
        if sd is None or Model is None:
            messagebox.showerror("Voice setup needed", "Install the voice packages first:\n\npy -m pip install -r requirements.txt\n\nThen run: py setup_voice.py")
            return
        if not MODEL_DIR.exists():
            messagebox.showerror("Speech model needed", "Download the offline speech model first:\n\npy setup_voice.py")
            return
        self.stop_event = threading.Event()
        self._discard_audio()
        self.listening = True
        self.listen_button.config(text="Stop listening", bg="#18392e", fg=GREEN)
        self._set_status("listening", "Listening locally. Say “Jarvis” followed by a command.")
        self.voice_thread = threading.Thread(target=self._listen_worker, args=(self.stop_event,), daemon=True)
        self.voice_thread.start()

    def _listen_worker(self, stop_event):
        try:
            model = Model(str(MODEL_DIR))
            device = sd.default.device[0]
            sample_rate = int(sd.query_devices(device, "input")["default_samplerate"])
            recognizer = KaldiRecognizer(model, sample_rate)
            wake_mode = "wake"
            last_partial = ""
            while not stop_event.is_set():
                try:
                    with sd.RawInputStream(samplerate=sample_rate, blocksize=max(8000, int(sample_rate * 0.25)),
                                           device=device, dtype="int16", channels=1,
                                           callback=self._audio_callback):
                        while not stop_event.is_set():
                            if self.speaking_event.is_set():
                                self._discard_audio()
                                time.sleep(0.06)
                                continue
                            try:
                                data = self.audio.get(timeout=0.3)
                            except queue.Empty:
                                continue
                            if recognizer.AcceptWaveform(data):
                                text = json.loads(recognizer.Result()).get("text", "").strip()
                                last_partial = ""
                                if not text:
                                    continue
                                if wake_mode == "wake":
                                    tail = wake_tail(text)
                                    if tail is None:
                                        continue
                                    if tail:
                                        wake_mode = "wake"
                                        self.events.put(("command", tail))
                                    else:
                                        wake_mode = "command"
                                        self.speaking_event.set()
                                        self.events.put(("wake", None))
                                else:
                                    wake_mode = "wake"
                                    self.events.put(("command", text))
                            else:
                                partial = json.loads(recognizer.PartialResult()).get("partial", "").strip()
                                if partial and partial != last_partial:
                                    last_partial = partial
                                    self.events.put(("heard", partial))
                except Exception as exc:
                    self.events.put(("error", str(exc)))
                    return
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def _audio_callback(self, indata, frames, timing, status):
        if status:
            self.events.put(("audio_status", str(status)))
        try:
            self.audio.put_nowait(bytes(indata))
        except queue.Full:
            pass

    def _discard_audio(self):
        while True:
            try:
                self.audio.get_nowait()
            except queue.Empty:
                return

    def _drain_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "wake":
                    self._set_status("command", "Yes? I’m listening for your command.")
                    self._speak("Yes?")
                elif kind == "command":
                    self.handle_command(value)
                elif kind == "heard" and self.listening:
                    self._set_status("listening", f"Listening locally · I hear: {value}")
                elif kind == "ready" and self.listening:
                    self._set_status("listening", "Listening locally. Say “Jarvis” followed by a command.")
                elif kind == "tts_error" and self.listening:
                    self._set_status("listening", "Voice output unavailable. Check your Windows speech voices.")
                elif kind == "error":
                    self.listening = False
                    self.listen_button.config(text="Enable voice activation", bg="#12303b", fg=CYAN)
                    self._set_status("idle", f"Voice recognition stopped: {value}")
                    messagebox.showerror("Microphone error", f"Could not listen to the microphone.\n\n{value}\n\nCheck that a microphone is connected and available.")
                elif kind == "audio_status":
                    self._set_status("listening", f"Microphone: {value}")
        except queue.Empty:
            pass
        if self.root.winfo_exists():
            self.root.after(100, self._drain_events)

    def _speak(self, text: str):
        if not self.listening:
            return
        self.speaking_event.set()
        self._set_status("speaking", "Speaking…")

        def worker():
            failed = False
            try:
                import pyttsx3
                engine = pyttsx3.init("sapi5" if os.name == "nt" else None)
                voices = engine.getProperty("voices")
                preferred = next((voice for voice in voices if re.search(r"david|mark|guy|male", voice.name, re.I)), None)
                if preferred:
                    engine.setProperty("voice", preferred.id)
                engine.setProperty("rate", 168)
                engine.setProperty("volume", 0.95)
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:
                failed = True
                self.events.put(("tts_error", str(exc)))
            finally:
                self._discard_audio()
                self.speaking_event.clear()
                if not failed:
                    self.events.put(("ready", None))

        threading.Thread(target=worker, daemon=True).start()

    def handle_command(self, command: str):
        command = command.strip()
        if not command:
            return
        self._add_message("You", command, "user")
        reply = self._run_command(command)
        self._add_message("JARVIS", reply, "assistant")
        if self.listening:
            self._speak(reply)

    def _run_command(self, command: str) -> str:
        normalized = re.sub(r"\s+", " ", command.lower()).strip(" .!?'")
        if re.search(r"\b(time|clock)\b", normalized) and not normalized.startswith(("open ", "search ", "new tab")):
            return f"It’s {datetime.now().astimezone().strftime('%I:%M %p').lstrip('0')} local time."
        if re.search(r"\b(date|today|what day)\b", normalized) and not normalized.startswith("open "):
            return f"Today is {datetime.now().strftime('%A, %B')} {datetime.now().day}."
        if normalized in {"help", "what can you do", "what can you open"}:
            return "I can open Calculator, Notepad, Paint, File Explorer, Task Manager, Settings, Chrome, Edge, or Firefox. I can also open a website or search the web in a new browser tab."
        if normalized.startswith(("search for ", "search the web for ", "google ")):
            query = re.sub(r"^(search the web for|search for|google)\s+", "", command, flags=re.I).strip()
            if not query:
                return "What would you like me to search for?"
            webbrowser.open_new_tab("https://www.google.com/search?q=" + quote_plus(query))
            return f"Searching the web for {query}. I opened a new browser tab."
        target = re.sub(r"^(please\s+)?(open|launch|start|new tab)\s+", "", command, flags=re.I).strip()
        target = re.sub(r"^(?:a\s+)?(?:new\s+)?(?:browser\s+)?tab(?:\s+(?:to|for))?\s+", "", target, flags=re.I)
        target = re.sub(r"^(?:to|for)\s+", "", target, flags=re.I)
        if target and target != command:
            return self._open_target(target)
        if normalized.startswith("go to "):
            return self._open_target(command[6:].strip())
        if normalized in {"stop listening", "turn off voice", "disable voice"}:
            self.root.after(0, self.toggle_voice)
            return "Voice activation is turning off."
        return "Try “open Calculator,” “open Chrome,” “open youtube.com,” or “search for something.” Say “Jarvis, help” for a list of commands."

    def _open_target(self, target: str) -> str:
        key = re.sub(r"\s+", " ", target.lower()).strip(" .!?'")
        target = re.sub(r"\s+dot\s+", ".", target, flags=re.I)
        target = re.sub(r"\s+(?:slash|forward slash)\s+", "/", target, flags=re.I)
        target = re.sub(r"\s+(?:dash|hyphen)\s+", "-", target, flags=re.I)
        key = re.sub(r"\s+", " ", target.lower()).strip(" .!?'")
        app_commands = {
            "calculator": ["calc.exe"], "calc": ["calc.exe"],
            "notepad": ["notepad.exe"], "notes": ["notepad.exe"], "text editor": ["notepad.exe"],
            "paint": ["mspaint.exe"], "microsoft paint": ["mspaint.exe"],
            "file explorer": ["explorer.exe"], "explorer": ["explorer.exe"], "files": ["explorer.exe"],
            "task manager": ["taskmgr.exe"], "settings": ["cmd", "/c", "start", "", "ms-settings:"],
        }
        if key in app_commands:
            try:
                subprocess.Popen(app_commands[key], shell=False)
                return f"Opening {target}."
            except OSError as exc:
                return f"I couldn’t open {target}: {exc}"

        browser_names = {"chrome", "google chrome", "edge", "microsoft edge", "firefox", "browser", "web browser"}
        if key in browser_names:
            candidates = {
                "chrome": ["chrome", "chrome.exe"], "google chrome": ["chrome", "chrome.exe"],
                "edge": ["msedge", "msedge.exe"], "microsoft edge": ["msedge", "msedge.exe"],
                "firefox": ["firefox", "firefox.exe"],
            }
            installed = next((shutil.which(name) for name in candidates.get(key, []) if shutil.which(name)), None)
            if not installed and os.name == "nt":
                browser_files = {
                    "chrome": [("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"), ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe"), ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe")],
                    "google chrome": [("PROGRAMFILES", "Google/Chrome/Application/chrome.exe"), ("PROGRAMFILES(X86)", "Google/Chrome/Application/chrome.exe"), ("LOCALAPPDATA", "Google/Chrome/Application/chrome.exe")],
                    "edge": [("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"), ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe")],
                    "microsoft edge": [("PROGRAMFILES(X86)", "Microsoft/Edge/Application/msedge.exe"), ("PROGRAMFILES", "Microsoft/Edge/Application/msedge.exe")],
                    "firefox": [("PROGRAMFILES", "Mozilla Firefox/firefox.exe"), ("PROGRAMFILES(X86)", "Mozilla Firefox/firefox.exe")],
                }
                installed = next((str(Path(os.environ.get(env, "")) / relative) for env, relative in browser_files.get(key, [])
                                  if os.environ.get(env) and (Path(os.environ[env]) / relative).exists()), None)
            if installed:
                subprocess.Popen([installed], shell=False)
            else:
                webbrowser.open_new_tab("https://www.google.com")
            return f"Opening {target}."

        sites = {"youtube": "https://www.youtube.com", "google": "https://www.google.com",
                 "github": "https://github.com", "chatgpt": "https://chatgpt.com", "wikipedia": "https://www.wikipedia.org"}
        url = sites.get(key)
        if not url:
            if re.match(r"^[\w-]+\.[a-z]{2,}([/:?#].*)?$", key):
                url = "https://" + key
            elif key.startswith(("https://", "http://")):
                url = key
            else:
                url = "https://www.google.com/search?q=" + quote_plus(target)
        webbrowser.open_new_tab(url)
        return f"Opening {target} in a new browser tab."

    def _clear_placeholder(self, _event):
        if self.entry.get() == "Type a command…":
            self.entry.delete(0, "end")

    def _submit_entry(self, _event=None):
        value = self.entry.get().strip()
        if value and value != "Type a command…":
            self.entry.delete(0, "end")
            self.handle_command(value)

    def clear_chat(self):
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")

    def close(self):
        self.stop_event.set()
        self.speaking_event.clear()
        self.root.destroy()


def main():
    root = tk.Tk()
    JarvisApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
