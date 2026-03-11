// Agent Suite - Web UI JavaScript

const API_BASE = window.location.origin;

// State
let apiKey = localStorage.getItem('agent_suite_api_key') || '';
let messages = [];

// DOM Elements
const messageListEl = document.getElementById('messageList');
const messageDetailEl = document.getElementById('messageDetail');
const apiKeyModal = document.getElementById('apiKeyModal');
const composeModal = document.getElementById('composeModal');
const emailAddressEl = document.getElementById('emailAddress');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (!apiKey) {
        showApiKeyModal();
    } else {
        loadMessages();
        loadInboxInfo();
    }
    setupEventListeners();
});

function setupEventListeners() {
    // API Key Modal
    document.getElementById('saveApiKey').addEventListener('click', saveApiKey);
    document.getElementById('cancelApiKey').addEventListener('click', () => {
        if (!apiKey) {
            showError('API key is required');
        }
        hideModal(apiKeyModal);
    });

    // Settings Button
    document.getElementById('settingsBtn').addEventListener('click', () => {
        document.getElementById('apiKeyInput').value = apiKey;
        showModal(apiKeyModal);
    });

    // Compose Button
    document.getElementById('composeBtn').addEventListener('click', () => {
        showModal(composeModal);
    });

    // Compose Form
    document.getElementById('composeForm').addEventListener('submit', sendEmail);
    document.getElementById('cancelCompose').addEventListener('click', () => {
        hideModal(composeModal);
    });

    // Back Button
    document.getElementById('backBtn').addEventListener('click', () => {
        messageDetailEl.classList.add('hidden');
        messageListEl.classList.remove('hidden');
    });
}

function getHeaders() {
    return {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
    };
}

async function loadInboxInfo() {
    try {
        const response = await fetch(`${API_BASE}/v1/inboxes/me`, {
            headers: getHeaders()
        });
        
        if (response.status === 401) {
            showApiKeyModal();
            return;
        }
        
        const data = await response.json();
        emailAddressEl.textContent = data.email_address;
    } catch (error) {
        console.error('Failed to load inbox info:', error);
    }
}

async function loadMessages() {
    messageListEl.innerHTML = '<div class="loading">Loading messages...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/v1/inboxes/me/messages`, {
            headers: getHeaders()
        });
        
        if (response.status === 401) {
            showApiKeyModal();
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        messages = data.messages;
        renderMessages(messages);
    } catch (error) {
        showError(`Failed to load messages: ${error.message}`);
    }
}

function renderMessages(messageList) {
    if (!messageList || messageList.length === 0) {
        messageListEl.innerHTML = `
            <div class="empty-state">
                <h3>📭 No messages yet</h3>
                <p>Your inbox is empty. Send a message to get started!</p>
            </div>
        `;
        return;
    }
    
    messageListEl.innerHTML = messageList.map(msg => `
        <div class="message-item ${msg.is_read ? '' : 'unread'}" data-id="${msg.id}">
            <div class="subject">${escapeHtml(msg.subject || '(No Subject)')}</div>
            <div class="preview">${escapeHtml(msg.body_text || '').substring(0, 100)}</div>
            <div class="meta">
                <span>${escapeHtml(msg.sender)}</span>
                <span>${formatDate(msg.received_at)}</span>
            </div>
        </div>
    `).join('');
    
    // Add click handlers
    document.querySelectorAll('.message-item').forEach(item => {
        item.addEventListener('click', () => {
            const msgId = item.dataset.id;
            showMessageDetail(msgId);
        });
    });
}

async function showMessageDetail(msgId) {
    const msg = messages.find(m => m.id === msgId);
    if (!msg) return;
    
    // Mark as read
    if (!msg.is_read) {
        msg.is_read = true;
        // Optionally call API to mark as read
    }
    
    document.getElementById('detailSubject').textContent = msg.subject || '(No Subject)';
    document.getElementById('detailFrom').textContent = msg.sender;
    document.getElementById('detailTo').textContent = msg.recipient;
    document.getElementById('detailDate').textContent = formatDate(msg.received_at);
    document.getElementById('detailBody').textContent = msg.body_text || '(No content)';
    
    messageListEl.classList.add('hidden');
    messageDetailEl.classList.remove('hidden');
}

async function sendEmail(e) {
    e.preventDefault();
    
    const to = document.getElementById('toInput').value;
    const subject = document.getElementById('subjectInput').value;
    const body = document.getElementById('bodyInput').value;
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';
    
    try {
        const response = await fetch(`${API_BASE}/v1/inboxes/me/send`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify({ to, subject, body })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to send');
        }
        
        const result = await response.json();
        
        // Show success and close modal
        hideModal(composeModal);
        e.target.reset();
        
        // Show success message
        const successEl = document.createElement('div');
        successEl.className = 'success';
        successEl.textContent = `✓ Message sent! Message ID: ${result.message_id}`;
        messageListEl.insertBefore(successEl, messageListEl.firstChild);
        
        // Refresh messages
        loadMessages();
        
    } catch (error) {
        showError(`Failed to send: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send';
    }
}

function saveApiKey() {
    const input = document.getElementById('apiKeyInput').value.trim();
    if (!input) {
        showError('Please enter a valid API key');
        return;
    }
    
    apiKey = input;
    localStorage.setItem('agent_suite_api_key', apiKey);
    hideModal(apiKeyModal);
    loadMessages();
    loadInboxInfo();
}

function showApiKeyModal() {
    document.getElementById('apiKeyInput').value = apiKey;
    showModal(apiKeyModal);
}

function showModal(modal) {
    modal.classList.remove('hidden');
}

function hideModal(modal) {
    modal.classList.add('hidden');
}

function showError(message) {
    const errorEl = document.createElement('div');
    errorEl.className = 'error';
    errorEl.textContent = message;
    messageListEl.insertBefore(errorEl, messageListEl.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => errorEl.remove(), 5000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    // Less than 24 hours
    if (diff < 86400000) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // Less than 7 days
    if (diff < 604800000) {
        const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        return days[date.getDay()] + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    
    // Older
    return date.toLocaleDateString();
}
