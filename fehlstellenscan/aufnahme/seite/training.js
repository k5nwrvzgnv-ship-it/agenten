'use strict';
const $=i=>document.getElementById(i),esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TEIL={train:'Training',val:'Prüfung',test:'Nur Test'};let S=null;
async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify(daten)})}catch(e){throw Error('Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.')}
 const j=await a.json();if(!a.ok)throw Error(j.fehler);return j}
const aktiv=()=>S.lauf&&['bauen','training'].includes(S.lauf.status);
function mal(){const d=document.activeElement&&document.activeElement.dataset.b;
 $('tbal').innerHTML=S.balken.map(b=>`<tr><td>${esc(b.id)}</td><td>${b.fertig} von ${b.fotos}</td><td>${b.objekte}</td><td>${b.fest?TEIL[b.teil]:`<select data-b="${esc(b.id)}" aria-label="Teil von ${esc(b.id)}">${Object.entries(TEIL).map(([k,n])=>`<option value="${k}" ${k===b.teil?'selected':''}>${n}</option>`).join('')}</select>`}</td></tr>`).join('');
 if(d)document.querySelector(`[data-b="${d}"]`)?.focus();
 const g=S.balken.some(b=>b.fertig&&b.teil!=='test');
 $('tprobe').textContent=S.probe&&g?'Ablaufprobe: Prüfung auf denselben Fotos wie das Training. Die Zahlen sagen nichts über die Erkennung.':'';
 $('tlos').disabled=!aktiv()&&!g;$('tlos').textContent=aktiv()?'Training abbrechen':'Training starten';
 const l=S.lauf;if(!l){$('tlauf').innerHTML='';return}
 const w=l.werte.at(-1),t={bauen:'Datensatz wird gebaut',training:`Epoche ${l.epoche} von ${l.epochen}`,fertig:'Fertig',fehler:'Fehlgeschlagen',abgebrochen:'Abgebrochen'}[l.status];
 $('tlauf').innerHTML=`<p role="status"><b>${esc(l.name)}</b> ${t}${l.probe?' (Ablaufprobe)':''}</p><progress max="${l.epochen}" value="${l.epoche}" aria-label="Epochen"></progress>${w&&w.map!==undefined?`<p class="leise">Masken-mAP50 ${w.map.toLocaleString('de-DE',{maximumFractionDigits:3})}</p>`:''}${l.fehler?`<p class="fehler">${esc(l.fehler)}</p>`:''}${l.status==='fertig'?`<p class="leise">${esc(l.ordner)}/weights/best.pt</p>`:''}`}
async function tu(weg,daten){try{S=await ruf(weg,daten);$('tfehler').textContent='';mal()}catch(e){$('tfehler').textContent=e.message}}
$('tlos').onclick=()=>tu(aktiv()?'/api/abbrechen':'/api/training',{});
$('tbal').onchange=e=>tu('/api/teil',{balken:e.target.dataset.b,teil:e.target.value});
async function puls(){if(document.activeElement.tagName!=='SELECT')try{S=await ruf('/api/training');mal()}catch(e){$('tfehler').textContent=e.message};setTimeout(puls,3000)}
puls();
