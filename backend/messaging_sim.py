"""A phone-shaped chat page for trying the WhatsApp/SMS front end without Twilio.

It posts to the same /twilio/webhook a real number would, as form fields, so what works here works
behind Twilio. Open /messaging/sim. A record button sends a voice note (browser recording) to /stt for
a transcript only when the real voice-note path is unavailable; the page itself never stores messages.
"""
PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>JARVIS on WhatsApp / SMS (simulator)</title>
<style>
:root{--bg:#0b141a;--panel:#111b21;--me:#005c4b;--bot:#202c33;--txt:#e9edef;--dim:#8696a0;--acc:#25d366}
@media (prefers-color-scheme: light){:root{--bg:#e5ddd5;--panel:#f0f2f5;--me:#d9fdd3;--bot:#fff;--txt:#111b21;--dim:#667781}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.45 system-ui,"Segoe UI",sans-serif;display:flex;justify-content:center}
.phone{width:min(480px,100vw);height:100dvh;display:flex;flex-direction:column;background:var(--bg)}
header{background:var(--panel);padding:10px 14px;display:flex;gap:10px;align-items:center;border-bottom:1px solid rgba(128,128,128,.25)}
.av{width:38px;height:38px;border-radius:50%;background:var(--acc);color:#04110b;display:grid;place-items:center;font-weight:800}
header small{color:var(--dim);display:block;font-size:12px}
.tools{margin-left:auto;display:flex;gap:6px;align-items:center;font-size:12px}
select{background:var(--bg);color:var(--txt);border:1px solid rgba(128,128,128,.4);border-radius:6px;padding:4px}
#log{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:6px}
.m{max-width:84%;padding:8px 11px;border-radius:10px;white-space:pre-wrap;overflow-wrap:anywhere;box-shadow:0 1px 1px rgba(0,0,0,.2)}
.me{align-self:flex-end;background:var(--me)}.bot{align-self:flex-start;background:var(--bot)}
.m b{font-weight:700}.meta{font-size:11px;color:var(--dim);text-align:center;margin:4px 0}
form{display:flex;gap:8px;padding:10px;background:var(--panel)}
input{flex:1;padding:11px 14px;border-radius:22px;border:0;background:var(--bg);color:var(--txt);font-size:16px}
button{border:0;border-radius:50%;width:44px;height:44px;background:var(--acc);color:#04110b;font-size:18px;cursor:pointer}
.chips{display:flex;flex-wrap:wrap;gap:6px;padding:0 10px 8px;background:var(--panel)}
.chips button{width:auto;height:auto;border-radius:16px;padding:6px 12px;font-size:13px;background:var(--bg);color:var(--txt);border:1px solid rgba(128,128,128,.4)}
</style></head><body><div class="phone">
<header><div class="av">J</div><div><b>JARVIS</b><small id="sub">simulator · same webhook as Twilio</small></div>
<div class="tools"><select id="ch"><option value="whatsapp:">WhatsApp</option><option value="">SMS</option></select>
<input id="num" value="+919800000001" style="width:118px;flex:none;padding:5px 8px;border-radius:6px;font-size:12px" aria-label="phone number"></div></header>
<div id="log" aria-live="polite"></div>
<div class="chips"><button data-q="hi">Menu</button><button data-q="1">1 Moneylender</button><button data-q="3">3 Schemes</button><button data-q="हिंदी">हिंदी</button><button data-q="CANCEL">Cancel</button></div>
<form id="f"><input id="t" autocomplete="off" placeholder="Type a message"><button aria-label="send">➤</button></form></div>
<script>
const log=document.getElementById('log');
function add(text,who){const d=document.createElement('div');d.className='m '+who;
  d.innerHTML=text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\*([^*\n]+)\*/g,'<b>$1</b>').replace(/(https?:\/\/\S+)/g,'<a href="$1" target="_blank" style="color:inherit">$1</a>');log.appendChild(d);log.scrollTop=log.scrollHeight}
async function send(text){if(!text.trim())return;add(text,'me');
  const from=document.getElementById('ch').value+document.getElementById('num').value;
  const fd=new URLSearchParams({From:from,Body:text,MessageSid:'SIM'+Date.now()});
  try{const r=await fetch('/twilio/webhook?format=json',{method:'POST',body:fd});const j=await r.json();
    for(const m of j.messages){await new Promise(r=>setTimeout(r,250));add(m,'bot')}}
  catch(e){add('Could not reach the server.','bot')}}
document.getElementById('f').onsubmit=e=>{e.preventDefault();const t=document.getElementById('t');const v=t.value;t.value='';send(v)};
document.querySelectorAll('.chips button').forEach(b=>b.onclick=()=>send(b.dataset.q));
add('Send "hi" to start. Numbers work too: 1 to 9.','bot');
</script></body></html>"""
