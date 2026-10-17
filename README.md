# JARVIS Desktop Assistant

JARVIS is a small Windows desktop app written in Python. It listens for the wake word on your microphone using offline speech recognition, speaks replies, opens selected desktop apps, and opens websites or web searches in new browser tabs.

## Set it up on Windows

Install Python 3.10 or 3.11 from python.org if it is not already installed. During setup, enable **Add Python to PATH** and include **tcl/tk and IDLE** so the desktop window can run.

Open a terminal in this project folder and run this one-time setup:

```powershell
py -m pip install -r requirements.txt
py setup_voice.py
py run.py
```

The voice model download is about 40 MB. Once setup is complete, double-click `Start JARVIS.bat` any time to open the app. Recognition happens locally and does not use a browser speech service. Keep the app open, click **Enable voice activation**, and allow microphone access if Windows asks. Say “Jarvis” and then your command, for example “Jarvis, open calculator.” The small English model can make occasional transcription mistakes; the wake matcher accepts close and split spellings.

## Voice commands

- “Jarvis, open calculator/notepad/paint/file explorer/task manager/settings”
- “Jarvis, open Chrome/Edge/Firefox” or “Jarvis, open browser”
- “Jarvis, open youtube.com” or “Jarvis, open a new browser tab to github.com”
- “Jarvis, search the web for [something]”
- “Jarvis, what time is it?” or “Jarvis, help”

The app only starts a fixed set of local applications. Website and search requests open in your default browser. Typing commands in the app works even when voice activation is off.

## Project files

- `jarvis.py` — native Tkinter interface, local microphone listener, speech output, and command handling
- `run.py` — desktop app launcher
- `setup_voice.py` — downloads and unpacks the English speech model
- `requirements.txt` — Python packages for offline speech recognition and voice output

The voice model is stored under `models/` and excluded from Git. The official compact Vosk English model is approximately 40 MB and licensed Apache 2.0. [Vosk model list](https://alphacephei.com/vosk/models). The microphone capture follows Vosk's Python `sounddevice` example: [Vosk microphone example](https://github.com/alphacep/vosk-api/blob/master/python/example/test_microphone.py).
