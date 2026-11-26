'use strict';
/* Hochladen (Servermodus): Balken wählen oder anlegen, Seite antippen, Fotos wählen. Jedes Foto geht einzeln hoch. */
const $=s=>document.querySelector(s),esc=t=>String(t??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cm=(mm,n=1)=>(mm/10).toLocaleString('de-DE',{maximumFractionDigits:n,useGrouping:false}),lies=t=>/^\s*\d+([.,]\d+)?\s*$/.test(t)?Math.round(parseFloat(t.replace(',','.'))*100)/10:null;
const PF={weg:'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v5M14 11v5',bild:'M4 5h16v14H4zM4 15l5-5 4 4 3-3 4 4'};
const ic=n=>`<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="${PF[n]}"/></svg>`;
/* Balken im Schrägbild wie in der Aufnahme: Seite k schraffiert, 1 oben, 2 rechts, 3 unten, 4 links */
function balken3d(b,k){const l=Math.max(b.breite_mm,b.hoehe_mm),s=Math.min(b.breite_mm,b.hoehe_mm),w=16,h=Math.max(7,16*s/l),dx=30,dy=-15,x=6,y=4-dy,P=q=>q.map(z=>z.toFixed(1)).join(' ');
 const v=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]],r=v.map(([a,c])=>[a+dx,c+dy]),f={1:[v[0],v[1],r[1],r[0]],2:[v[1],r[1],r[2],v[2]],3:[v[3],v[2],r[2],r[3]],4:[v[0],r[0],r[3],v[3]]}[k];
 return `<svg class="b3" viewBox="0 0 ${x+w+dx+6} ${(y+h+6).toFixed(1)}" aria-hidden="true"><path d="M${f.map(P).join('L')}Z" class="flaeche${+k>2?' hinten':''}"/><path d="M${P(v[3])}L${P(r[3])}L${P(r[2])}M${P(r[0])}L${P(r[3])}" class="verdeckt"/><path d="M${P(v[0])}H${x+w}V${(y+h).toFixed(1)}H${x}ZM${P(v[0])}L${P(r[0])}L${P(r[1])}L${P(r[2])}L${P(v[2])}M${P(v[1])}L${P(r[1])}" class="kanten"/></svg>`}
let S={balken:[],ich:'',verwalten:false},bid=null,seite='1',laeuft=false;
try{bid=localStorage.getItem('hoch-balken');seite=localStorage.getItem('hoch-seite')||'1'}catch(e){}
const B=()=>S.balken.find(b=>b.id===bid);
async function api(weg,body,roh){const a=await fetch(weg,{method:'POST',headers:{'X-Aufnahme':'1'},body:roh?body:JSON.stringify(body)});let j={};try{j=await a.json()}catch(e){}if(!a.ok)throw Error(j.fehler||`Fehler ${a.status}`);return j}
function merk(){try{localStorage.setItem('hoch-balken',bid||'');localStorage.setItem('hoch-seite',seite)}catch(e){}}
function zeige(){
 $('#ich').textContent=S.ich;
 $('#wahl').innerHTML=S.balken.map(b=>`<option value="${b.id}">${b.id}${b.holzart?' · '+esc(b.holzart):''}</option>`).join('');
 if(!B())bid=S.balken.length?S.balken[S.balken.length-1].id:null;
 const ohne=!bid;$('#form').hidden=!ohne&&!$('#form').dataset.offen;$('#hoch').hidden=!$('#form').hidden;$('#abbr').hidden=ohne;
 if(ohne)return;
 $('#wahl').value=bid;const b=B(),s=b.seiten[seite];merk();
 $('#seiten').innerHTML=['1','2','3','4'].map(k=>{const x=b.seiten[k];const t=`Seite ${k}`+(x.frei?'':' (Fotobox)');return `<button data-s="${k}" aria-pressed="${k===seite}" title="${t}" aria-label="${t}, ${x.fotos.length} Fotos" ${x.frei?'':'disabled'}>${balken3d(b,k)}<small>${x.fotos.length}</small></button>`}).join('');
 $('#werte').innerHTML=`<dt>L × B × H</dt><dd>${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)} cm</dd>`;
 $('#fotos').innerHTML=s.fotos.map(f=>{const n=f.datei.replace(/\.[a-z]+$/,'');return `<li><img src="/zuschnitt/${esc(n)}_k.jpg" alt="Foto ${f.nr+1}" loading="lazy"><span><b>${f.nr+1}</b><small>${esc(f.von||'')}</small>${S.verwalten?`<button class="sy" data-weg="${f.nr}" title="Foto verwerfen" aria-label="Foto ${f.nr+1} verwerfen">${ic('weg')}</button>`:''}</span></li>`}).join('');
 $('#leer').hidden=s.fotos.length>0;$('#leer').innerHTML=ic('bild');
 $('#waehlen').classList.toggle('aus',!s.frei||laeuft);$('#datei').disabled=!s.frei||laeuft}
async function laden(){try{const a=await fetch('/api/stand');const j=await a.json();if(!a.ok)throw Error(j.fehler);S=j;zeige()}catch(e){$('#hfehler').textContent='Keine Verbindung zu Neurolign. '+e.message}}
$('#wahl').onchange=e=>{bid=e.target.value;zeige()};
$('#seiten').onclick=e=>{const k=e.target.closest('button')?.dataset.s;if(k){seite=k;zeige()}};
$('#neu').onclick=()=>{$('#form').dataset.offen='1';zeige();$('#form input').focus()};
$('#abbr').onclick=()=>{delete $('#form').dataset.offen;zeige()};
$('#form form').onsubmit=async e=>{e.preventDefault();const f=e.target,fe=f.querySelector('.fehler');
 const w={laenge_mm:lies(f.laenge.value),breite_mm:lies(f.breite.value),hoehe_mm:lies(f.hoehe.value),holzart:f.holzart.value};
 if([w.laenge_mm,w.breite_mm,w.hoehe_mm].includes(null)){fe.textContent='Länge, Breite und Höhe in cm eintragen.';return}
 try{const b=await api('/api/balken',w);fe.textContent='';f.reset();delete $('#form').dataset.offen;bid=b.id;seite='1';await laden()}catch(x){fe.textContent=x.message}};
$('#datei').onchange=async e=>{const liste=[...e.target.files];e.target.value='';if(!liste.length||laeuft)return;
 laeuft=true;const p=$('#fort'),fe=$('#hfehler');fe.textContent='';p.hidden=false;p.max=liste.length;p.value=0;zeige();const ziel=bid,sei=seite,fehl=[];
 for(const d of liste){try{S=await api(`/api/hochladen?balken=${encodeURIComponent(ziel)}&seite=${sei}`,d,true)}catch(x){fehl.push(`${d.name}: ${x.message}`)}p.value++;zeige()}
 laeuft=false;p.hidden=true;fe.textContent=fehl.join(' ');zeige()};
$('#fotos').onclick=async e=>{const k=e.target.closest('[data-weg]');if(!k)return;
 try{S=await api('/api/foto-weg',{balken:bid,seite,nr:+k.dataset.weg});zeige()}catch(x){$('#hfehler').textContent=x.message}};
laden();
