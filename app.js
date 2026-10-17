const form = document.querySelector('#chatForm');
const input = document.querySelector('#prompt');
const messages = document.querySelector('#messages');
const welcome = document.querySelector('#welcome');
const sendBtn = document.querySelector('#sendBtn');
const micBtn = document.querySelector('#micBtn');
const toast = document.querySelector('#toast');

function updateClock() {
  const now = new Date();
  document.querySelector('#clock').innerHTML = `${new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', hour12: false }).format(now)}<span>${new Intl.DateTimeFormat(undefined, { second: '2-digit' }).format(now)}</span>`;
  document.querySelector('#date').textContent = new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(now);
  document.querySelector('#timezone').textContent = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Local timezone';
}
updateClock(); setInterval(updateClock, 1000);

function notify(text) { toast.textContent = text; toast.classList.add('show'); clearTimeout(notify.timer); notify.timer = setTimeout(() => toast.classList.remove('show'), 2800); }
function addMessage(text, role) {
  const row = document.createElement('div'); row.className = `message ${role}`;
  const avatar = document.createElement('div'); avatar.className = 'message-avatar'; avatar.textContent = role === 'user' ? 'Y' : 'J';
  const body = document.createElement('div'); body.className = 'message-body'; body.textContent = text;
  row.append(avatar, body); messages.append(row); document.querySelector('#conversation').scrollTop = document.querySelector('#conversation').scrollHeight;
  return body;
}
function localAnswer(prompt) {
  const text = prompt.toLowerCase();
  if (/time|clock/.test(text)) return `It's ${new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date())} in your local time zone.`;
  if (/date|day|today/.test(text)) return `Today is ${new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' }).format(new Date())}.`;
  if (/capabilit|what can you|help/.test(text)) return 'I can tell you the local time and date, take voice input, and speak my replies. Connect an AI provider to add general conversation, research, and your own tools. The setup guide is in the project README.';
  if (/brief|morning|start.*day/.test(text)) return `Here’s your quick briefing: it’s ${new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(new Date())} on ${new Intl.DateTimeFormat(undefined, { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date())}. I’m ready when you are. Connect an AI provider for news, calendar, and task summaries.`;
  if (/interesting|surprise/.test(text)) return 'A day on Venus is longer than its year: Venus takes about 243 Earth days to rotate once, and about 225 Earth days to orbit the Sun.';
  return 'I’m running in local demo mode, so I can’t answer open-ended questions yet. Connect an AI provider to enable full conversations. For now, try asking for the time, date, a quick briefing, or my capabilities.';
}
function speak(text) { if (!('speechSynthesis' in window)) return; window.speechSynthesis.cancel(); const utterance = new SpeechSynthesisUtterance(text); utterance.rate = 1; window.speechSynthesis.speak(utterance); }
function submitPrompt(value) {
  const prompt = (value || '').trim(); if (!prompt) return;
  welcome.hidden = true; addMessage(prompt, 'user'); input.value = ''; input.style.height = 'auto'; sendBtn.disabled = true;
  const reply = localAnswer(prompt); const bubble = addMessage('', 'assistant');
  let i = 0; const timer = setInterval(() => { bubble.textContent = reply.slice(0, i += 3); if (i >= reply.length) { clearInterval(timer); sendBtn.disabled = false; input.focus(); } }, 13);
}
form.addEventListener('submit', e => { e.preventDefault(); submitPrompt(input.value); });
input.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
input.addEventListener('input', () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 110)}px`; });
document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => { input.value = button.dataset.prompt; submitPrompt(input.value); }));
document.querySelector('#clearBtn').addEventListener('click', () => { messages.replaceChildren(); welcome.hidden = false; input.focus(); });
document.querySelector('#setupBtn').addEventListener('click', () => notify('Follow the setup guide in README.md to connect an AI provider.'));

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  const recognition = new SpeechRecognition(); recognition.lang = navigator.language || 'en-US'; recognition.interimResults = false;
  micBtn.addEventListener('click', () => { try { recognition.start(); micBtn.classList.add('listening'); } catch { notify('Voice input is already listening.'); } });
  recognition.onresult = event => { input.value = event.results[0][0].transcript; submitPrompt(input.value); };
  recognition.onerror = () => notify('Voice input was unavailable. Check microphone permission and try again.');
  recognition.onend = () => micBtn.classList.remove('listening');
} else { micBtn.addEventListener('click', () => notify('Voice input works in browsers that support speech recognition, such as Chrome.')); }

