// ===== TAB SWITCHING =====
const navBtns = document.querySelectorAll('.nav-btn');
const tabTitles = { qa: 'Policy Q&A', checklist: 'Compliance Checklist' };

navBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    navBtns.forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`tab-${tab}`).classList.add('active');
    document.getElementById('tabTitle').textContent = tabTitles[tab];
  });
});

// ===== TOAST =====
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  window.setTimeout(() => t.classList.remove('show'), 2500);
}

function escHtml(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function formatInline(text) {
  return escHtml(text).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}

function formatAnswer(text) {
  const lines = (text || '').split(/\r?\n/);
  let html = '';
  let inList = false;

  const closeList = () => {
    if (inList) { html += '</ul>'; inList = false; }
  };

  for (const rawLine of lines) {
    const line = (rawLine || '').replace(/\s+$/g, '');
    if (!line.trim()) {
      closeList();
      html += '<div class="spacer"></div>';
      continue;
    }

    const bulletMatch = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/);
    if (bulletMatch) {
      if (!inList) { html += '<ul class="answer-list">'; inList = true; }
      html += `<li>${formatInline(bulletMatch[1])}</li>`;
      continue;
    }

    closeList();
    html += `<div class="answer-line">${formatInline(line)}</div>`;
  }

  closeList();
  return html;
}

// ===== Q&A =====
const chatArea = document.getElementById('chatArea');
const qaInput = document.getElementById('qaInput');
const sendBtn = document.getElementById('sendBtn');

function fillQ(btn) {
  qaInput.value = btn.textContent;
  qaInput.focus();
}

function scrollChat() {
  chatArea.scrollTop = chatArea.scrollHeight;
}

function appendUserMsg(text) {
  const div = document.createElement('div');
  div.className = 'msg msg-user';
  div.innerHTML = `<div class="bubble">${escHtml(text)}</div>`;
  chatArea.appendChild(div);
  scrollChat();
}

function appendThinking() {
  const div = document.createElement('div');
  div.className = 'msg msg-ai thinking-wrap';
  div.innerHTML = `<div class="thinking"><div class="dots" aria-hidden="true"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div> Analyzing documents…</div>`;
  chatArea.appendChild(div);
  scrollChat();
  return div;
}

function appendAIMsg(answer, sources) {
  const div = document.createElement('div');
  div.className = 'msg msg-ai';
  const formatted = formatAnswer(answer);
  const sourcesHtml = sources && sources.length
    ? `<div class="sources-row">${sources.map(s => `<span class="source-tag">${escHtml(s)}</span>`).join('')}</div>`
    : '';
  div.innerHTML = `<div class="bubble">${formatted}</div>${sourcesHtml}`;
  chatArea.appendChild(div);
  scrollChat();
}

async function sendQuestion() {
  const q = qaInput.value.trim();
  if (!q) return;

  const welcome = chatArea.querySelector('.chat-welcome');
  if (welcome) welcome.remove();

  appendUserMsg(q);
  qaInput.value = '';
  sendBtn.disabled = true;

  const thinking = appendThinking();

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q })
    });
    const data = await res.json();
    thinking.remove();

    if (data.error) {
      appendAIMsg(`Error: ${data.error}`, []);
      showToast(data.error, 'error');
    } else {
      appendAIMsg(data.answer, data.sources);
    }
  } catch (e) {
    thinking.remove();
    appendAIMsg('Network error. Please try again.', []);
    showToast('Request failed', 'error');
  }

  sendBtn.disabled = false;
}

sendBtn.addEventListener('click', sendQuestion);
qaInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion(); }
});

// ===== CHECKLIST =====
document.getElementById('checklistBtn').addEventListener('click', async () => {
  const topic = document.getElementById('checklistTopic').value.trim();
  if (!topic) { showToast('Enter a topic first', 'error'); return; }

  const btn = document.getElementById('checklistBtn');
  const wrap = document.getElementById('checklistResult');
  btn.disabled = true;
  btn.textContent = 'Generating…';
  wrap.innerHTML = '';
  wrap.style.display = 'none';

  try {
    const res = await fetch('/checklist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic })
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, 'error'); }
    else {
      wrap.style.display = 'flex';
      data.checklist.forEach((item, i) => {
        const div = document.createElement('div');
        div.className = 'cl-item';
        div.style.animationDelay = `${i * 0.03}s`;
        div.innerHTML = `<div class="cl-check" onclick="toggleCheck(this)"></div><span>${escHtml(item)}</span>`;
        wrap.appendChild(div);
      });
    }
  } catch (e) {
    showToast('Request failed', 'error');
  }

  btn.disabled = false;
  btn.textContent = 'Generate';
});

function toggleCheck(el) {
  el.classList.toggle('checked');
}

// ===== REBUILD INDEX =====
document.getElementById('rebuildBtn').addEventListener('click', async () => {
  const btn = document.getElementById('rebuildBtn');
  btn.textContent = 'Indexing…';
  btn.disabled = true;
  try {
    const res = await fetch('/rebuild-index', { method: 'POST' });
    const data = await res.json();
    if (data.error) showToast(data.error, 'error');
    else showToast(data.message, 'success');
  } catch (e) {
    showToast('Failed to rebuild index', 'error');
  }
  btn.textContent = 'Reindex';
  btn.disabled = false;
});
