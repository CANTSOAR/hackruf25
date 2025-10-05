(() => {
  const wrap   = document.getElementById('chat');
  const form   = document.getElementById('msgForm');
  const input  = document.getElementById('msgInput');
  const sendBtn= document.getElementById('sendBtn');
  const callBtn= document.getElementById('callBtn');
  const prefsBtn = document.getElementById('prefsOpen');
  const modal  = document.getElementById('prefsModal');
  const modalClose = document.getElementById('prefsClose');
  const modalSave  = document.getElementById('prefsSave');
  const toneSel = document.getElementById('toneSel');
  const preview = document.getElementById('emojiPreview');
  const pullHint = document.getElementById('pullHint');
  if (!wrap) return;

  // ----- Avatar prefs -----
  const toneMap = { default:'', light:'🏻', medium:'🏼', dark:'🏽', darker:'🏾', darkest:'🏿' };
  let avatarGender='person', avatarTone='default';
  function emojiFromPrefs(gender, tone){
    const toneChar = toneMap[tone] ?? '';
    if(gender==='man') return '👨' + toneChar;
    if(gender==='woman') return '👩' + toneChar;
    return '🧑' + toneChar;
  }
  async function loadPrefs(){
    try{
      const r = await fetch('/api/prefs'); if(!r.ok) return;
      const d = await r.json();
      avatarGender = d.avatar_gender || 'person';
      avatarTone   = d.avatar_tone || 'default';
      preview.textContent = emojiFromPrefs(avatarGender, avatarTone);
      const g = modal.querySelector(`input[name="gender"][value="${avatarGender}"]`); if(g) g.checked = true;
      toneSel.value = avatarTone;
    }catch(e){ console.warn(e); }
  }
  async function savePrefs(){
    const gender = modal.querySelector('input[name="gender"]:checked')?.value || 'person';
    const tone = toneSel.value || 'default';
    try{
      await fetch('/api/prefs', {method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({avatar_gender: gender, avatar_tone: tone})});
      avatarGender=gender; avatarTone=tone;
      preview.textContent = emojiFromPrefs(avatarGender, avatarTone);
      closeModal(); renderAll();
    }catch(e){ console.warn(e); }
  }
  function openModal(){ modal.classList.remove('hidden'); }
  function closeModal(){ modal.classList.add('hidden'); }
  prefsBtn?.addEventListener('click', async ()=>{ await loadPrefs(); openModal(); });
  modalClose?.addEventListener('click', closeModal);
  modalSave?.addEventListener('click', (e)=>{ e.preventDefault(); savePrefs(); });
  toneSel?.addEventListener('change', ()=>{ 
    preview.textContent = emojiFromPrefs(modal.querySelector('input[name="gender"]:checked')?.value || 'person', toneSel.value); 
  });
  modal.querySelectorAll('input[name="gender"]').forEach(r => r.addEventListener('change',()=>{
    preview.textContent = emojiFromPrefs(r.value, toneSel.value);
  }));

  // ----- Voice call placeholder -----
  callBtn?.addEventListener('click', async ()=>{
    try{
      const r = await fetch('/api/interact', {method:'POST'});
      const d = await r.json();
      alert(d.message || 'Voice coming soon.');
    }catch(e){ alert('Voice coming soon.'); }
  });

  // ----- Chat logic -----
  let newestBatch = [];        // messages from this login session (initial view)
  let allMessages = [];        // unified list after unlock
  let oldest = null;           // string ISO of earliest loaded
  let loading = false;
  let reachedEnd = false;
  let loginAt = null;          // string ISO from server
  let unlockedOlder = false;   // require 2 pulls
  let pullCount = 0;
  let pullCooldown = false;    // debounce pulls

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
    const userAvatar = `<div class="avatar">${emojiFromPrefs(avatarGender, avatarTone)}</div>`;
    const botAvatar  = `<div class="avatar"><img src="/static/images/rutgers_logo.png" onerror="this.parentElement.textContent='🤖'"></div>`;
    return isUser
      ? `<div class="${rowClass}"><div class="${bubble}">${m.text}</div>${userAvatar}</div>`
      : `<div class="${rowClass}">${botAvatar}<div class="${bubble}">${m.text}</div></div>`;
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

      // FIX: do not filter out all messages if login_at is newer than message timestamps
      if (!before && !unlockedOlder && loginAt) {
        const cutoff = new Date(loginAt).getTime();
        const BUFFER_MS = 24*3600*1000; // allow 1 day earlier to keep initial messages
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

  // Merge two sorted asc lists (by timestamp) without dupes
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
      await fetchBatch();  // refresh latest (user + bot)
      wrap.scrollTop = wrap.scrollHeight;
    }catch(e){ console.error(e); }
    finally{ sendBtn.disabled = false; input.focus(); }
  }

  form?.addEventListener('submit', (e)=>{ e.preventDefault(); send(); });
  sendBtn?.addEventListener('click', (e)=>{ e.preventDefault(); send(); });

  // Pull-to-unlock with resistance & double pull
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

  // init
  window.addEventListener('DOMContentLoaded', async ()=>{
    await loadPrefs();
    await fetchBatch();
    wrap.scrollTop = wrap.scrollHeight;
  });
})();
