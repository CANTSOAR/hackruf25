(() => {
  const wrap   = document.getElementById('chat');
  const form   = document.getElementById('msgForm');
  const input  = document.getElementById('msgInput');
  const sendBtn= document.getElementById('sendBtn');
  const callBtn= document.getElementById('callBtn');
  const pullHint = document.getElementById('pullHint');
  if (!wrap) return;

  // ----- Voice Recording State -----
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  // ----- Chat logic -----
  let newestBatch = [];        
  let allMessages = [];        
  let oldest = null;           
  let loading = false;
  let reachedEnd = false;
  let loginAt = null;          
  let unlockedOlder = false;   
  let pullCount = 0;
  let pullCooldown = false;    

  function formatStamp(iso){
    const dt = new Date(iso);
    const optsDate = { weekday:'short', month:'short', day:'numeric' };
    const optsTime = { hour:'numeric', minute:'2-digit' };
    return `${dt.toLocaleDateString(undefined, optsDate)} • ${dt.toLocaleTimeString(undefined, optsTime)}`;
  }

  function buildRow(m){
    const isUser = m.role === 'user';
    const bubble = isUser ? 'bubble bubble-user' : 'bubble bubble-bot';
    const rowClass = isUser ? 'message-row user' : 'message-row bot';
    const userAvatar = `<div class="avatar">🧑</div>`;
    const botAvatar  = `<div class="avatar"><img src="/static/images/rutgers_logo.png" onerror="this.parentElement.textContent='🤖'"></div>`;
    return isUser
      ? `<div class="${rowClass}"><div class="${bubble}">${escapeHtml(m.text)}</div>${userAvatar}</div>`
      : `<div class="${rowClass}">${botAvatar}<div class="${bubble}">${escapeHtml(m.text)}</div></div>`;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderList(list){
    let html = '';
    const ONE_HOUR = 3600000;
    const loginDate = loginAt ? new Date(loginAt) : null;

    for(let i=0;i<list.length;i++){
      const cur = list[i];
      const curDate = new Date(cur.timestamp);
      let needStamp = (i === 0);

      if(!needStamp && i>0){
        const prevDate = new Date(list[i-1].timestamp);
        if (curDate - prevDate >= ONE_HOUR) needStamp = true;
      }
      if(!needStamp && loginDate){
        const prevDate = i>0 ? new Date(list[i-1].timestamp) : null;
        if((!prevDate || prevDate < loginDate) && curDate >= loginDate) needStamp = true;
      }

      if(needStamp) html += `<div class="timestamp">${formatStamp(cur.timestamp)}</div>`;
      html += buildRow(cur);
    }
    wrap.innerHTML = html;
  }

  function renderAll(){
    renderList(unlockedOlder ? allMessages : newestBatch);
    wrap.scrollTop = wrap.scrollHeight;
  }

  async function fetchBatch(before=null){
    if(loading || (before && reachedEnd)) return {count:0};
    loading = true;
    try{
      const url = before ? `/api/messages?before=${encodeURIComponent(before)}` : `/api/messages`;
      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (!loginAt) loginAt = data.login_at || null;

      let msgs = data.messages || [];

      if (!before && !unlockedOlder && loginAt) {
        const cutoff = new Date(loginAt).getTime();
        const BUFFER_MS = 24*3600*1000;
        msgs = msgs.filter(m => new Date(m.timestamp).getTime() >= cutoff - BUFFER_MS);
      }

      if (before) {
        if (msgs.length === 0) { reachedEnd = true; return {count:0}; }
        const prevHeight = wrap.scrollHeight;
        allMessages = [...msgs, ...(unlockedOlder ? allMessages : newestBatch)];
        renderAll();
        wrap.scrollTop = wrap.scrollHeight - prevHeight;
        oldest = allMessages.length ? allMessages[0].timestamp : oldest;
        return {count: msgs.length};
      } else {
        newestBatch = msgs;
        if (unlockedOlder) {
          allMessages = mergeChronologically(allMessages, newestBatch);
          oldest = allMessages.length ? allMessages[0].timestamp : null;
        } else {
          oldest = newestBatch.length ? newestBatch[0].timestamp : null;
        }
        renderAll();
        return {count: msgs.length};
      }
    } catch (err) {
      console.error('fetchBatch() failed:', err);
      return {count:0};
    } finally {
      loading = false;
    }
  }

  function mergeChronologically(a, b){
    const out = [];
    let i=0,j=0;
    while(i<a.length || j<b.length){
      const ai = a[i], bj = b[j];
      if(ai && (!bj || new Date(ai.timestamp) <= new Date(bj.timestamp))){
        if(!out.length || out[out.length-1].timestamp !== ai.timestamp || out[out.length-1].text !== ai.text || out[out.length-1].role !== ai.role){
          out.push(ai);
        }
        i++;
      }else if(bj){
        if(!out.length || out[out.length-1].timestamp !== bj.timestamp || out[out.length-1].text !== bj.text || out[out.length-1].role !== bj.role){
          out.push(bj);
        }
        j++;
      }else break;
    }
    return out;
  }

  async function send(){
    const text = (input.value || '').trim();
    if (!text) return;
    sendBtn.disabled = true;
    try{
      const res = await fetch('/api/message', {
        method: 'POST',
        headers: { 'Content-Type':'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ text })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      input.value = '';
      reachedEnd = false;
      await fetchBatch();
      wrap.scrollTop = wrap.scrollHeight;
    }catch(e){ 
      console.error(e);
      alert('Failed to send message. Please try again.');
    }
    finally{ sendBtn.disabled = false; input.focus(); }
  }

  form?.addEventListener('submit', (e)=>{ e.preventDefault(); send(); });
  sendBtn?.addEventListener('click', (e)=>{ e.preventDefault(); send(); });

  // ----- Voice Recording -----
  async function toggleRecording() {
    if (isRecording) {
      // Stop recording
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
          audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
          isRecording = false;
          callBtn.innerHTML = `<svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8">
            <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07A19.5 19.5 0 0 1 3.15 8.81 19.8 19.8 0 0 1 .08 0.18 2 2 0 0 1 2.06 0h3a2 2 0 0 1 2 1.72 12.05 12.05 0 0 0 .65 2.73 2 2 0 0 1-.45 2.11L6.1 8.9a16 16 0 0 0 9 9l2.34-1.16a2 2 0 0 1 2.11.45 12.05 12.05 0 0 0 2.73.65A2 2 0 0 1 22 16.92z"/>
          </svg>`;
          callBtn.title = 'Start Voice Recording';
          
          // Stop all tracks
          stream.getTracks().forEach(track => track.stop());
          
          // Send audio
          await sendAudio();
        };
        
        mediaRecorder.start();
        isRecording = true;
        
        // Update button to show recording state
        callBtn.innerHTML = `<svg viewBox="0 0 24 24" class="h-5 w-5" fill="currentColor">
          <rect x="6" y="4" width="4" height="16" rx="1"/>
          <rect x="14" y="4" width="4" height="16" rx="1"/>
        </svg>`;
        callBtn.title = 'Stop Recording';
        
      } catch (err) {
        console.error('Error accessing microphone:', err);
        alert('Could not access microphone. Please check permissions.');
      }
    }
  }

  async function sendAudio() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    
    // Add temporary "processing" message
    const tempMsg = {
      role: 'bot',
      text: '🎤 Processing your voice message...',
      timestamp: new Date().toISOString()
    };
    newestBatch.push(tempMsg);
    renderAll();
    
    try {
      const response = await fetch('/api/voice/interact', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin'
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Voice processing failed');
      }
      
      // Remove temp message
      newestBatch.pop();
      
      // Play audio response
      const audioResponseBlob = await response.blob();
      const audioUrl = URL.createObjectURL(audioResponseBlob);
      const audio = new Audio(audioUrl);
      
      audio.play().catch(e => {
        console.error('Autoplay prevented:', e);
        alert('Audio response ready. Click to play.');
      });
      
      // Refresh messages to show transcription and response
      reachedEnd = false;
      await fetchBatch();
      wrap.scrollTop = wrap.scrollHeight;
      
    } catch (err) {
      console.error('Error sending audio:', err);
      newestBatch.pop();
      renderAll();
      alert(`Voice error: ${err.message}`);
    }
  }

  // Voice button click handler
  callBtn?.addEventListener('click', async (e) => {
    e.preventDefault();
    
    // Check if voice is available
    try {
      const checkRes = await fetch('/api/voice/start', { method: 'POST' });
      const checkData = await checkRes.json();
      
      if (!checkData.ok) {
        alert(checkData.message);
        return;
      }
      
      // Start/stop recording
      toggleRecording();
      
    } catch (err) {
      console.error('Voice check error:', err);
      alert('Voice features are not available.');
    }
  });

  // Pull-to-unlock
  wrap.addEventListener('scroll', async ()=>{
    if (wrap.scrollTop <= 8){
      pullHint.classList.add('visible');
      if (!unlockedOlder) wrap.scrollTop = 22;

      if (!pullCooldown && oldest){
        pullCooldown = true;
        setTimeout(()=> pullCooldown=false, 450);

        if (!unlockedOlder){
          pullCount += 1;
          if (pullCount >= 2){
            unlockedOlder = true;
            allMessages = newestBatch.slice(0);
            await fetchBatch(oldest);
            pullHint.textContent = "Loaded previous chat.";
            setTimeout(()=> pullHint.classList.remove('visible'), 1200);
          }
        } else {
          await fetchBatch(allMessages[0]?.timestamp || oldest);
        }
      }
    } else {
      pullHint.classList.remove('visible');
    }
  });

  // Check for notifications periodically
  async function checkNotifications() {
    try {
      const res = await fetch('/api/get-notifications');
      const data = await res.json();
      if (data.notifications && data.notifications.length > 0) {
        // Show notification as bot message
        const notif = data.notifications[0];
        const user = await fetch('/api/messages').then(r => r.ok);
        if (user) {
          await fetchBatch();
        }
      }
    } catch (err) {
      console.error('Notification check error:', err);
    }
  }

  // Poll for notifications every 5 seconds
  setInterval(checkNotifications, 5000);

  // init
  window.addEventListener('DOMContentLoaded', async ()=>{
    await fetchBatch();
    wrap.scrollTop = wrap.scrollHeight;
  });
})();