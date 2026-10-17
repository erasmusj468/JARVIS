# JARVIS — Personal Assistant

A responsive, voice-ready assistant interface with a live clock, quick commands, speech input, and spoken replies. It runs as a static site and needs no build step.

## Run it

Open `index.html` in a modern browser, or serve this folder with any static file server. Microphone access requires a secure context (`https://` or `localhost`) and browser support for the Web Speech API. Voice playback uses the browser's speech synthesis.

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
- `app.js` — chat demo, clock, speech input, and speech output
