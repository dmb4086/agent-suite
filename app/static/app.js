const app = document.getElementById('app');
const apiKeyStore = 'agent-suite-api-key';
let selectedMessage = null;
function apiKey(){ return localStorage.getItem(apiKeyStore) || ''; }
function setApiKey(value){ localStorage.setItem(apiKeyStore, value.trim()); }
function authHeaders(){ return { 'Authorization': `Bearer ${apiKey()}`, 'Content-Type': 'application/json' }; }
function escapeHtml(value=''){ return value.replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function showError(message){ return `<div class="card error">${escapeHtml(message)}</div>`; }
function keyBar(){ return `<div class="toolbar card"><label>API key<input id="api-key" placeholder="Bearer API key" value="${escapeHtml(apiKey())}" /></label><button id="save-key">Save key</button><button id="refresh">Refresh</button></div>`; }
async function fetchMessages(){
  const res = await fetch('/v1/inboxes/me/messages', { headers: authHeaders() });
  if(!res.ok) throw new Error(await res.text() || `Failed to load messages (${res.status})`);
  return res.json();
}
function messageButton(msg, i){
  const date = msg.received_at ? new Date(msg.received_at).toLocaleString() : '';
  return `<button class="message ${selectedMessage?.id === msg.id ? 'active' : ''}" data-index="${i}"><strong>${escapeHtml(msg.subject || '(no subject)')}</strong><div class="meta">${escapeHtml(msg.sender || 'unknown sender')}</div><div class="meta">${escapeHtml(date)}</div></button>`;
}
function detail(msg){
  if(!msg) return `<section class="card detail"><p>Select a message to read it.</p></section>`;
  const body = msg.body_text || msg.body_html || '';
  return `<section class="card detail"><div class="meta">From ${escapeHtml(msg.sender || '')} to ${escapeHtml(msg.recipient || '')}</div><h2>${escapeHtml(msg.subject || '(no subject)')}</h2><div class="body">${escapeHtml(body)}</div></section>`;
}
async function renderInbox(){
  app.innerHTML = keyBar() + `<div class="grid"><section class="card"><p>Loading messages...</p></section>${detail(null)}</div>`;
  wireKeyBar(renderInbox);
  try{
    const data = await fetchMessages();
    const messages = data.messages || [];
    if(!selectedMessage && messages.length) selectedMessage = messages[0];
    app.querySelector('.grid').innerHTML = `<section class="card"><h2>Inbox</h2><div class="message-list">${messages.map(messageButton).join('') || '<p>No messages yet.</p>'}</div></section>${detail(selectedMessage)}`;
    app.querySelectorAll('.message').forEach(btn => btn.addEventListener('click', () => { selectedMessage = messages[Number(btn.dataset.index)]; renderInbox(); }));
  } catch(err){ app.innerHTML = keyBar() + showError(err.message); wireKeyBar(renderInbox); }
}
function renderCompose(status=''){
  app.innerHTML = keyBar() + `<section class="card"><h2>Compose</h2>${status}<form id="compose-form"><label>To<input name="to" type="email" required /></label><label>Subject<input name="subject" required /></label><label>Body<textarea name="body" required></textarea></label><div class="actions"><button type="submit">Send email</button><a class="button" href="/inbox">Back to inbox</a></div></form></section>`;
  wireKeyBar(() => renderCompose());
  document.getElementById('compose-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    try{
      const res = await fetch('/v1/inboxes/me/send', { method:'POST', headers: authHeaders(), body: JSON.stringify(Object.fromEntries(form)) });
      if(!res.ok) throw new Error(await res.text() || `Failed to send (${res.status})`);
      renderCompose('<p class="success">Message sent.</p>');
    } catch(err){ renderCompose(showError(err.message)); }
  });
}
function wireKeyBar(afterSave){
  document.getElementById('save-key')?.addEventListener('click', () => { setApiKey(document.getElementById('api-key').value); afterSave(); });
  document.getElementById('refresh')?.addEventListener('click', afterSave);
}
function route(){ selectedMessage = null; location.pathname.startsWith('/compose') ? renderCompose() : renderInbox(); }
route();
