// chat.js - Complete working version

const chat = document.getElementById('chat');
const msgForm = document.getElementById('msgForm');
const msgInput = document.getElementById('msgInput');
const sendBtn = document.getElementById('sendBtn');

let isLoadingMessages = false;
let oldestTimestamp = null;

// Format timestamp
function formatTime(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
}

// Create message element
function createMessageElement(msg) {
  const div = document.createElement('div');
  // Changed from 'message' to 'message-row' to match CSS alignment
  div.className = `message-row ${msg.role}`; 
  
  const bubble = document.createElement('div');
  // Added bubble-user/bot for coloring
  bubble.className = `bubble bubble-${msg.role}`; 
  bubble.textContent = msg.text;
  
  const time = document.createElement('div');
  time.className = 'time';
  time.textContent = formatTime(msg.timestamp);
  
  // Removed: bubble.appendChild(time); 
  
  div.appendChild(bubble);
  
  return div;
}

// Add message to chat
function addMessage(msg, prepend = false) {
  const msgEl = createMessageElement(msg);
  
  if (prepend) {
    chat.insertBefore(msgEl, chat.firstChild);
  } else {
    chat.appendChild(msgEl);
    // Scroll to bottom for new messages
    setTimeout(() => {
      chat.scrollTop = chat.scrollHeight;
    }, 10);
  }
}

// Load messages from API
async function loadMessages(before = null) {
  if (isLoadingMessages) return;
  isLoadingMessages = true;
  
  try {
    const url = before ? `/api/messages?before=${before}` : '/api/messages';
    const resp = await fetch(url);
    
    if (!resp.ok) {
      console.error('Failed to load messages:', resp.status);
      return;
    }
    
    const data = await resp.json();
    
    if (data.messages && data.messages.length > 0) {
      // Store oldest timestamp for pagination
      oldestTimestamp = data.oldest;
      
      // Add messages to chat
      data.messages.forEach(msg => {
        addMessage(msg, before !== null);
      });
      
      // Scroll to bottom on initial load
      if (!before) {
        setTimeout(() => {
          chat.scrollTop = chat.scrollHeight;
        }, 50);
      }
    }
  } catch (err) {
    console.error('Error loading messages:', err);
  } finally {
    isLoadingMessages = false;
  }
}

// Send message
async function sendMessage(text) {
  if (!text.trim()) return;
  
  // Disable input while sending
  msgInput.disabled = true;
  sendBtn.disabled = true;
  
  try {
    // Add user message immediately to UI
    const userMsg = {
      role: 'user',
      text: text,
      timestamp: new Date().toISOString()
    };
    addMessage(userMsg);
    
    // Send to API
    const resp = await fetch('/api/message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    
    if (!resp.ok) {
      throw new Error('Failed to send message');
    }
    
    const data = await resp.json();
    
    // Add bot response if returned
    if (data.message) {
      addMessage(data.message);
    }
    
    // NOTE: Input clearing logic moved to finally block below.
    
  } catch (err) {
    console.error('Error sending message:', err);
    alert('Failed to send message. Please try again.');
  } finally {
    // === CHANGE IS HERE: Clear input regardless of success/failure ===
    msgInput.value = '';
    
    msgInput.disabled = false;
    sendBtn.disabled = false;
    msgInput.focus();
  }
}

// Form submit handler
msgForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = msgInput.value.trim();
  if (text) {
    sendMessage(text);
  }
});

// Send button click handler
sendBtn.addEventListener('click', (e) => {
  e.preventDefault();
  const text = msgInput.value.trim();
  if (text) {
    sendMessage(text);
  }
});

// Enter key to send
msgInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const text = msgInput.value.trim();
    if (text) {
      sendMessage(text);
    }
  }
});

// Poll for notifications
async function checkNotifications() {
  try {
    const resp = await fetch('/api/get-notifications');
    if (resp.ok) {
      const data = await resp.json();
      if (data.notifications && data.notifications.length > 0) {
        data.notifications.forEach(notif => {
          const msg = {
            role: 'bot',
            text: notif,
            timestamp: new Date().toISOString()
          };
          addMessage(msg);
        });
      }
    }
  } catch (err) {
    console.error('Error checking notifications:', err);
  }
}

// Check notifications every 3 seconds
setInterval(checkNotifications, 3000);

// Load initial messages on page load
loadMessages();

// Focus input on load
msgInput.focus();