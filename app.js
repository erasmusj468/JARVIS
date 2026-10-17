const form = document.querySelector('#chatForm');
const input = document.querySelector('#prompt');
const messages = document.querySelector('#messages');
const welcome = document.querySelector('#welcome');
const sendBtn = document.querySelector('#sendBtn');
const micBtn = document.querySelector('#micBtn');
const wakeButton = document.querySelector('#wakeButton');
const wakeLabel = document.querySelector('#wakeLabel');
const voiceStatus = document.querySelector('#voiceStatus');
const voiceNote = document.querySelector('#voiceNote');
const toast = document.querySelector('#toast');
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let voiceEnabled = false;
let recognizing = false;
let mode = 'wake'; // wake word, command, or idle
let restartTimer;

function updateClock() {
  const now = new Date();
  document.querySelector('#clock').innerHTML = `${new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', hour12: false }).format(now)}<span>${new Intl.DateTimeFormat(undefined, { second: '2-digit' }).format(now)}</span>`;
  document.querySelector('#date').textContent = new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(now);
  document.querySelector('#timezone').textContent = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Local timezone';
}
updateClock(); setInterval(updateClock, 1000);

function notify(text) { toast.textContent = text; toast.classList.add('show'); clearTimeout(notify.timer); notify.timer = setTimeout(() => toast.classList.remove('show'), 2800); }
function setVoiceState(state) {
  document.body.dataset.voiceState = state;
  if (state === 'listening') { voiceStatus.textContent = 'I’m listening. Say “Jarvis” to get my attention.'; wakeLabel.textContent = 'Listening for “Jarvis”'; }
  else if (state === 'command') { voiceStatus.textContent = 'Yes? I’m listening.'; wakeLabel.textContent = 'Listening to your request'; }
  else if (state === 'speaking') { voiceStatus.textContent = 'Speaking…'; wakeLabel.textContent = 'JARVIS is speaking'; }
  else if (state === 'unsupported') { voiceStatus.textContent = 'Voice activation needs a browser with speech recognition.'; wakeLabel.textContent = 'Voice activation unavailable'; }
  else { voiceStatus.textContent = 'Say “Jarvis” whenever you need me.'; wakeLabel.textContent = 'Enable voice activation'; }
  wakeButton.classList.toggle('enabled', voiceEnabled);
}
function addMessage(text, role) {
  const row = document.createElement('div'); row.className = `message ${role}`;
  const avatar = document.createElement('div'); avatar.className = 'message-avatar'; avatar.textContent = role === 'user' ? 'Y' : 'J';
  const body = document.createElement('div'); body.className = 'message-body'; body.textContent = text;
  row.append(avatar, body); messages.append(row); document.querySelector('#conversation').scrollTop = document.querySelector('#conversation').scrollHeight;
  return body;
}
function localAnswer(prompt) {
  const text = prompt.toLowerCase();
  if (/time|clock/.test(text)) return `It’s ${new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date())} in your local time zone.`;
  if (/date|day|today/.test(text)) return `Today is ${new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(new Date())}.`;
  if (/capabilit|what can you|help/.test(text)) return 'I can tell you the local time and date, listen for your voice, and speak my replies. Connect an AI provider to add general conversation, research, and your own tools.';
  if (/brief|morning|start.*day/.test(text)) return `Here’s your quick briefing: it’s ${new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date())} on ${new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date())}. I’m ready when you are. Connect an AI provider for news, calendar, and task summaries.`;
  if (/interesting|surprise/.test(text)) return 'A day on Venus is longer than its year. Venus takes about 243 Earth days to rotate once, and about 225 Earth days to orbit the Sun.';
  return 'I’m in local demo mode, so I can’t answer that one yet. Connect an AI provider for open conversations. For now, ask me for the time, date, a quick briefing, or what I can do.';
}
function startRecognition() {
  if (!voiceEnabled || !recognition || recognizing || speechSynthesis.speaking) return;
  clearTimeout(restartTimer);
  try { recognition.start(); } catch { /* The browser may still be finishing a previous session. */ }
}
function speak(text) {
  if (!('speechSynthesis' in window)) return;
  if (recognizing && recognition) { try { recognition.stop(); } catch { /* already stopping */ } }
  window.speechSynthesis.cancel();
  if (voiceEnabled) { mode = 'wake'; setVoiceState('speaking'); }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.96; utterance.pitch = 0.88;
  const voices = window.speechSynthesis.getVoices();
  const preferred = voices.find(v => /en/i.test(v.lang) && /natural|neural|enhanced/i.test(v.name)) || voices.find(v => /en/i.test(v.lang));
  if (preferred) utterance.voice = preferred;
  utterance.onend = () => { if (voiceEnabled) { setVoiceState('listening'); restartTimer = setTimeout(startRecognition, 450); } };
  utterance.onerror = utterance.onend;
  window.speechSynthesis.speak(utterance);
}
async function answerPrompt(prompt) {
  const text = (prompt || '').trim(); if (!text) return;
  welcome.hidden = true; addMessage(text, 'user'); input.value = ''; input.style.height = 'auto'; sendBtn.disabled = true;
  const bubble = addMessage('', 'assistant');
  let reply;
  try {
    const response = await fetch('/api/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: text }) });
    if (!response.ok) throw new Error('Python server unavailable');
    ({ reply } = await response.json());
  } catch { reply = localAnswer(text); }
  let i = 0; const timer = setInterval(() => {
    bubble.textContent = reply.slice(0, i += 3);
    if (i >= reply.length) { clearInterval(timer); sendBtn.disabled = false; if (voiceEnabled) speak(reply); }
  }, 9);
}
function activateVoice() {
  if (!SpeechRecognition) { setVoiceState('unsupported'); voiceNote.textContent = 'Use Chrome or Edge on localhost/HTTPS for hands-free voice activation.'; return; }
  if (voiceEnabled) {
    voiceEnabled = false; mode = 'wake'; clearTimeout(restartTimer);
    try { recognition.stop(); } catch { /* no active session */ }
    window.speechSynthesis.cancel(); setVoiceState('idle'); voiceNote.textContent = 'Microphone is off.'; return;
  }
  recognition = new SpeechRecognition();
  recognition.lang = navigator.language || 'en-US'; recognition.continuous = true; recognition.interimResults = true; recognition.maxAlternatives = 4;
  recognition.onstart = () => { recognizing = true; setVoiceState(mode === 'command' ? 'command' : 'listening'); };
  recognition.onend = () => { recognizing = false; if (voiceEnabled && !window.speechSynthesis.speaking) restartTimer = setTimeout(startRecognition, 350); };
  recognition.onerror = event => {
    recognizing = false;
    if (event.error === 'not-allowed' || event.error === 'service-not-allowed' || event.error === 'audio-capture' || event.error === 'network') {
      voiceEnabled = false; setVoiceState('idle'); voiceNote.textContent = 'Microphone permission was blocked. Allow microphone access in your browser, then try again.';
      if (event.error === 'network') voiceNote.textContent = 'The browser speech service is unavailable. Check your internet connection or try Chrome/Edge.';
      if (event.error === 'audio-capture') voiceNote.textContent = 'No microphone was found. Connect or enable a microphone, then try again.';
    } else if (event.error !== 'no-speech' && event.error !== 'aborted') notify(`Voice recognition: ${event.error}.`);
  };
  recognition.onresult = event => {
    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const result = event.results[i];
      if (mode === 'wake') {
        // Check alternate speech hypotheses too: the service can hear "Jarvice" or "Jarvus".
        let match;
        for (let alternative = 0; alternative < result.length; alternative += 1) {
          const heard = result[alternative].transcript.trim();
          match = heard.match(/\bjarv(?:is|ice|us|iss|es|as)\b[,.!\s]*(.*)/i);
          if (match) break;
        }
        // Wait for the utterance to finish so "Jarvis, what's the time?" is not cut off.
        if (!match || !result.isFinal) continue;
        const rest = match[1].trim();
        if (rest) { mode = 'command'; answerPrompt(rest); }
        else { mode = 'command'; setVoiceState('command'); speak('Yes?'); }
        break;
      }
      if (mode === 'command' && result.isFinal) {
        const heard = result[0].transcript.trim();
        const command = heard.replace(/^\s*jarv(?:is|ice|us)[,.!\s]*/i, '').trim();
        if (command) answerPrompt(command);
        else { mode = 'wake'; setVoiceState('listening'); }
        break;
      }
    }
  };
  voiceEnabled = true; mode = 'wake'; voiceNote.textContent = 'Keep this tab open. Say “Jarvis” to wake me, then tell me what you need.';
  setVoiceState('listening'); startRecognition();
}

form.addEventListener('submit', e => { e.preventDefault(); answerPrompt(input.value); });
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 110)}px`; });
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => answerPrompt(button.dataset.prompt)));
document.querySelector('#clearBtn').addEventListener('click', () => { messages.replaceChildren(); welcome.hidden = false; input.focus(); });
document.querySelector('#setupBtn').addEventListener('click', () => notify('Follow the setup guide in README.md to connect an AI provider.'));
wakeButton.addEventListener('click', activateVoice);
micBtn.addEventListener('click', activateVoice);
setVoiceState(SpeechRecognition ? 'idle' : 'unsupported');
