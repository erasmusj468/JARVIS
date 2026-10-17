# JARVIS — Personal Assistant

A responsive, voice-first assistant interface with a live clock, wake-word activation, speech input, and spoken replies. It runs as a static site and needs no build step.

## Run it

Run `py run.py` from this folder. It starts the Python server at `http://127.0.0.1:8000` and opens the page. Click **Enable voice activation** once to grant microphone permission, then leave the tab open and say **“Jarvis”** followed by your request. You can also say just “Jarvis,” wait for the spoken “Yes?”, then give your request. Wake matching tolerates common recognition misspellings and split words. While it listens, the status line shows the words the browser recognized, which helps diagnose microphone or speech recognition issues. Click the button again to stop listening.

Hands-free wake-word listening requires browser support for the Web Speech API (commonly available in Chrome and Edge) and a secure context (`https://` or `localhost`). The browser requires a user gesture before it can request microphone access. Voice playback uses the browser's speech synthesis. The Python server handles local demo commands; type in the message field when voice recognition is unavailable. The browser may use its speech service for recognition, depending on browser settings.

## Current behavior

This starter runs in local demo mode. It handles time, date, a short briefing, and a capabilities prompt locally. Open-ended AI answers need a model provider and a small server-side API route; the browser should never contain a provider secret.

To connect an AI model:

1. Choose a provider and create a private API key.
2. Add a server endpoint such as `POST /api/chat` that reads the key from a server environment variable and forwards the conversation to the provider.
3. Replace `localAnswer()` in `app.js` with a `fetch('/api/chat', ...)` call, and render the returned text. Keep the API key on the server.
4. Update the assistant's loading and error states to match the endpoint response.

## Project files

- `index.html` — page structure
- `styles.css` — responsive dark interface
- `app.js` — chat interface, clock, wake-word listener, and spoken replies
- `voice.css` — microphone activation and voice state animations
- `run.py` — Python web server and local command endpoint
