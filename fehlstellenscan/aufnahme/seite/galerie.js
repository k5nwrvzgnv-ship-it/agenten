'use strict';
// Galerie: alle Balken, neueste zuerst, in den drei Teilen der Aufteilung (kette.teile). Ziehen ordnet zu,
// Pfeil links/rechts auf einer Karte auch. Balken, mit denen schon trainiert wurde, bleiben (gesperrt).
// ··· an der Karte: Aufnahme, Labeln, Maße, Name, Löschen. Löschen legt in den Papierkorb, Rückgängig statt Nachfrage.
const $=s=>document.querySelector(s),esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TEILE=['train','val','test'],NAME={train:'Training',val:'Prüfung',test:'Nur Test'};
const SCHLOSS='<svg class="ic" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="11" width="14" height="10" rx="1"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
const BALKEN='<svg viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 20l12-8h24l-12 8zM6 20v14h24V20M30 34l12-8V12"/></svg>';
let G=[],zug=null,mehr=null,weg=null;const WAHL=new Set;
const cm=mm=>(mm/10).toLocaleString('de-DE',{maximumFractionDigits:1}),lies=t=>/^\s*\d+([.,]\d+)?\s*$/.test(t)?Math.round(parseFloat(t.replace(',','.'))*100)/10:null;

async function ruf(weg,daten){let a;try{a=await fetch(weg,daten===undefined?{}:{method:'POST',headers:{'X-Aufnahme':'1'},body:JSON.stringify(daten)})}
 catch(e){throw Error('Das Programm auf dem Mac antwortet nicht. Im Terminal neu starten.')}
 let j={};try{j=await a.json()}catch(e){}if(!a.ok)throw Error(j.fehler||`Fehler ${a.status}`);return j}

function karte(b){
 // Seitenstriche nur, wenn etwas fehlt: ein vollständiger Balken bleibt ruhig
 const gut=n=>b.seiten[n]&&!b.weg?.includes(n),voll=['1','2','3','4'].every(gut);
 const seiten=voll?'':`<span class="vier">${['1','2','3','4'].map(n=>`<i class="${gut(n)?'ja':b.weg?.includes(n)?'weg':''}"></i>`).join('')}</span>`;
 // Vorschau: abgewickelter Mantel (unten Seite 1, darüber die nächste, wie beim Rollen), sonst ein Zuschnitt
 const bild=b.koerper?`<div class="mantel">${['4','3','2','1'].map(n=>`<i${b.seiten[n]&&!b.weg?.includes(n)?` style="background-image:url('/koerper/${encodeURIComponent(b.id)}/S${n}_k.jpg?v=${b.koerper}')"`:` class="fehlt${b.weg?.includes(n)?' weg':''}"`}></i>`).join('')}</div>`
  :b.bild?`<img src="/zuschnitt/${encodeURIComponent(b.bild)}_k.jpg" alt="" loading="lazy" draggable="false">`:`<div class="ohne">${BALKEN}</div>`;
 const titel=[`${b.id}: ${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)} cm`,b.holzart,
  `${Object.values(b.seiten).filter(Boolean).length} von 4 Seiten, ${b.fertig} von ${b.fotos} Fotos gelabelt`,
  ...(b.weg||[]).map(n=>`Seite ${n}: ${b.gruende?.[n]||'unbrauchbar'}`),
  b.abweichung>2?`Maß weicht bis ${b.abweichung.toLocaleString('de-DE')} % ab`:'',b.fest?'Schon trainiert, Teil bleibt':''].filter(Boolean).join('\n');
 // Ohne Fotos gibt es keinen Körper: die Karte führt dann in die Aufnahme
 const ziel=b.fotos?`/koerper?id=${encodeURIComponent(b.id)}`:`/?balken=${encodeURIComponent(b.id)}`,name=b.name||b.id;
 return `<div class="karte${b.fest?' fest':''}${b.id===rechnet?' rechnet':''}${WAHL.has(b.id)?' gewaehlt':''}" data-b="${esc(b.id)}" draggable="${!b.fest}" title="${esc(titel)}">
  <a href="${ziel}" draggable="false" aria-label="${esc(b.name?b.id+' '+b.name:b.id)}, ${esc(NAME[b.teil])}${b.fest?', gesperrt':''}${WAHL.has(b.id)?', gewählt':''}" aria-keyshortcuts="ArrowLeft ArrowRight Space">${bild}
  <span><b>${esc(name)}</b>${b.abweichung>2?'<i class="ab"></i>':''}${b.fest?SCHLOSS:''}${seiten}${vlz(b.id)}</span>
  <small>${b.name?esc(b.id)+' · ':''}${cm(b.laenge_mm)} × ${cm(b.breite_mm)} × ${cm(b.hoehe_mm)}</small>
  ${b.fotos?`<i class="lbl" style="--a:${Math.round(100*b.fertig/b.fotos)}%"></i>`:''}</a>
  <button class="mehr sy" aria-label="${esc(b.id)}" title="···" aria-haspopup="true" aria-expanded="${b.id===mehr}" aria-controls="kmenue">···</button></div>`}

// Vorlabeln (vorlabeln.js): Zustand je Balken als Zeichnung auf der Karte, solange er im letzten Lauf steht.
// Auswahl: Strg/Cmd- oder Umschalt-Klick, Leertaste auf einer Karte; dann unten eine Leiste mit dem Symbol.
function vlz(id){const l=VL.stand&&VL.stand.lauf;if(!l||!l.balken[id])return'';const[t,z]=VL.zustand(id);return`<span class="vlz" role="img" aria-label="Vorlabeln: ${esc(t)}" title="Vorlabeln: ${esc(t)}">${z}</span>`}
const vlFrei=ids=>ids.filter(i=>!VL.gesperrt(i)&&G.some(b=>b.id===i&&b.fotos));
function leiste(){const w=$('#gwahl');w.hidden=!WAHL.size;if(!WAHL.size)return;const frei=vlFrei([...WAHL]);
 $('#gwahlz').textContent=WAHL.size;$('#gwahlk').innerHTML=VL.knopf(frei[0]||[...WAHL][0],`data-vl="1"${frei.length?'':' aria-disabled="true"'}`,`${frei.length} Balken vorlabeln`);
 $('#gwahle').innerHTML=VL.etikett()}
function waehlen(id){WAHL.has(id)?WAHL.delete(id):WAHL.add(id);mal(id)}
async function vorlabeln(ids){$('#gfehler').textContent='';const frei=vlFrei(ids);if(!frei.length)return;
 try{await VL.start(frei);WAHL.clear();mal(aktiv())}catch(e){$('#gfehler').textContent=e.message}}
VL.beiStand=()=>mal(aktiv());VL.beiFertig=()=>laden();
function mal(fokus){leiste();
 const z=$('#grueck');z.hidden=!weg;if(weg){z.querySelector('span').textContent=weg;z.title=`${weg} zurückholen`;z.setAttribute('aria-label',z.title)}
 for(const sp of document.querySelectorAll('.spalte')){const t=sp.dataset.teil,da=G.filter(b=>b.teil===t);
  sp.querySelector('h2 small').textContent=da.length||'';
  sp.querySelector('.karten').innerHTML=da.map(karte).join('')||'<div class="leerspalte"></div>'}
 if(fokus)document.querySelector(`.karte[data-b="${fokus}"] a`)?.focus();
 if(mehr){const k=document.querySelector(`.karte[data-b="${mehr}"] .mehr`);if(k)stellen(k);else{mehr=null;menue.hidden=true}}}

async function setzen(id,teil){const b=G.find(x=>x.id===id);if(!b||b.fest||b.teil===teil)return;
 const alt=b.teil;b.teil=teil;mal(aktiv()===id?id:null);$('#gfehler').textContent='';
 try{await ruf('/api/teil',{balken:id,teil});$('#gmeldung').textContent=`${id}: ${NAME[teil]}`}
 catch(e){b.teil=alt;mal();$('#gfehler').textContent=e.message}}

const aktiv=()=>document.activeElement?.closest?.('.karte')?.dataset.b;
async function laden(){try{G=await ruf('/api/galerie');mal(aktiv());$('#gfehler').textContent='';nachrechnen()}
 catch(e){$('#gfehler').textContent=e.message}}

// Fehlende oder veraltete Körper nacheinander rechnen, neueste zuerst; was nicht geht, behält den Zuschnitt
const versucht=new Set();let rechnet=null;
async function nachrechnen(){if(rechnet)return;
 for(;;){const b=G.find(x=>x.fotos&&(!x.koerper||x.koerper_alt)&&!versucht.has(x.id));if(!b)break;
  versucht.add(b.id);rechnet=b.id;mal(aktiv());
  try{const k=await ruf('/api/koerper?id='+encodeURIComponent(b.id));const x=G.find(y=>y.id===b.id);
   if(x){x.koerper=k.stand;x.koerper_alt=false;x.weg=Object.keys(k.seiten).filter(n=>k.seiten[n].grund);x.gruende=Object.fromEntries(x.weg.map(n=>[n,k.seiten[n].grund]));const w=Object.values(k.seiten).filter(s=>!s.grund).flatMap(s=>Object.values(s.abweichung_prozent)).filter(v=>v!=null).map(Math.abs);x.abweichung=w.length?Math.max(...w):null}}
  catch(e){console.warn(b.id,e.message)}}
 rechnet=null;mal(aktiv())}

const galerie=$('#galerie');
galerie.addEventListener('dragstart',e=>{const k=e.target.closest?.('.karte');if(!k||k.classList.contains('fest'))return e.preventDefault();
 zug=k.dataset.b;e.dataTransfer.setData('text/plain',zug);e.dataTransfer.effectAllowed='move';k.classList.add('zieht')});
galerie.addEventListener('dragend',()=>{zug=null;document.querySelectorAll('.zieht,.ziel').forEach(x=>x.classList.remove('zieht','ziel'))});
galerie.addEventListener('dragover',e=>{const sp=e.target.closest('.spalte');if(!sp||!zug)return;e.preventDefault();e.dataTransfer.dropEffect='move';
 document.querySelectorAll('.ziel').forEach(x=>x!==sp&&x.classList.remove('ziel'));sp.classList.add('ziel')});
galerie.addEventListener('dragleave',e=>{const sp=e.target.closest('.spalte');if(sp&&!sp.contains(e.relatedTarget))sp.classList.remove('ziel')});
galerie.addEventListener('drop',e=>{const sp=e.target.closest('.spalte');if(!sp||!zug)return;e.preventDefault();sp.classList.remove('ziel');setzen(zug,sp.dataset.teil)});
galerie.addEventListener('keydown',e=>{const k=e.target.closest?.('.karte > a')?.parentElement;if(k&&e.key===' '){e.preventDefault();return waehlen(k.dataset.b)}
 if(e.key==='Escape'&&WAHL.size&&!mehr){WAHL.clear();return mal(k?.dataset.b)}if(!k||!['ArrowLeft','ArrowRight'].includes(e.key))return;
 const b=G.find(x=>x.id===k.dataset.b),i=TEILE.indexOf(b.teil)+(e.key==='ArrowRight'?1:-1);e.preventDefault();
 if(i>=0&&i<TEILE.length)setzen(b.id,TEILE[i])});
// ··· einer Karte: eine gemeinsame Symbolreihe unter dem Knopf
const menue=$('#kmenue');
function menueZu(still){if(!mehr)return;const id=mehr;mehr=null;menue.hidden=true;const k=document.querySelector(`.karte[data-b="${id}"] .mehr`);if(k){k.setAttribute('aria-expanded','false');if(!still)k.focus()}}
function menueAuf(knopf){const id=knopf.closest('.karte').dataset.b,b=G.find(x=>x.id===id);if(mehr===id)return menueZu();menueZu(true);mehr=id;knopf.setAttribute('aria-expanded','true');
 const vk=menue.querySelector('[data-tu=vorlabeln]'),[vt,vz]=VL.zustand(id),gesp=!!VL.aus||VL.laeuft()||VL.gesperrt(id)||!VL.stand;vk.hidden=!b.fotos;
 vk.innerHTML=VL.knopf(id,'','').replace(/^<button[^>]*>|<\/button>$/g,'');vk.title=VL.aus||(gesp?vt:'Vorlabeln');vk.setAttribute('aria-label',vk.title);vk.setAttribute('aria-disabled',gesp);
 menue.querySelector('[data-tu=aufnahme]').href=`/?balken=${encodeURIComponent(id)}`;const l=menue.querySelector('[data-tu=labeln]');l.href=`/labeln?balken=${encodeURIComponent(id)}`;l.hidden=!b.fotos;
 menue.hidden=false;stellen(knopf);menue.querySelector('a,button:not([hidden])').focus()}
function stellen(knopf){const g=galerie.getBoundingClientRect(),r=knopf.getBoundingClientRect(),w=menue.offsetWidth;
 menue.style.left=Math.max(8,Math.min(r.right-g.left-w,g.width-w-8))+'px';menue.style.top=(r.bottom-g.top+4)+'px'}
galerie.addEventListener('click',e=>{const k=e.target.closest('.mehr');if(k){e.preventDefault();menueAuf(k);return}
 const a=e.target.closest('.karte > a');if(a&&(e.ctrlKey||e.metaKey||e.shiftKey)){e.preventDefault();waehlen(a.parentElement.dataset.b)}
 const v=e.target.closest('[data-vl]');if(v&&v.getAttribute('aria-disabled')!=='true')vorlabeln([...WAHL]);if(e.target.closest('#gwahlx')){WAHL.clear();mal()}
 const m=e.target.closest('.vlmehr');if(m)VL.menue(m)});
menue.addEventListener('click',e=>{const t=e.target.closest('[data-tu]')?.dataset.tu,id=mehr;if(!t||!id||t==='aufnahme'||t==='labeln')return;menueZu(true);
 if(t==='bearbeiten')bearbeiten(id,'laenge');if(t==='weg')loeschen(id);if(t==='vorlabeln'&&menue.querySelector('[data-tu=vorlabeln]').getAttribute('aria-disabled')!=='true')vorlabeln([id])});
menue.addEventListener('keydown',e=>{const k=[...menue.querySelectorAll('[data-tu]:not([hidden])')],i=k.indexOf(document.activeElement);
 if(e.key==='Escape'){e.preventDefault();menueZu()}if(e.key==='ArrowRight'||e.key==='ArrowDown'){e.preventDefault();k[(i+1)%k.length].focus()}
 if(e.key==='ArrowLeft'||e.key==='ArrowUp'){e.preventDefault();k[(i+k.length-1)%k.length].focus()}});
addEventListener('pointerdown',e=>{if(mehr&&!e.target.closest('#kmenue,.mehr'))menueZu(true)});
galerie.addEventListener('scroll',()=>menueZu(true),true);addEventListener('resize',()=>menueZu(true));

async function loeschen(id){$('#gfehler').textContent='';try{await ruf('/api/balken-weg',{balken:id});G=G.filter(b=>b.id!==id);weg=id;mal();$('#grueck').focus();$('#gmeldung').textContent=`${id} gelöscht`}
 catch(e){$('#gfehler').textContent=e.message}}
async function zurueck(){if(!weg)return;const id=weg;try{await ruf('/api/balken-zurueck',{balken:id});weg=null;await laden();mal(id)}catch(e){$('#gfehler').textContent=e.message}}
$('#grueck').onclick=zurueck;
addEventListener('keydown',e=>{if(e.key==='z'&&(e.metaKey||e.ctrlKey)&&weg&&!$('#bearb').open&&!/^(INPUT|SELECT)$/.test(e.target.tagName)){e.preventDefault();zurueck()}});

// Maße und Name im Dialog. Fotos bleiben, der Server passt Abstand und Maßstab der fotografierten Seiten an
const dlg=$('#bearb'),form=dlg.querySelector('form');let bid=null;
function bearbeiten(id,feld){const b=G.find(x=>x.id===id);if(!b)return;bid=id;$('#btitel').textContent=b.name?`${b.id} ${b.name}`:b.id;
 for(const k of['laenge','breite','hoehe'])form[k].value=cm(b[k+'_mm']).replace(/\./g,'');form.holzart.value=b.holzart||'';form.name.value=b.name||'';
 form.querySelector('.fehler').textContent='';dlg.showModal();form[feld].focus();form[feld].select()}
form.onsubmit=async e=>{e.preventDefault();const d={id:bid,holzart:form.holzart.value,name:form.name.value};for(const k of['laenge','breite','hoehe'])d[k+'_mm']=lies(form[k].value);
 try{await ruf('/api/balken',d);dlg.close();await laden();mal(bid)}catch(x){form.querySelector('.fehler').textContent=x.message}};
dlg.querySelector('.zu').onclick=()=>dlg.close();
dlg.addEventListener('close',()=>{document.querySelector(`.karte[data-b="${bid}"] .mehr`)?.focus()});
galerie.addEventListener('error',e=>{if(e.target.tagName==='IMG'){const d=document.createElement('div');d.className='ohne';d.innerHTML=BALKEN;e.target.replaceWith(d)}},true);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)laden()});
laden();VL.laden();
